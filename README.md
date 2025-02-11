# README

## Instalasi Dependencies

Sebelum menjalankan proyek, pastikan untuk menginstal dependencies yang diperlukan. Jalankan perintah berikut:

```sh
pip install -r requirements.txt
```

Jika `requirements.txt` belum tersedia, instal paket-paket berikut secara manual:

```sh
pip install selenium webdriver-manager requests flask apscheduler
```

## File yang Digunakan

### 1. idxGetEmiten.py
Script ini digunakan untuk mengambil data saham dari situs IDX dan menyimpannya ke dalam file JSON.

### 2. apiTrending.py
Script ini digunakan untuk scraping berita saham dari Google News dan mengirim notifikasi ke bot Telegram.

## Menjalankan Script dengan PM2
Untuk memastikan script berjalan di latar belakang dan otomatis restart jika terjadi crash, gunakan `pm2`.

### Instalasi PM2
Jika belum terinstal, jalankan perintah berikut:

```sh
npm install -g pm2
```

### Menjalankan Script
Jalankan kedua file dengan PM2:

```sh
pm2 start idxGetEmiten.py --interpreter python3 --name idx-emiten
pm2 start apiTrending.py --interpreter python3 --name api-trending
```

### Melihat Status
Untuk melihat status proses yang berjalan:

```sh
pm2 status
```

### Menyimpan Konfigurasi agar Otomatis Berjalan saat Restart Server
```sh
pm2 save
pm2 startup
```

### Menghentikan atau Menghapus Script
```sh
pm2 stop idx-emiten api-trending
pm2 delete idx-emiten api-trending
```

## Catatan
- Pastikan Python 3.x sudah terinstal di sistem.
- Selenium memerlukan `chromedriver`, pastikan sudah terpasang dengan `webdriver-manager`.
- Jika ada kendala, cek log dengan perintah:

```sh
pm2 logs idx-emiten
pm2 logs api-trending
```

