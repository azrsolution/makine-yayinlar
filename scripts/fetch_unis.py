#!/usr/bin/env python3
"""
UNIS (Karabük Üniversitesi Akademik Veri Yönetim Sistemi) birim sayfasından
yıllara göre yayın sayılarını ve öne çıkan yayınları çekip docs/data.json'a yazar.

Kullanım:  python scripts/fetch_unis.py
Bağımlılık: pip install requests beautifulsoup4

Ayarlar aşağıdaki CONFIG bölümündedir. Başka bir bölüm için yalnızca
UNIT_SLUG, UNIT_ID ve SOURCE_URL değiştirilir.
"""
import json
import os
import sys
import time
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

# ----------------------------- CONFIG --------------------------------------
UNIT_NAME = "Makine Mühendisliği"
UNIT_SLUG = "makine-muhendisligi"
UNIT_ID = "32896"  # UNIS içindeki birim kimliği (sayfanın isteğinde 'id')
SOURCE_URL = "https://unis.karabuk.edu.tr/birim/calismalar/makine-muhendisligi/id=2_Cp8uEJO_74"
START_YEAR = 2010
FEATURED_COUNT = 20                # gösterilecek öne çıkan yayın sayısı
FEATURED_INDEXES = {"SCI Expanded", "SCI", "SSCI"}   # öne çıkanlarda kabul edilen endeksler
FEATURED_YEARS_BACK = 1            # bu yıl + önceki 1 yıl
MAX_DROP = 0.30                    # toplam sayı önceki çalıştırmaya göre %30'dan fazla düşerse yazma
DELAY = 0.5                        # istekler arası bekleme (sn) - sunucuyu yormamak için
OUT = os.path.join(os.path.dirname(__file__), "..", "docs", "data.json")
# ---------------------------------------------------------------------------

BASE = "https://unis.karabuk.edu.tr/"
ENDPOINT = (
    BASE + "?act=guest&act2=akademik&act3=birim&act4=calismalar"
    f"&act5={UNIT_SLUG}&id={UNIT_ID}&act7=calismalar&act8={UNIT_SLUG}"
    "&grid=1&table_id=SolrRecord"
)
COLS = "SiraNo,Id,Title,TurStr,Url,Html,IdEncoded"

# UNIS endeks etiketi -> grafik kategorisi
INDEX_MAP = {
    "SCI Expanded": "SCI-E",
    "SCI": "SCI / SSCI",
    "SSCI": "SCI / SSCI",
    "ESCI": "ESCI",
    "Scopus": "Scopus",
    "TR Dizin": "TR Dizin",
}
CATEGORIES = ["SCI-E", "SCI / SSCI", "ESCI", "Scopus", "TR Dizin", "Diğer"]

session = requests.Session()
session.headers.update({
    "User-Agent": "KBU-Makine-Bolum-Web/1.0 (gunluk yayin istatistigi)",
    "X-Requested-With": "XMLHttpRequest",
})


def query(filters: dict, length: int = 1) -> dict:
    """UNIS listeleme ucuna bir sorgu atar, JSON döndürür."""
    params = [
        {"name": "sEcho", "value": 1},
        {"name": "iColumns", "value": 7},
        {"name": "sColumns", "value": COLS},
        {"name": "iDisplayStart", "value": 0},
        {"name": "iDisplayLength", "value": length},
        {"name": "sSearch", "value": ""},
        {"name": "bRegex", "value": False},
        {"name": "iSortCol_0", "value": 0},
        {"name": "sSortDir_0", "value": "asc"},
        {"name": "iSortingCols", "value": 1},
        {"name": "Tur", "value": "Yayin"},
        *[{"name": k, "value": str(v)} for k, v in filters.items()],
        {"name": "table_id", "value": "SolrRecord"},
        {"name": "sConditionOperators", "value": {}},
        {"name": "selected_fields", "value": COLS},
        {"name": "user_selected_fields", "value": "SiraNo"},
    ]
    for attempt in range(3):
        try:
            r = session.post(ENDPOINT, data={"data": json.dumps(params)}, timeout=60)
            r.raise_for_status()
            time.sleep(DELAY)
            return json.loads(r.text)
        except (requests.RequestException, ValueError) as e:
            if attempt == 2:
                raise
            print(f"  tekrar deneniyor ({e})", file=sys.stderr)
            time.sleep(5 * (attempt + 1))


def parse_row(row: list) -> dict:
    """Bir aaData satırını (SiraNo, Id, Title, TurStr, Url, Html, IdEncoded) çözer."""
    soup = BeautifulSoup(row[5], "html.parser")

    def text(sel):
        el = soup.select_one(sel)
        return el.get_text(strip=True) if el else ""

    author_el = next(
        (d for d in soup.select("div.text-secondary") if "fw-bold" not in d.get("class", [])),
        None,
    )
    year_txt = text(".badge-outline-secondary")
    return {
        "id": int(str(row[1]).split("-")[-1]),
        "title": " ".join(str(row[2]).split()),
        "journal": text("div.fw-bold.text-secondary"),
        "authors": " ".join(author_el.get_text(" ", strip=True).split()).replace(" ,", ",") if author_el else "",
        "dept_authors": [b.get_text(strip=True) for b in author_el.find_all("b")] if author_el else [],
        "year": int(year_txt) if year_txt.isdigit() else None,
        "index": text(".badge-outline-info") or None,
        "url": BASE + str(row[4]).lstrip("/"),
    }


def pick_featured(papers: list) -> list:
    """En yeni SCI/SCI-E makalelerden, her bölüm yazarı en fazla bir kez olacak şekilde seçer."""
    papers = sorted(papers, key=lambda p: (p["year"] or 0, p["id"]), reverse=True)
    used, chosen = set(), []
    for p in papers:
        if p["index"] not in FEATURED_INDEXES or not p["dept_authors"]:
            continue
        if any(a in used for a in p["dept_authors"]):
            continue
        used.update(p["dept_authors"])
        chosen.append({k: v for k, v in p.items() if k != "id"})
        if len(chosen) >= FEATURED_COUNT:
            break
    return chosen


def main():
    now_year = datetime.now().year
    years, makale, bildiri, toplam = [], [], [], []
    endeks = {c: [] for c in CATEGORIES}
    recent = []

    for y in range(START_YEAR, now_year + 1):
        t = query({"Yayin.Yil": y})
        b = query({"Yayin.Yil": y, "Yayin.Tur": 14})
        m = query({"Yayin.Yil": y, "Yayin.Tur": 10}, length=2000)

        counts = {c: 0 for c in CATEGORIES}
        for row in m["aaData"]:
            p = parse_row(row)
            counts[INDEX_MAP.get(p["index"], "Diğer")] += 1
            if y >= now_year - FEATURED_YEARS_BACK:
                recent.append(p)

        years.append(y)
        toplam.append(t["iTotalRecords"])
        bildiri.append(b["iTotalRecords"])
        makale.append(m["iTotalRecords"])
        for c in CATEGORIES:
            endeks[c].append(counts[c])
        print(f"{y}: toplam={toplam[-1]} makale={makale[-1]} bildiri={bildiri[-1]}")

    all_pubs = query({})["iTotalRecords"]

    data = {
        "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": SOURCE_URL,
        "unit": UNIT_NAME,
        "years": years,
        "makale": makale,
        "bildiri": bildiri,
        "toplam": toplam,
        "endeks": endeks,
        "totals": {"yayin": all_pubs, "makale": sum(makale)},
        "featured": pick_featured(recent),
    }

    # Güvenlik kontrolü: UNIS hata verip boş/eksik döndürürse siteyi bozmayalım.
    if sum(toplam) == 0:
        sys.exit("HATA: UNIS'ten hiç kayıt gelmedi, data.json güncellenmedi.")
    if os.path.exists(OUT):
        with open(OUT, encoding="utf-8") as f:
            old = json.load(f)
        old_sum = sum(old.get("toplam", []))
        if old_sum and sum(toplam) < old_sum * (1 - MAX_DROP):
            sys.exit(f"HATA: toplam {old_sum} -> {sum(toplam)} düştü (>%{int(MAX_DROP*100)}). "
                     "UNIS arayüzü değişmiş olabilir; data.json güncellenmedi.")

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"Yazıldı: {OUT}  ({len(data['featured'])} öne çıkan yayın)")


if __name__ == "__main__":
    main()
