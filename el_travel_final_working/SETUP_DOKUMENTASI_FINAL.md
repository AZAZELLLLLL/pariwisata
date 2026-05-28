# 📋 EL TRAVEL - SETUP & DOKUMENTASI FINAL

**Version:** 2.0 FINAL
**Database:** pariwisataDb  
**Status:** ✅ READY TO DEPLOY

---

## 🎯 DAFTAR PERUBAHAN (UPDATES)

### ✅ FASE 1: DATABASE
- **Nama Database Diubah:** `pariwisata` → `pariwisataDb`
- **File SQL:** `database_setup_final.sql` (yang terbaru dan terakhir)
- **Struktur:** 7 tables dengan data 18 destinasi
- **Data:** Sudah include 18 destinasi wisata (lokal + internasional)

### ✅ FASE 2: NAVBAR
- **Improvement:** Navbar background tidak transparent lagi
- **Visibility:** Text navbar lebih jelas dengan text-shadow
- **Contrast:** Warna text jelas di background navy
- **Scroll Effect:** Bekerja sempurna saat user scroll

### ✅ FASE 3: PAYMENT SYSTEM (BARU!)
- **Route Baru:** `/pembayaran/<pemesanan_id>`
- **Method:** GET (show form) + POST (process payment)
- **Database:** Data pembayaran tersimpan di table `pembayaran`
- **Status Tracking:** pending → menunggu_verifikasi → berhasil
- **Metode:** Transfer, Kartu Kredit, QR Code, Cicilan
- **Konfirmasi:** Page `/konfirmasi_pembayaran/<pemesanan_id>`

### ✅ FASE 4: RATING SYSTEM (BARU!)
- **Route Baru:** `/review/<pemesanan_id>`
- **Method:** GET (show form) + POST (save rating)
- **Database:** Data rating tersimpan di table `rating_review`
- **Fields:** 
  - Rating Destinasi (1-5)
  - Rating Pelayanan (1-5)
  - Rating Keseluruhan (1-5)
  - Judul Review
  - Isi Review
- **Status:** pending → published (after admin approval)
- **Dynamic:** Rating tersimpan di DB, bukan di JSON/localStorage

### ✅ FASE 5: APP.PY LENGKAP
- **Database Connection:** Updated ke `pariwisataDb`
- **Error Handling:** Try-except di semua routes
- **Validation:** Input validation untuk semua form
- **Security:** Prepared statements untuk queries
- **API Endpoints:** `/api/destinasi/<id>` dan `/api/paket/<wisata_id>`
- **Error Pages:** 404.html dan 500.html sudah ada

### ✅ FASE 6: CSS NAVBAR FIX
- **Initial Background:** `rgba(26,39,68,0.7)` (not transparent)
- **Nav Link Color:** `rgba(255,255,255,0.95)` dengan text-shadow
- **Scroll Effect:** Background menjadi solid navy dengan shadow
- **Font Weight:** 500 untuk better readability

---

## 🚀 SETUP INSTRUCTIONS

### STEP 1: Database Setup

**Buka phpMyAdmin:**
```
http://localhost/phpmyadmin
```

**Pilih file sesuai kebutuhan:**
1. `database_setup_final.sql`
   Untuk fresh install / database baru dari nol.
2. `database_refresh_update.sql`
   Untuk update master data, gambar destinasi, paket, dan tabel operasional owner tanpa menghapus transaksi lama.

**Import Database:**
1. Klik tab **Import**
2. Pilih file SQL yang sesuai kebutuhan Anda
3. Klik **Go**
4. Tunggu sampai selesai ✓

**Verify:**
```bash
mysql -u root -p
USE pariwisataDb;
SELECT COUNT(*) FROM wisata;
# Should return: 21
```

**Catatan lokal Codex saat ini:**
- File `.env` lokal sudah diarahkan ke database kerja `pariwisatadb_codex_live`.
- Database itu sudah lolos pengujian end-to-end untuk flow user dan backoffice.
- Jika Anda ingin kembali memakai nama database lain, cukup ubah `DB_NAME` di file `.env`.

### STEP 2: Install Python Dependencies

```bash
cd ELproject/
pip install -r requirements.txt
```

### STEP 3: Aktifkan OTP Gmail Asli

1. Duplikat file `.env.example` menjadi `.env`
2. Isi Gmail pengirim pada `SMTP_USERNAME`
3. Isi Google App Password 16 digit pada `SMTP_PASSWORD`
4. Pastikan `SMTP_FROM_EMAIL` sama dengan Gmail pengirim
5. Untuk Gmail biasa, biarkan:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_SSL=false
```

**Catatan penting:**
- Aplikasi ini **tidak** meminta password Gmail user untuk login.
- Password akun tetap dikelola Google.
- Yang dipakai di server hanya **App Password Gmail pengirim** untuk mengirim kode OTP 6 digit ke inbox user.

### STEP 4: Jalankan Flask App

```bash
python app.py
```

**Expected Output:**
```
* Running on http://127.0.0.1:5000
* Debug mode: on
```

### STEP 5: Open Browser

```
http://localhost:5000
```

### STEP 6: Aktifkan Dashboard Owner / Staff

**URL backoffice:**
```
http://localhost:5000/backoffice/login
```

**Kalau belum ada akun staff sama sekali:**
1. Buka:
   `http://localhost:5000/backoffice/setup-owner`
2. Buat akun owner pertama
3. Setelah itu Anda akan langsung diarahkan ke dashboard internal

**Fungsi dashboard backoffice:**
- melihat antrean pesanan customer
- verifikasi pembayaran
- update status tiket, voucher, dan dokumen
- memberi catatan internal tim
- menandai pesanan selesai
- menambah destinasi baru langsung ke MySQL
- mengedit destinasi yang sudah ada
- menambah paket dan info keberangkatan untuk setiap destinasi
- CRUD promo / diskon destinasi
- melihat riwayat pembayaran dan rekap keuangan

**URL penting backoffice:**
- `/backoffice/login`
- `/backoffice/setup-owner`
- `/backoffice`
- `/backoffice/pesanan`
- `/backoffice/destinasi`
- `/backoffice/promo`
- `/backoffice/keuangan`
- `/backoffice/staff`

### STEP 7: File Konfigurasi yang Sekarang Dipakai

**Link perusahaan dan sosial media:**
- `company_links_config.py`
  Pusat untuk WhatsApp, telepon, email, Instagram, TikTok, YouTube, dan Facebook.

**Konten halaman kontak:**
- `contact_config.py`
  Khusus judul, label, placeholder, dan copy halaman kontak.

**Tujuan pembayaran perusahaan:**
- `company_payment_config.py`
  Khusus rekening bank, ShopeePay, DANA, GoPay, QRIS, dan label kanal pembayaran.

**Copy halaman pembayaran:**
- `payment_config.py`
  Khusus teks bantuan, catatan payment, dan paket uji Rp1.

### STEP 8: Target Hosting Gratis yang Disiapkan

**Target deployment yang sekarang saya siapkan di project:** `Vercel Hobby + Aiven MySQL Free`

**Kenapa kombinasi ini yang paling cocok untuk project sekarang:**
- aplikasi ini tetap memakai Flask sehingga bisa berjalan sebagai Python function di Vercel
- user bisa mengakses website kapan pun tanpa laptop lokal menyala
- akun login, pesanan, pembayaran, promo, dan backoffice tetap tersimpan di database cloud MySQL
- Anda tidak perlu memindahkan seluruh query SQL ke Firebase atau mengubah stack utama ke SPA

**File yang sudah disiapkan:**
- `vercel.json`
- `.vercelignore`
- `.python-version`
- `build_vercel_assets.py`

**Catatan penting:**
- Vercel cocok untuk aplikasi Flask sebagai function.
- Untuk aset statis, Vercel lebih cocok memakai folder `public/`, karena itu project ini sekarang punya build script yang menyalin `static/` ke `public/static`.
- Agar aplikasi benar-benar bisa diakses kapan pun tanpa laptop menyala, database juga harus dipindah ke server cloud.
- Koneksi database sekarang sudah mendukung:
  - `DB_PORT`
  - `DB_SSL_MODE`
  - `DB_SSL_ENABLED`
  - `DB_SSL_VERIFY_CERT`
  - `DB_SSL_VERIFY_IDENTITY`
  - `DB_SSL_CA`
  - `DB_SSL_CA_CONTENT`

**Kenapa Firebase tidak saya jadikan target utama backend ini:**
- Firebase Hosting utamanya untuk static / single-page app.
- Firebase App Hosting untuk backend dinamis sekarang membutuhkan Blaze plan.
- Karena project ini adalah Flask + dashboard admin + payment flow + database SQL, Vercel lebih dekat ke arsitektur aplikasi yang sekarang.

**Alur deploy gratis yang disarankan:**
1. Buat database cloud MySQL gratis di Aiven
2. Import:
   - `database_setup_final.sql`
   - lalu `database_refresh_update.sql`
3. Isi environment variable produksi:
   - `DB_HOST`
   - `DB_PORT`
   - `DB_USER`
   - `DB_PASSWORD`
   - `DB_NAME`
   - `DB_SSL_ENABLED=true`
   - `DB_SSL_MODE=require`
   - `DB_SSL_CA_CONTENT`
   - `SECRET_KEY`
   - `SMTP_*`
   - `MIDTRANS_*` jika gateway dipakai
4. Jalankan build aset:
   `python build_vercel_assets.py`
5. Deploy ke Vercel dari root project ini

**Fallback demo lokal kalau database masih di laptop:**
- Anda tetap bisa memakai Cloudflare Tunnel untuk demo cepat.
- Cocok untuk presentasi, tetapi bukan hosting permanen karena laptop harus tetap menyala.

**Referensi resmi yang dipakai untuk keputusan ini:**
- Vercel Python runtime: https://vercel.com/docs/functions/runtimes/python
- Vercel Hobby plan: https://vercel.com/docs/plans/hobby
- Firebase Hosting pricing: https://firebase.google.com/docs/hosting/usage-quotas-pricing
- Firebase App Hosting costs: https://firebase.google.com/docs/app-hosting/costs
- Aiven MySQL free tier: https://aiven.io/docs/products/mysql/concepts/mysql-free-tier
- Aiven connect docs: https://aiven.io/docs/products/mysql/howto/connect-from-mysql-workbench

---

## 🔧 KEY FEATURES

### Login User
**Flow:**
1. User membuka `/login`
2. Yang tampil utama hanya panel `Akun Sudah Ada`
3. User memasukkan Gmail + password akun EL Travel
4. User menyelesaikan captcha hitung singkat
5. Jika akun ditemukan dan password cocok, user langsung login
6. Jika akun belum ditemukan, sistem menampilkan pop-up untuk mendaftarkan akun baru
7. Akun baru diaktivasi memakai kode 6 digit yang dikirim ke Gmail

**Catatan keamanan:**
- query login tetap memakai parameterized SQL
- captcha dipakai sebagai filter anti-bot tambahan, bukan pengganti proteksi SQL injection
- password user disimpan dalam bentuk hash, bukan plaintext

### Payment System
**Flow:**
1. User booking paket → Insert ke table `pemesanan`
2. Redirect ke `/pembayaran/<pemesanan_id>`
3. User pilih metode pembayaran → Insert ke table `pembayaran`
4. Status: pending → menunggu_verifikasi → berhasil
5. Konfirmasi page menampilkan detail pembayaran

**Database:**
```sql
SELECT * FROM pembayaran WHERE pemesanan_id = 1;
```

**Update terbaru flow pembayaran:**
- metode yang tersedia sekarang mencakup transfer bank, QRIS, ShopeePay, DANA, dan GoPay
- jika key gateway aktif, aplikasi juga bisa membuat transaksi Midtrans
- histori maintenance pembayaran bisa dilihat dari `/backoffice/keuangan`
- audit pembayaran detail tersimpan di tabel `payment_audit_log`

```sql
SELECT * FROM payment_audit_log WHERE pemesanan_id = 1;
```

### Rating System
**Flow:**
1. User setelah membayar bisa rate di `/review/<pemesanan_id>`
2. Input rating 1-5 untuk: destinasi, pelayanan, keseluruhan
3. Buat judul dan isi review
4. Insert ke table `rating_review` dengan status 'pending'
5. Setelah admin approve → status menjadi 'published'
6. Rating muncul di halaman detail destinasi

**Database:**
```sql
SELECT * FROM rating_review 
WHERE pemesanan_id = 1 AND status_review = 'published';
```

---

## 📁 PROJECT STRUCTURE

```
ELproject/
├── app.py                      ← MAIN Flask app (UPDATED!)
├── requirements.txt            ← Python dependencies
├── database_setup_final.sql    ← Database file (USE THIS!)
├── static/
│   ├── css/style.css          ← Navbar CSS fixed ✓
│   └── js/main.js
└── templates/
    ├── base.html
    ├── index.html              ← Homepage
    ├── destinasi.html          ← Destinasi list
    ├── detail.html             ← Detail wisata
    ├── pesan.html              ← Booking form
    ├── pembayaran.html         ← Payment form (NEW!)
    ├── konfirmasi_pembayaran.html ← Payment confirmation
    ├── review.html             ← Rating form (NEW!)
    ├── riwayat.html            ← Order history
    ├── kontak.html
    ├── tentang.html
    ├── 404.html                ← Error page
    └── 500.html                ← Error page
```

---

## 🔒 SECURITY NOTES

✅ **Prepared Statements:** Semua query menggunakan %s placeholder
✅ **Input Validation:** Email, phone, amounts di-validate
✅ **Error Messages:** User-friendly, tidak expose DB details
✅ **Session Security:** Flask secret key sudah diset

---

## ⚠️ IMPORTANT NOTES

### Database Name
**PERHATIAN:** Database harus bernama **`pariwisataDb`** (bukan `pariwisata`)
- app.py sudah set ke `pariwisataDb`
- File SQL juga sudah create database ini

### Database File
**GUNAKAN:** `database_setup_final.sql`
- Jangan gunakan `database_setup_updated.sql`
- File final sudah punya semua struktur + data

### Routes di app.py
```python
@app.route('/pembayaran/<int:pemesanan_id>')  # NEW
@app.route('/konfirmasi_pembayaran/<int:pemesanan_id>')  # NEW
@app.route('/review/<int:pemesanan_id>')  # NEW
```

---

## 🧪 TESTING CHECKLIST

### Homepage Test
- [ ] Navbar visible dengan warna benar
- [ ] 4 filter buttons bekerja
- [ ] Destinasi cards muncul
- [ ] Navbar scroll effect jalan

### Booking Test
- [ ] Click destinasi → detail page
- [ ] Click paket → booking form
- [ ] Form validation bekerja
- [ ] Submit → redirect ke payment page

### Payment Test
- [ ] Payment form muncul
- [ ] Semua metode ada (transfer, kartu, QR, cicilan)
- [ ] Submit → data terseimpan di table `pembayaran`
- [ ] Konfirmasi page muncul

### Rating Test
- [ ] dari riwayat, bisa klik rate
- [ ] Form rating muncul
- [ ] Input rating 1-5
- [ ] Submit → data tersimpan di table `rating_review`
- [ ] Flash message "Terima kasih" muncul

### Database Test
```bash
mysql -u root -p
USE pariwisataDb;

# Check bookings
SELECT COUNT(*) FROM pemesanan;

# Check payments
SELECT COUNT(*) FROM pembayaran;

# Check ratings
SELECT COUNT(*) FROM rating_review;
```

---

## 🐛 TROUBLESHOOTING

### Error: "Unknown database 'pariwisataDb'"
**Solution:** Import `database_setup_final.sql` lagi di phpMyAdmin

### Error: "Table 'pariwisataDb.pembayaran' doesn't exist"
**Solution:** Gunakan file SQL terbaru yang ada semua tables

### Navbar masih tidak terlihat
**Solution:** Clear browser cache (Ctrl+Shift+Del) kemudian refresh (F5)

### Payment tidak tersimpan
**Solution:** Check MySQL connection di app.py line 13
```python
database='pariwisataDb'  # Pastikan ini benar!
```

### Rating tidak muncul
**Solution:** Rating dengan status 'pending' tidak ditampilkan
- Hanya published reviews yang muncul
- Admin perlu approve terlebih dahulu

---

## 📊 DATABASE SCHEMA

### Tabel Pembayaran
```sql
CREATE TABLE pembayaran (
    id INT PRIMARY KEY,
    pemesanan_id INT (FK),
    metode_pembayaran ENUM('transfer','kartu_kredit','qr_code','cicilan'),
    status_pembayaran ENUM('pending','berhasil','gagal','menunggu_verifikasi'),
    tanggal_pembayaran DATETIME,
    jumlah_dibayar DECIMAL(15,0),
    keterangan TEXT,
    created_at DATETIME,
    updated_at DATETIME
);
```

### Tabel Rating Review
```sql
CREATE TABLE rating_review (
    id INT PRIMARY KEY,
    pemesanan_id INT (FK UNIQUE),
    destinasi_id INT (FK),
    nama_pengguna VARCHAR(255),
    rating_destinasi DECIMAL(2,1),
    rating_pelayanan DECIMAL(2,1),
    rating_keseluruhan DECIMAL(2,1),
    judul_review VARCHAR(255),
    isi_review TEXT,
    status_review ENUM('pending','published','rejected'),
    tanggal_review DATETIME,
    tanggal_publish DATETIME
);
```

---

## 💡 TIPS

1. **Testing Payment:** Gunakan data dummy, tidak perlu uang asli
2. **Testing Rating:** Rating bisa diupdate berkali-kali
3. **Admin Panel:** Tidak ada di versi ini (bisa dibuat kemudian)
4. **Email Verification:** Belum implement (bisa ditambah nanti)

---

## ✨ FITUR YANG SUDAH COMPLETE

✅ Homepage dengan 4 filter categories
✅ Detail destinasi dengan reviews
✅ Booking form dengan validation
✅ **Payment system dengan tracking** (NEW)
✅ **Rating system dengan storage di DB** (NEW)
✅ Order history
✅ Responsive navbar
✅ Error pages (404, 500)
✅ API endpoints untuk AJAX

---

## 🎁 BONUS FEATURES

1. **API Endpoints:** `/api/destinasi/<id>` dan `/api/paket/<wisata_id>`
2. **Dynamic Rating:** Tersimpan di database, bukan hardcoded
3. **Payment Tracking:** Admin bisa track pembayaran per booking
4. **Review Publishing:** Moderation system untuk reviews

---

## 📞 SUPPORT

Jika ada error atau bug:
1. Check error message di Flask console
2. Verify database connection
3. Clear browser cache
4. Check MySQL running

---

**Version:** 2.0 FINAL
**Release Date:** 11 Maret 2026
**Status:** ✅ PRODUCTION READY

**Semua fitur sudah tested dan siap jalan!** 🚀
