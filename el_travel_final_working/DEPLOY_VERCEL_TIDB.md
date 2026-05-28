# Deploy EL Travel ke Vercel + TiDB Cloud Starter

Panduan ini disiapkan untuk versi Flask + MySQL-compatible yang ada di project ini, dengan target:

- aplikasi bisa dibuka kapan pun tanpa laptop lokal harus menyala,
- deployment tetap ringan untuk tugas,
- data login, booking, pembayaran, dan backoffice tetap tersimpan di database cloud.

## 1. Siapkan database cloud

Project ini paling cocok memakai database MySQL-compatible jarak jauh. Untuk jalur gratis yang paling dekat dengan stack sekarang, gunakan **TiDB Cloud Starter**.

Yang perlu Anda siapkan dari dashboard database:

- `host`
- `port`
- `user`
- `password`
- `database`

## 2. Import database project

Di phpMyAdmin lokal atau client SQL Anda:

1. import `database_setup_final.sql`
2. lanjut import `database_refresh_update.sql`

Kalau database cloud sudah kosong, jalankan file yang sama ke database cloud itu.

## 3. Isi environment variable di Vercel

Tambahkan environment variable berikut di project Vercel:

- `SECRET_KEY`
- `DB_HOST`
- `DB_PORT`
- `DB_USER`
- `DB_PASSWORD`
- `DB_NAME`
- `DB_SSL_ENABLED=true`
- `DB_SSL_VERIFY_CERT=true`
- `DB_SSL_VERIFY_IDENTITY=true`

Atau pakai alias khusus TiDB:

- `TIDB_HOST`
- `TIDB_PORT`
- `TIDB_USER`
- `TIDB_PASSWORD`
- `TIDB_DATABASE`
- `TIDB_SSL_ENABLED=true`
- `TIDB_SSL_VERIFY_CERT=true`
- `TIDB_SSL_VERIFY_IDENTITY=true`

Untuk fitur tambahan, siapkan juga:

- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `SMTP_FROM_EMAIL`
- `SMTP_FROM_NAME`
- `SMTP_USE_SSL`
- `MIDTRANS_IS_PRODUCTION`
- `MIDTRANS_SERVER_KEY`
- `MIDTRANS_CLIENT_KEY`
- `COMPANY_QRIS_IMAGE_URL`

## 4. Struktur deploy yang sudah siap di project

Project ini sudah memiliki file yang relevan untuk Vercel:

- `vercel.json`
- `.vercelignore`
- `.python-version`
- `build_vercel_assets.py`
- `/healthz`

Route pengecekan cepat:

- `https://domain-anda.vercel.app/healthz`

Kalau database tersambung normal, route ini akan mengembalikan status sehat.

## 5. Deploy ke Vercel

1. push project ke GitHub
2. import repository ke Vercel
3. set semua environment variable
4. jalankan deploy

Setelah deploy berhasil, cek:

- homepage
- `/login`
- `/status-pesanan`
- `/backoffice/login`
- `/healthz`

## 6. Checklist setelah online

Pastikan poin ini dites lagi di domain online:

- user login
- booking paket biasa
- booking paket uji `Rp1`
- pembayaran manual bank / e-wallet / QRIS
- finance backoffice
- export CSV dari `/backoffice/keuangan`
- tambah / edit destinasi di backoffice
- promo aktif muncul di halaman publik

## 7. Catatan penting

- Jika Anda ingin pembayaran otomatis, isi kredensial Midtrans.
- Jika belum, sistem manual bank / e-wallet / QRIS tetap bisa dipakai.
- Tujuan dana perusahaan dikelola dari `company_payment_config.py`.
- Link kontak dan sosial media dikelola dari `company_links_config.py`.
