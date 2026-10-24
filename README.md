# Makine Mühendisliği – Otomatik Yayın Widget'ı

UNIS'teki bölüm yayınlarını her gece çeker, yıllara göre bar grafik ve öne çıkan
yayınları gösteren bir sayfa üretir. Bölüm web sayfasına iframe ile gömülür.

```
scripts/fetch_unis.py           UNIS'ten veriyi çeker -> docs/data.json
docs/index.html                 Widget (Chart.js grafik + yayın kartları)
docs/data.json                  Veri (24.10.2026 tarihli başlangıç verisi dahil)
.github/workflows/guncelle.yml  Her gece 05:17'de betiği çalıştırır
```

## Kurulum

1. GitHub'da **public** bir depo açın (ör. `makine-yayinlar`). Bölüm adına bir hesap/organizasyon önerilir.
2. Bu klasördeki tüm dosyaları depoya yükleyin (`.github` klasörü dahil).
3. **Settings → Pages**: Source = *Deploy from a branch*, Branch = `main`, klasör = `/docs` → Save.
   Birkaç dakika sonra adres: `https://<kullanici>.github.io/makine-yayinlar/`
4. **Actions** sekmesi → "UNIS verisini güncelle" → **Run workflow**. Yeşil tik gelirse otomasyon çalışıyor.
5. Bölüm sitesindeki "Yayınlar" sayfasını düzenleyin, editörde **Kaynak** moduna geçin,
   eski iki `<img>` bloğunu silip şunu yapıştırın:

```html
<iframe src="https://<kullanici>.github.io/makine-yayinlar/"
        style="width:100%;height:2800px;border:0" loading="lazy"
        title="Makine Mühendisliği yayın istatistikleri"></iframe>
```

Parçaları ayrı yerlere koymak isterseniz:
- yalnızca grafik: `.../makine-yayinlar/?view=grafik` (height ≈ 650px)
- yalnızca öne çıkan yayınlar: `.../makine-yayinlar/?view=yayinlar` (height ≈ 2150px)

Yükseklik masaüstüne göre ölçülmüştür (20 makale). Telefonda içerik uzar; iframe içinde kaydırma çubuğu çıkar.

## Ayarlar (`scripts/fetch_unis.py` başı)

| Ayar | Varsayılan | Anlamı |
|---|---|---|
| `START_YEAR` | 2010 | Grafiğin başladığı yıl |
| `FEATURED_COUNT` | 20 | Öne çıkan yayın sayısı |
| `FEATURED_INDEXES` | SCI-E, SCI, SSCI | Öne çıkanlarda kabul edilen endeksler (ESCI eklenebilir) |
| `FEATURED_YEARS_BACK` | 1 | Bu yıl + önceki yıl |

Öne çıkan seçim kuralı: en yeni makaleler, her bölüm öğretim elemanı en fazla bir kez.

## Güvenlik önlemleri

- UNIS boş/eksik veri döndürürse (toplam %30'dan fazla düşerse) `data.json` **güncellenmez**,
  sitede son sağlam veri kalır ve Actions çalıştırması kırmızı görünür (GitHub e-posta ile bildirir).
- Günde bir kez, istekler arası 0,5 sn beklemeyle ~55 istek atılır.

## Bilinen riskler

- Kullanılan UNIS ucu belgelenmiş bir API değildir; UNIS arayüzü değişirse betik güncellenmelidir.
  Kalıcı çözüm için Bilgi İşlem'den resmi bir JSON ucu / onay istenmelidir.
- GitHub sunucuları yurt dışındadır. UNIS yurt dışı erişimi engellerse 4. adım başarısız olur;
  bu durumda betik üniversite içindeki bir bilgisayarda/sunucuda zamanlanmış görevle çalıştırılıp
  `docs/` klasörü üniversite sunucusundan yayınlanabilir.
