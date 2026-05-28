-- =============================================
-- EL Travel - Safe Database Refresh / Update
-- Database Name: pariwisataDb
-- Tujuan:
-- 1. Menambah kolom media destinasi yang lebih akurat
-- 2. Menambah tabel operasional owner / staff
-- 3. Memperbarui master data destinasi dan paket tanpa drop tabel transaksi
-- 4. Aman untuk import ulang di phpMyAdmin pada database yang sudah berjalan
-- =============================================

CREATE DATABASE IF NOT EXISTS pariwisataDb
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE pariwisataDb;

CREATE TABLE IF NOT EXISTS akun_user (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(190) NOT NULL UNIQUE,
    nama_lengkap VARCHAR(120) NOT NULL,
    jenis_kelamin VARCHAR(40) DEFAULT 'Tidak ingin menyebutkan',
    telepon VARCHAR(25),
    tanggal_lahir DATE NULL,
    kota_domisili VARCHAR(120),
    password_hash VARCHAR(255) NOT NULL,
    email_verified TINYINT(1) DEFAULT 0,
    verification_code_hash VARCHAR(64),
    verification_expires_at DATETIME NULL,
    verification_attempts INT DEFAULT 0,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    last_login_at DATETIME NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS akun_staff (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nama_lengkap VARCHAR(120) NOT NULL,
    email VARCHAR(190) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('owner', 'finance', 'operasional', 'customer_service') DEFAULT 'operasional',
    is_active TINYINT(1) DEFAULT 1,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    last_login_at DATETIME NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

ALTER TABLE destinasi ADD COLUMN IF NOT EXISTS negara VARCHAR(120) NULL AFTER lokasi;
ALTER TABLE destinasi ADD COLUMN IF NOT EXISTS benua VARCHAR(60) NULL AFTER negara;
ALTER TABLE destinasi ADD COLUMN IF NOT EXISTS thumbnail_foto VARCHAR(600) NULL AFTER foto;
ALTER TABLE destinasi ADD COLUMN IF NOT EXISTS moment_foto VARCHAR(600) NULL AFTER thumbnail_foto;
ALTER TABLE destinasi ADD COLUMN IF NOT EXISTS foto_source_url VARCHAR(1000) NULL AFTER moment_foto;
ALTER TABLE destinasi ADD COLUMN IF NOT EXISTS foto_source_label VARCHAR(255) NULL AFTER foto_source_url;
ALTER TABLE destinasi ADD COLUMN IF NOT EXISTS best_time VARCHAR(255) NULL AFTER foto_source_label;
ALTER TABLE destinasi ADD COLUMN IF NOT EXISTS display_order INT NULL AFTER total_review;
ALTER TABLE destinasi ADD COLUMN IF NOT EXISTS is_active TINYINT(1) DEFAULT 1 AFTER display_order;

ALTER TABLE wisata ADD COLUMN IF NOT EXISTS negara VARCHAR(120) NULL AFTER lokasi;
ALTER TABLE wisata ADD COLUMN IF NOT EXISTS benua VARCHAR(60) NULL AFTER negara;
ALTER TABLE wisata ADD COLUMN IF NOT EXISTS thumbnail_foto VARCHAR(600) NULL AFTER foto;
ALTER TABLE wisata ADD COLUMN IF NOT EXISTS moment_foto VARCHAR(600) NULL AFTER thumbnail_foto;
ALTER TABLE wisata ADD COLUMN IF NOT EXISTS foto_source_url VARCHAR(1000) NULL AFTER moment_foto;
ALTER TABLE wisata ADD COLUMN IF NOT EXISTS foto_source_label VARCHAR(255) NULL AFTER foto_source_url;
ALTER TABLE wisata ADD COLUMN IF NOT EXISTS best_time VARCHAR(255) NULL AFTER foto_source_label;
ALTER TABLE wisata ADD COLUMN IF NOT EXISTS display_order INT NULL AFTER rating;
ALTER TABLE wisata ADD COLUMN IF NOT EXISTS is_active TINYINT(1) DEFAULT 1 AFTER display_order;

ALTER TABLE tipe_paket ADD COLUMN IF NOT EXISTS kode_paket VARCHAR(80) NULL AFTER wisata_id;
ALTER TABLE tipe_paket ADD COLUMN IF NOT EXISTS jenis_paket VARCHAR(40) DEFAULT 'custom' AFTER nama_paket;
ALTER TABLE tipe_paket ADD COLUMN IF NOT EXISTS status_paket VARCHAR(30) DEFAULT 'aktif' AFTER max_orang;
ALTER TABLE tipe_paket ADD COLUMN IF NOT EXISTS meeting_point VARCHAR(255) NULL AFTER status_paket;
ALTER TABLE tipe_paket ADD COLUMN IF NOT EXISTS keberangkatan_info TEXT NULL AFTER meeting_point;
ALTER TABLE tipe_paket ADD COLUMN IF NOT EXISTS kuota_total INT DEFAULT 20 AFTER keberangkatan_info;
ALTER TABLE tipe_paket ADD COLUMN IF NOT EXISTS kuota_tersedia INT DEFAULT 20 AFTER kuota_total;
ALTER TABLE tipe_paket ADD COLUMN IF NOT EXISTS is_featured TINYINT(1) DEFAULT 0 AFTER kuota_tersedia;

ALTER TABLE pemesanan ADD COLUMN IF NOT EXISTS kode_pemesanan VARCHAR(30) NULL AFTER id;
ALTER TABLE pemesanan ADD COLUMN IF NOT EXISTS sumber_pesanan VARCHAR(40) DEFAULT 'website' AFTER catatan;

ALTER TABLE pembayaran ADD COLUMN IF NOT EXISTS gateway_provider VARCHAR(40) NULL AFTER bukti_pembayaran;
ALTER TABLE pembayaran ADD COLUMN IF NOT EXISTS gateway_order_id VARCHAR(120) NULL AFTER gateway_provider;
ALTER TABLE pembayaran ADD COLUMN IF NOT EXISTS gateway_transaction_id VARCHAR(120) NULL AFTER gateway_order_id;
ALTER TABLE pembayaran ADD COLUMN IF NOT EXISTS gateway_status VARCHAR(40) NULL AFTER gateway_transaction_id;
ALTER TABLE pembayaran ADD COLUMN IF NOT EXISTS snap_token VARCHAR(255) NULL AFTER gateway_status;
ALTER TABLE pembayaran ADD COLUMN IF NOT EXISTS redirect_url VARCHAR(600) NULL AFTER snap_token;
ALTER TABLE pembayaran ADD COLUMN IF NOT EXISTS channel_code VARCHAR(80) NULL AFTER redirect_url;
ALTER TABLE pembayaran ADD COLUMN IF NOT EXISTS payment_reference VARCHAR(120) NULL AFTER channel_code;
ALTER TABLE pembayaran ADD COLUMN IF NOT EXISTS paid_at DATETIME NULL AFTER payment_reference;
ALTER TABLE pembayaran ADD COLUMN IF NOT EXISTS verified_by_staff_id INT NULL AFTER paid_at;
ALTER TABLE pembayaran ADD COLUMN IF NOT EXISTS verified_at DATETIME NULL AFTER verified_by_staff_id;
ALTER TABLE pembayaran ADD COLUMN IF NOT EXISTS verification_note TEXT NULL AFTER verified_at;
ALTER TABLE pembayaran ADD COLUMN IF NOT EXISTS raw_response_json LONGTEXT NULL AFTER verification_note;
ALTER TABLE pembayaran MODIFY COLUMN metode_pembayaran VARCHAR(40) DEFAULT 'bank_transfer';

ALTER TABLE payment_detail ADD COLUMN IF NOT EXISTS detail_key VARCHAR(50) NULL AFTER pembayaran_id;
ALTER TABLE payment_detail ADD COLUMN IF NOT EXISTS detail_value VARCHAR(255) NULL AFTER detail_key;

CREATE TABLE IF NOT EXISTS operasional_pesanan (
    id INT AUTO_INCREMENT PRIMARY KEY,
    pemesanan_id INT NOT NULL UNIQUE,
    kode_booking VARCHAR(30) NOT NULL,
    status_operasional ENUM(
        'baru', 'menunggu_pembayaran', 'verifikasi_pembayaran',
        'siapkan_tiket', 'siapkan_voucher', 'siap_berangkat',
        'selesai', 'dibatalkan'
    ) DEFAULT 'baru',
    status_tiket ENUM('belum_dibuat', 'diproses', 'terbit') DEFAULT 'belum_dibuat',
    status_voucher ENUM('belum_dibuat', 'diproses', 'terkirim') DEFAULT 'belum_dibuat',
    status_dokumen ENUM('belum_lengkap', 'menunggu_user', 'lengkap') DEFAULT 'belum_lengkap',
    assigned_staff_id INT NULL,
    payment_checked_by INT NULL,
    payment_checked_at DATETIME NULL,
    deadline_follow_up DATETIME NULL,
    catatan_internal TEXT,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    FOREIGN KEY (pemesanan_id) REFERENCES pemesanan(id) ON DELETE CASCADE,
    FOREIGN KEY (assigned_staff_id) REFERENCES akun_staff(id) ON DELETE SET NULL,
    FOREIGN KEY (payment_checked_by) REFERENCES akun_staff(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS pemesanan_status_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    pemesanan_id INT NOT NULL,
    actor_type ENUM('system', 'customer', 'staff') DEFAULT 'system',
    actor_name VARCHAR(120),
    status_label VARCHAR(120) NOT NULL,
    message VARCHAR(600),
    created_at DATETIME NOT NULL,
    FOREIGN KEY (pemesanan_id) REFERENCES pemesanan(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS detail_peserta_pesanan (
    id INT AUTO_INCREMENT PRIMARY KEY,
    pemesanan_id INT NOT NULL,
    nama_peserta VARCHAR(120) NOT NULL,
    jenis_kelamin VARCHAR(40),
    tanggal_lahir DATE NULL,
    kewarganegaraan VARCHAR(80) DEFAULT 'Indonesia',
    no_identitas VARCHAR(120),
    status_dokumen ENUM('belum_lengkap', 'menunggu_user', 'lengkap') DEFAULT 'belum_lengkap',
    catatan TEXT,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    FOREIGN KEY (pemesanan_id) REFERENCES pemesanan(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS payment_audit_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    pembayaran_id INT NOT NULL,
    pemesanan_id INT NOT NULL,
    actor_type ENUM('system', 'customer', 'staff') DEFAULT 'system',
    actor_name VARCHAR(120),
    event_label VARCHAR(160) NOT NULL,
    message VARCHAR(700),
    created_at DATETIME NOT NULL,
    FOREIGN KEY (pembayaran_id) REFERENCES pembayaran(id) ON DELETE CASCADE,
    FOREIGN KEY (pemesanan_id) REFERENCES pemesanan(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS promo_destinasi (
    id INT AUTO_INCREMENT PRIMARY KEY,
    wisata_id INT NOT NULL,
    promo_name VARCHAR(160) NOT NULL,
    promo_label VARCHAR(80) NULL,
    description TEXT NULL,
    discount_type ENUM('percent', 'amount') DEFAULT 'percent',
    discount_value INT NOT NULL,
    starts_at DATETIME NOT NULL,
    ends_at DATETIME NOT NULL,
    is_active TINYINT(1) DEFAULT 1,
    created_by_staff_id INT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    FOREIGN KEY (wisata_id) REFERENCES wisata(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by_staff_id) REFERENCES akun_staff(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

DROP TEMPORARY TABLE IF EXISTS tmp_destination_seed;
CREATE TEMPORARY TABLE tmp_destination_seed (
    nama VARCHAR(255) PRIMARY KEY,
    lokasi VARCHAR(255) NOT NULL,
    negara VARCHAR(120) NOT NULL,
    benua VARCHAR(60) NOT NULL,
    deskripsi TEXT,
    foto VARCHAR(600),
    thumbnail_foto VARCHAR(600),
    moment_foto VARCHAR(600),
    foto_source_url VARCHAR(1000),
    foto_source_label VARCHAR(255),
    maps_url VARCHAR(1000),
    rating DECIMAL(2,1) DEFAULT 4.5,
    tipe ENUM('lokal','internasional') DEFAULT 'lokal',
    kategori VARCHAR(100),
    total_review INT DEFAULT 0,
    best_time VARCHAR(255),
    display_order INT DEFAULT 1,
    is_active TINYINT(1) DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO tmp_destination_seed (
    nama, lokasi, negara, benua, deskripsi, foto, thumbnail_foto, moment_foto,
    foto_source_url, foto_source_label, maps_url, rating, tipe, kategori,
    total_review, best_time, display_order, is_active
) VALUES
('Labuan Bajo', 'Labuan Bajo, Nusa Tenggara Timur', 'Indonesia', 'Asia', 'Labuan Bajo menjadi pintu gerbang utama menuju Taman Nasional Komodo, pengalaman sailing trip, dan lanskap laut Flores yang sangat kuat secara visual.', 'https://upload.wikimedia.org/wikipedia/commons/4/45/Labuan_Bajo%2C_a_port_in_West_Flores%2C_Nusa_Tenggara%2C_Indonesia%3B_January_2020.jpg', 'https://upload.wikimedia.org/wikipedia/commons/thumb/4/45/Labuan_Bajo%2C_a_port_in_West_Flores%2C_Nusa_Tenggara%2C_Indonesia%3B_January_2020.jpg/330px-Labuan_Bajo%2C_a_port_in_West_Flores%2C_Nusa_Tenggara%2C_Indonesia%3B_January_2020.jpg', 'https://upload.wikimedia.org/wikipedia/commons/4/45/Labuan_Bajo%2C_a_port_in_West_Flores%2C_Nusa_Tenggara%2C_Indonesia%3B_January_2020.jpg', 'https://en.wikipedia.org/wiki/Labuan_Bajo', 'Wikipedia - Labuan Bajo', 'https://maps.google.com/?q=Labuan+Bajo+Flores+Indonesia', 4.9, 'lokal', 'Bahari', 0, 'Sunrise pelabuhan dan sore menjelang golden hour.', 1, 1),
('Raja Ampat', 'Raja Ampat, Papua Barat', 'Indonesia', 'Asia', 'Raja Ampat menghadirkan salah satu kombinasi terbaik antara diving, island hopping, dan panorama gugusan pulau karst di Indonesia.', 'https://upload.wikimedia.org/wikipedia/commons/a/ae/Raja_Ampat%2C_West_Papua%2C_Indonesia.jpg', 'https://upload.wikimedia.org/wikipedia/commons/thumb/a/ae/Raja_Ampat%2C_West_Papua%2C_Indonesia.jpg/330px-Raja_Ampat%2C_West_Papua%2C_Indonesia.jpg', 'https://upload.wikimedia.org/wikipedia/commons/a/ae/Raja_Ampat%2C_West_Papua%2C_Indonesia.jpg', 'https://en.wikipedia.org/wiki/Raja_Ampat_Regency', 'Wikipedia - Raja Ampat Regency', 'https://maps.google.com/?q=Raja+Ampat+Papua+Barat+Indonesia', 5.0, 'lokal', 'Bahari', 0, 'Musim terbaik Oktober sampai April dengan laut lebih bersahabat.', 2, 1),
('Candi Borobudur', 'Magelang, Jawa Tengah', 'Indonesia', 'Asia', 'Borobudur adalah candi Buddha terbesar di dunia dan menjadi tujuan utama untuk wisata budaya, arsitektur, dan sejarah Jawa.', 'https://upload.wikimedia.org/wikipedia/commons/2/25/Pradaksina.jpg', 'https://upload.wikimedia.org/wikipedia/commons/thumb/2/25/Pradaksina.jpg/330px-Pradaksina.jpg', 'https://upload.wikimedia.org/wikipedia/commons/2/25/Pradaksina.jpg', 'https://en.wikipedia.org/wiki/Borobudur', 'Wikipedia - Borobudur', 'https://maps.google.com/?q=Borobudur+Magelang+Jawa+Tengah', 4.8, 'lokal', 'Budaya', 0, 'Pagi hari sebelum ramai pengunjung dan saat kabut tipis masih turun.', 3, 1),
('Danau Toba', 'Danau Toba, Sumatera Utara', 'Indonesia', 'Asia', 'Danau Toba menghadirkan bentang kaldera raksasa, udara yang sejuk, dan pengalaman budaya Batak yang kuat.', 'https://upload.wikimedia.org/wikipedia/commons/c/c4/Lake_Toba_and_the_surrounding_hills.jpg', 'https://upload.wikimedia.org/wikipedia/commons/thumb/c/c4/Lake_Toba_and_the_surrounding_hills.jpg/330px-Lake_Toba_and_the_surrounding_hills.jpg', 'https://upload.wikimedia.org/wikipedia/commons/c/c4/Lake_Toba_and_the_surrounding_hills.jpg', 'https://en.wikipedia.org/wiki/Lake_Toba', 'Wikipedia - Lake Toba', 'https://maps.google.com/?q=Danau+Toba+Sumatera+Utara', 4.7, 'lokal', 'Alam', 0, 'Pagi cerah dan sore hari saat cahaya lembut menyapu permukaan danau.', 4, 1),
('Pulau Komodo', 'Pulau Komodo, Nusa Tenggara Timur', 'Indonesia', 'Asia', 'Pulau Komodo cocok untuk traveler yang ingin melihat habitat komodo, trekking savana, dan teluk-teluk eksotis dalam satu perjalanan.', 'https://upload.wikimedia.org/wikipedia/commons/e/e3/Komodo_Island_north_aerial.jpg', 'https://upload.wikimedia.org/wikipedia/commons/thumb/e/e3/Komodo_Island_north_aerial.jpg/330px-Komodo_Island_north_aerial.jpg', 'https://upload.wikimedia.org/wikipedia/commons/e/e3/Komodo_Island_north_aerial.jpg', 'https://en.wikipedia.org/wiki/Komodo_(island)', 'Wikipedia - Komodo Island', 'https://maps.google.com/?q=Pulau+Komodo+Indonesia', 4.9, 'lokal', 'Petualangan', 0, 'Musim kemarau dengan langit lebih bersih dan jalur trekking lebih nyaman.', 5, 1),
('Gunung Bromo', 'Probolinggo, Jawa Timur', 'Indonesia', 'Asia', 'Gunung Bromo menawarkan salah satu lanskap sunrise paling ikonik di Indonesia, lengkap dengan lautan pasir dan siluet pegunungan.', 'https://upload.wikimedia.org/wikipedia/commons/8/8e/Bromo-Semeru-Batok-Widodaren.jpg', 'https://upload.wikimedia.org/wikipedia/commons/thumb/8/8e/Bromo-Semeru-Batok-Widodaren.jpg/330px-Bromo-Semeru-Batok-Widodaren.jpg', 'https://upload.wikimedia.org/wikipedia/commons/8/8e/Bromo-Semeru-Batok-Widodaren.jpg', 'https://en.wikipedia.org/wiki/Mount_Bromo', 'Wikipedia - Mount Bromo', 'https://maps.google.com/?q=Gunung+Bromo+Jawa+Timur', 4.8, 'lokal', 'Petualangan', 0, 'Berangkat dini hari untuk mengejar sunrise terbaik.', 6, 1),
('Kawah Ijen', 'Banyuwangi, Jawa Timur', 'Indonesia', 'Asia', 'Kawah Ijen terkenal dengan jalur pendakian malam hari, fenomena blue fire, dan pemandangan crater lake yang sangat khas.', 'https://upload.wikimedia.org/wikipedia/commons/1/16/Sulfur_mining_in_Kawah_Ijen_-_Indonesia_-_20110608.jpg', 'https://upload.wikimedia.org/wikipedia/commons/thumb/1/16/Sulfur_mining_in_Kawah_Ijen_-_Indonesia_-_20110608.jpg/330px-Sulfur_mining_in_Kawah_Ijen_-_Indonesia_-_20110608.jpg', 'https://upload.wikimedia.org/wikipedia/commons/1/16/Sulfur_mining_in_Kawah_Ijen_-_Indonesia_-_20110608.jpg', 'https://en.wikipedia.org/wiki/Ijen', 'Wikipedia - Ijen', 'https://maps.google.com/?q=Kawah+Ijen+Banyuwangi', 4.7, 'lokal', 'Petualangan', 0, 'Tengah malam sampai subuh untuk melihat blue fire dan sunrise.', 7, 1),
('Ubud', 'Ubud, Bali', 'Indonesia', 'Asia', 'Ubud menonjol lewat perpaduan alam, spiritualitas, seni Bali, sawah, dan pengalaman slow travel yang lebih intim.', 'https://upload.wikimedia.org/wikipedia/commons/5/5d/Ubud_%2849818456887%29.jpg', 'https://upload.wikimedia.org/wikipedia/commons/thumb/5/5d/Ubud_%2849818456887%29.jpg/330px-Ubud_%2849818456887%29.jpg', 'https://upload.wikimedia.org/wikipedia/commons/5/5d/Ubud_%2849818456887%29.jpg', 'https://en.wikipedia.org/wiki/Ubud', 'Wikipedia - Ubud', 'https://maps.google.com/?q=Ubud+Bali+Indonesia', 4.8, 'lokal', 'Budaya', 0, 'Pagi hari untuk suasana yang lebih tenang dan cahaya lembut.', 8, 1),
('Tokyo', 'Tokyo', 'Jepang', 'Asia', 'Tokyo memadukan budaya tradisional, distrik modern, kuliner, dan ritme kota besar yang tetap sangat terorganisir.', 'https://upload.wikimedia.org/wikipedia/commons/b/b2/Skyscrapers_of_Shinjuku_2009_January.jpg', 'https://upload.wikimedia.org/wikipedia/commons/thumb/b/b2/Skyscrapers_of_Shinjuku_2009_January.jpg/330px-Skyscrapers_of_Shinjuku_2009_January.jpg', 'https://upload.wikimedia.org/wikipedia/commons/b/b2/Skyscrapers_of_Shinjuku_2009_January.jpg', 'https://en.wikipedia.org/wiki/Tokyo', 'Wikipedia - Tokyo', 'https://maps.google.com/?q=Tokyo+Japan', 5.0, 'internasional', 'Budaya', 0, 'Musim semi dan musim gugur paling populer untuk city trip.', 9, 1),
('Seoul', 'Seoul', 'Korea Selatan', 'Asia', 'Seoul cocok untuk city break dengan perpaduan istana, street culture, k-pop district, dan pengalaman belanja modern.', 'https://upload.wikimedia.org/wikipedia/commons/3/30/%EC%A4%91%ED%99%94%EC%A0%84%EC%9D%98_%EB%82%AE.jpg', 'https://upload.wikimedia.org/wikipedia/commons/thumb/3/30/%EC%A4%91%ED%99%94%EC%A0%84%EC%9D%98_%EB%82%AE.jpg/330px-%EC%A4%91%ED%99%94%EC%A0%84%EC%9D%98_%EB%82%AE.jpg', 'https://upload.wikimedia.org/wikipedia/commons/3/30/%EC%A4%91%ED%99%94%EC%A0%84%EC%9D%98_%EB%82%AE.jpg', 'https://en.wikipedia.org/wiki/Seoul', 'Wikipedia - Seoul', 'https://maps.google.com/?q=Seoul+South+Korea', 4.9, 'internasional', 'Budaya', 0, 'Autumn dan musim semi memberi cuaca yang paling nyaman.', 10, 1),
('Paris', 'Paris', 'Prancis', 'Eropa', 'Paris menawarkan arsitektur klasik, museum kelas dunia, pengalaman sungai Seine, dan atmosfer kota yang sangat ikonik.', 'https://upload.wikimedia.org/wikipedia/commons/4/4b/La_Tour_Eiffel_vue_de_la_Tour_Saint-Jacques%2C_Paris_ao%C3%BBt_2014_%282%29.jpg', 'https://upload.wikimedia.org/wikipedia/commons/thumb/4/4b/La_Tour_Eiffel_vue_de_la_Tour_Saint-Jacques%2C_Paris_ao%C3%BBt_2014_%282%29.jpg/330px-La_Tour_Eiffel_vue_de_la_Tour_Saint-Jacques%2C_Paris_ao%C3%BBt_2014_%282%29.jpg', 'https://upload.wikimedia.org/wikipedia/commons/4/4b/La_Tour_Eiffel_vue_de_la_Tour_Saint-Jacques%2C_Paris_ao%C3%BBt_2014_%282%29.jpg', 'https://en.wikipedia.org/wiki/Paris', 'Wikipedia - Paris', 'https://maps.google.com/?q=Paris+France', 5.0, 'internasional', 'Budaya', 0, 'April sampai Juni dan September sampai Oktober paling ideal.', 11, 1),
('London', 'London', 'Inggris', 'Eropa', 'London menghadirkan kota besar yang kaya sejarah, museum, landmark, dan jaringan transportasi yang memudahkan itinerary.', 'https://upload.wikimedia.org/wikipedia/commons/6/67/London_Skyline_%28125508655%29.jpeg', 'https://upload.wikimedia.org/wikipedia/commons/thumb/6/67/London_Skyline_%28125508655%29.jpeg/330px-London_Skyline_%28125508655%29.jpeg', 'https://upload.wikimedia.org/wikipedia/commons/6/67/London_Skyline_%28125508655%29.jpeg', 'https://en.wikipedia.org/wiki/London', 'Wikipedia - London', 'https://maps.google.com/?q=London+United+Kingdom', 4.9, 'internasional', 'Budaya', 0, 'Akhir musim semi dan awal autumn lebih nyaman untuk city walking.', 12, 1),
('Swiss Alps', 'Zermatt dan Swiss Alps', 'Swiss', 'Eropa', 'Swiss Alps cocok untuk scenic rail, pegunungan, desa klasik, dan perjalanan romantis di kawasan alpine.', 'https://upload.wikimedia.org/wikipedia/commons/6/60/Matterhorn_from_Domh%C3%BCtte_-_2.jpg', 'https://upload.wikimedia.org/wikipedia/commons/thumb/6/60/Matterhorn_from_Domh%C3%BCtte_-_2.jpg/330px-Matterhorn_from_Domh%C3%BCtte_-_2.jpg', 'https://upload.wikimedia.org/wikipedia/commons/6/60/Matterhorn_from_Domh%C3%BCtte_-_2.jpg', 'https://en.wikipedia.org/wiki/Matterhorn', 'Wikipedia - Matterhorn', 'https://maps.google.com/?q=Swiss+Alps+Switzerland', 5.0, 'internasional', 'Petualangan', 0, 'Winter untuk salju, summer untuk scenic trail dan panorama hijau.', 13, 1),
('New York City', 'New York City', 'USA', 'Amerika', 'New York City cocok untuk perjalanan urban, belanja, skyline, museum, dan itinerary cepat yang padat namun efisien.', 'https://upload.wikimedia.org/wikipedia/commons/7/7a/View_of_Empire_State_Building_from_Rockefeller_Center_New_York_City_dllu_%28cropped%29.jpg', 'https://upload.wikimedia.org/wikipedia/commons/thumb/7/7a/View_of_Empire_State_Building_from_Rockefeller_Center_New_York_City_dllu_%28cropped%29.jpg/330px-View_of_Empire_State_Building_from_Rockefeller_Center_New_York_City_dllu_%28cropped%29.jpg', 'https://upload.wikimedia.org/wikipedia/commons/7/7a/View_of_Empire_State_Building_from_Rockefeller_Center_New_York_City_dllu_%28cropped%29.jpg', 'https://en.wikipedia.org/wiki/New_York_City', 'Wikipedia - New York City', 'https://maps.google.com/?q=New+York+City+USA', 4.9, 'internasional', 'Budaya', 0, 'Spring dan autumn lebih nyaman untuk city exploration.', 14, 1),
('Santorini', 'Santorini', 'Yunani', 'Eropa', 'Santorini identik dengan desa tebing putih, panorama kaldera, dan momen sunset yang sangat kuat untuk pasangan.', 'https://upload.wikimedia.org/wikipedia/commons/3/37/Oia_sunset_-_panoramio_%282%29.jpg', 'https://upload.wikimedia.org/wikipedia/commons/thumb/3/37/Oia_sunset_-_panoramio_%282%29.jpg/330px-Oia_sunset_-_panoramio_%282%29.jpg', 'https://upload.wikimedia.org/wikipedia/commons/3/37/Oia_sunset_-_panoramio_%282%29.jpg', 'https://en.wikipedia.org/wiki/Oia,_Greece', 'Wikipedia - Oia, Greece', 'https://maps.google.com/?q=Santorini+Greece', 5.0, 'internasional', 'Budaya', 0, 'Sore menjelang sunset dan shoulder season adalah momen terbaik.', 15, 1),
('Dubai', 'Dubai', 'Uni Emirat Arab', 'Asia', 'Dubai unggul untuk traveler yang ingin menggabungkan city luxury, desert safari, dan belanja modern dalam satu rute.', 'https://upload.wikimedia.org/wikipedia/en/c/c7/Burj_Khalifa_2021.jpg', 'https://upload.wikimedia.org/wikipedia/en/thumb/c/c7/Burj_Khalifa_2021.jpg/330px-Burj_Khalifa_2021.jpg', 'https://upload.wikimedia.org/wikipedia/en/c/c7/Burj_Khalifa_2021.jpg', 'https://en.wikipedia.org/wiki/Dubai', 'Wikipedia - Dubai', 'https://maps.google.com/?q=Dubai+United+Arab+Emirates', 4.9, 'internasional', 'Budaya', 0, 'Oktober sampai Maret lebih nyaman untuk city tour dan desert trip.', 16, 1),
('Machu Picchu', 'Cusco dan Machu Picchu', 'Peru', 'Amerika', 'Machu Picchu cocok untuk pencinta sejarah dan petualangan dengan jalur klasik Andes serta situs Inca yang sangat ikonik.', 'https://upload.wikimedia.org/wikipedia/commons/b/bb/Machu_Picchu%2C_2023_%28012%29.jpg', 'https://upload.wikimedia.org/wikipedia/commons/thumb/b/bb/Machu_Picchu%2C_2023_%28012%29.jpg/330px-Machu_Picchu%2C_2023_%28012%29.jpg', 'https://upload.wikimedia.org/wikipedia/commons/b/bb/Machu_Picchu%2C_2023_%28012%29.jpg', 'https://en.wikipedia.org/wiki/Machu_Picchu', 'Wikipedia - Machu Picchu', 'https://maps.google.com/?q=Machu+Picchu+Peru', 5.0, 'internasional', 'Petualangan', 0, 'Musim kering sekitar Mei sampai September paling aman.', 17, 1),
('Maldives', 'Male dan Atol Maladewa', 'Maladewa', 'Asia', 'Maldives dikenal sebagai resort tropis premium dengan air jernih, vila atas laut, dan pengalaman honeymoon.', 'https://upload.wikimedia.org/wikipedia/commons/4/44/Rehendi_Suite_Deck_%28Service%29.jpg', 'https://upload.wikimedia.org/wikipedia/commons/thumb/4/44/Rehendi_Suite_Deck_%28Service%29.jpg/330px-Rehendi_Suite_Deck_%28Service%29.jpg', 'https://upload.wikimedia.org/wikipedia/commons/4/44/Rehendi_Suite_Deck_%28Service%29.jpg', 'https://en.wikipedia.org/wiki/Tourism_in_the_Maldives', 'Wikipedia - Tourism in the Maldives', 'https://maps.google.com/?q=Maldives', 5.0, 'internasional', 'Bahari', 0, 'November sampai April lebih ideal untuk resort stay dan aktivitas laut.', 18, 1),
('Rome', 'Rome', 'Italia', 'Eropa', 'Rome menghadirkan warisan Kekaisaran Romawi, piazza klasik, dan kota tua yang tetap hidup untuk wisata sejarah.', 'https://upload.wikimedia.org/wikipedia/commons/7/7e/Trevi_Fountain%2C_Rome%2C_Italy_2_-_May_2007.jpg', 'https://upload.wikimedia.org/wikipedia/commons/thumb/7/7e/Trevi_Fountain%2C_Rome%2C_Italy_2_-_May_2007.jpg/330px-Trevi_Fountain%2C_Rome%2C_Italy_2_-_May_2007.jpg', 'https://upload.wikimedia.org/wikipedia/commons/7/7e/Trevi_Fountain%2C_Rome%2C_Italy_2_-_May_2007.jpg', 'https://en.wikipedia.org/wiki/Rome', 'Wikipedia - Rome', 'https://maps.google.com/?q=Rome+Italy', 4.9, 'internasional', 'Budaya', 0, 'Spring dan early autumn memberi cuaca paling nyaman.', 19, 1),
('Hanoi', 'Hanoi', 'Vietnam', 'Asia', 'Hanoi menawarkan old quarter, kuliner street food, dan pengalaman kota yang lebih intim untuk traveler Asia pertama kali.', 'https://upload.wikimedia.org/wikipedia/commons/8/8e/Hanoi_skyline_with_Ba_Vi_Mountain.jpg', 'https://upload.wikimedia.org/wikipedia/commons/thumb/8/8e/Hanoi_skyline_with_Ba_Vi_Mountain.jpg/330px-Hanoi_skyline_with_Ba_Vi_Mountain.jpg', 'https://upload.wikimedia.org/wikipedia/commons/8/8e/Hanoi_skyline_with_Ba_Vi_Mountain.jpg', 'https://en.wikipedia.org/wiki/Hanoi', 'Wikipedia - Hanoi', 'https://maps.google.com/?q=Hanoi+Vietnam', 4.8, 'internasional', 'Budaya', 0, 'Musim semi dan akhir tahun cocok untuk city trip dan kuliner.', 20, 1),
('Phuket', 'Phuket', 'Thailand', 'Asia', 'Phuket cocok untuk island hopping, resort, beach club, dan perjalanan singkat dengan suasana tropis.', 'https://upload.wikimedia.org/wikipedia/commons/6/60/Phuket_Aerial.jpg', 'https://upload.wikimedia.org/wikipedia/commons/thumb/6/60/Phuket_Aerial.jpg/330px-Phuket_Aerial.jpg', 'https://upload.wikimedia.org/wikipedia/commons/6/60/Phuket_Aerial.jpg', 'https://en.wikipedia.org/wiki/Phuket_province', 'Wikipedia - Phuket Province', 'https://maps.google.com/?q=Phuket+Thailand', 4.8, 'internasional', 'Bahari', 0, 'November sampai April biasanya lebih stabil untuk wisata pantai.', 21, 1);

INSERT INTO destinasi (
    nama, lokasi, negara, benua, deskripsi, foto, thumbnail_foto, moment_foto,
    foto_source_url, foto_source_label, maps_url, rating, tipe, kategori,
    total_review, best_time, display_order, is_active
)
SELECT
    nama, lokasi, negara, benua, deskripsi, foto, thumbnail_foto, moment_foto,
    foto_source_url, foto_source_label, maps_url, rating, tipe, kategori,
    total_review, best_time, display_order, is_active
FROM tmp_destination_seed
ON DUPLICATE KEY UPDATE
    lokasi = VALUES(lokasi),
    negara = VALUES(negara),
    benua = VALUES(benua),
    deskripsi = VALUES(deskripsi),
    foto = VALUES(foto),
    thumbnail_foto = VALUES(thumbnail_foto),
    moment_foto = VALUES(moment_foto),
    foto_source_url = VALUES(foto_source_url),
    foto_source_label = VALUES(foto_source_label),
    maps_url = VALUES(maps_url),
    rating = VALUES(rating),
    tipe = VALUES(tipe),
    kategori = VALUES(kategori),
    best_time = VALUES(best_time),
    display_order = VALUES(display_order),
    is_active = VALUES(is_active);

UPDATE wisata w
JOIN tmp_destination_seed s ON s.nama = w.nama
SET
    w.lokasi = s.lokasi,
    w.negara = s.negara,
    w.benua = s.benua,
    w.deskripsi = s.deskripsi,
    w.foto = s.foto,
    w.thumbnail_foto = s.thumbnail_foto,
    w.moment_foto = s.moment_foto,
    w.foto_source_url = s.foto_source_url,
    w.foto_source_label = s.foto_source_label,
    w.maps_url = s.maps_url,
    w.rating = s.rating,
    w.kategori = s.kategori,
    w.best_time = s.best_time,
    w.display_order = s.display_order,
    w.is_active = s.is_active;

INSERT INTO wisata (
    nama, lokasi, negara, benua, deskripsi, foto, thumbnail_foto, moment_foto,
    foto_source_url, foto_source_label, maps_url, rating, kategori,
    best_time, display_order, is_active
)
SELECT
    s.nama, s.lokasi, s.negara, s.benua, s.deskripsi, s.foto, s.thumbnail_foto,
    s.moment_foto, s.foto_source_url, s.foto_source_label, s.maps_url, s.rating,
    s.kategori, s.best_time, s.display_order, s.is_active
FROM tmp_destination_seed s
LEFT JOIN wisata w ON w.nama = s.nama
WHERE w.id IS NULL;

DROP TEMPORARY TABLE IF EXISTS tmp_package_seed;
CREATE TEMPORARY TABLE tmp_package_seed (
    kode_paket VARCHAR(80) PRIMARY KEY,
    destination_name VARCHAR(255) NOT NULL,
    nama_paket VARCHAR(255) NOT NULL,
    jenis_paket VARCHAR(40) DEFAULT 'custom',
    deskripsi TEXT,
    harga DECIMAL(15,0) NOT NULL,
    durasi VARCHAR(100),
    fasilitas TEXT,
    min_orang INT DEFAULT 1,
    max_orang INT DEFAULT 20,
    status_paket VARCHAR(30) DEFAULT 'aktif',
    meeting_point VARCHAR(255),
    keberangkatan_info TEXT,
    kuota_total INT DEFAULT 20,
    kuota_tersedia INT DEFAULT 20,
    is_featured TINYINT(1) DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO tmp_package_seed (
    kode_paket, destination_name, nama_paket, jenis_paket, deskripsi, harga,
    durasi, fasilitas, min_orang, max_orang, status_paket, meeting_point,
    keberangkatan_info, kuota_total, kuota_tersedia, is_featured
) VALUES
('PKG-LABUAN-3D2N', 'Labuan Bajo', 'Labuan Bajo Signature Sailing Escape', 'group', 'Paket sailing trip untuk jelajah pulau dan spot snorkeling utama Labuan Bajo.', 8500000, '3 Hari / 2 Malam', 'Hotel, kapal sharing, makan, transfer lokal, guide', 1, 10, 'aktif', 'Bandara Komodo / hotel area Labuan Bajo', 'Berangkat mingguan dari Labuan Bajo. Private trip tersedia sesuai permintaan.', 20, 20, 1),
('PKG-RAJA-4D3N', 'Raja Ampat', 'Raja Ampat Reef and Island Journey', 'group', 'Paket island hopping dan eksplorasi spot unggulan Raja Ampat.', 12800000, '4 Hari / 3 Malam', 'Hotel, speedboat, makan, guide lokal, airport transfer', 1, 8, 'aktif', 'Bandara Domine Eduard Osok Sorong', 'Musim terbaik Oktober sampai April. Cocok untuk island hopping premium.', 16, 16, 1),
('PKG-BOROBUDUR-2D1N', 'Candi Borobudur', 'Borobudur Heritage Cultural Escape', 'pasangan', 'Paket budaya singkat untuk sunrise area Borobudur dan wisata heritage sekitar Yogyakarta.', 2850000, '2 Hari / 1 Malam', 'Hotel, transportasi lokal, tiket area heritage, breakfast', 1, 6, 'aktif', 'Yogyakarta city area / meeting point Magelang', 'Jadwal fleksibel. Cocok untuk short cultural break.', 24, 24, 0),
('PKG-TOBA-3D2N', 'Danau Toba', 'Danau Toba Scenic Lake Journey', 'keluarga', 'Paket darat untuk menikmati panorama Danau Toba dan budaya Batak.', 3900000, '3 Hari / 2 Malam', 'Hotel, transportasi lokal, sarapan, driver', 2, 8, 'aktif', 'Bandara Silangit / Medan by request', 'Berangkat mingguan dengan opsi private family trip.', 18, 18, 0),
('PKG-KOMODO-3D2N', 'Pulau Komodo', 'Komodo Island Trek and Sea Route', 'group', 'Paket petualangan untuk trekking Pulau Komodo dan eksplorasi teluk sekitar.', 9600000, '3 Hari / 2 Malam', 'Boat trip, makan, guide ranger, entrance fee lokal', 1, 8, 'aktif', 'Labuan Bajo harbor', 'Cocok untuk traveler aktif dan island hopping.', 16, 16, 0),
('PKG-BROMO-2D1N', 'Gunung Bromo', 'Bromo Sunrise Volcano Trip', 'group', 'Paket favorit untuk menikmati sunrise Penanjakan dan lautan pasir Bromo.', 3400000, '2 Hari / 1 Malam', 'Jeep, hotel, sarapan, guide lokal', 1, 10, 'aktif', 'Malang / Surabaya pickup point', 'Start dini hari untuk mengejar golden sunrise.', 24, 24, 0),
('PKG-IJEN-2D1N', 'Kawah Ijen', 'Ijen Blue Fire Adventure', 'group', 'Paket trekking malam ke Kawah Ijen untuk melihat blue fire dan sunrise.', 3100000, '2 Hari / 1 Malam', 'Hotel, transportasi, masker, guide trekking', 1, 8, 'aktif', 'Banyuwangi city area', 'Berangkat malam dan cocok untuk traveler fit.', 18, 18, 0),
('PKG-UBUD-3D2N', 'Ubud', 'Ubud Culture and Wellness Retreat', 'pasangan', 'Paket santai untuk eksplorasi Ubud, sawah, spa, dan pengalaman budaya Bali.', 4200000, '3 Hari / 2 Malam', 'Villa / hotel, breakfast, transfer lokal, itinerary assist', 1, 6, 'aktif', 'Denpasar airport / Ubud center', 'Cocok untuk slow travel dan honeymoon ringan.', 18, 18, 0),
('PKG-TOKYO-5D4N', 'Tokyo', 'Tokyo City Lights and Culture Route', 'solo', 'Paket city trip untuk distrik utama Tokyo dan pengalaman budaya populer Jepang.', 16900000, '5 Hari / 4 Malam', 'Hotel, airport transfer, city tour basic, itinerary book', 1, 6, 'aktif', 'Haneda / Narita airport', 'Fleksibel mengikuti musim sakura atau autumn.', 20, 20, 1),
('PKG-SEOUL-5D4N', 'Seoul', 'Seoul City and Lifestyle Escape', 'solo', 'Paket Korea untuk traveler yang ingin city route, palace, dan shopping district.', 15600000, '5 Hari / 4 Malam', 'Hotel, transfer, city orientation, itinerary booklet', 1, 6, 'aktif', 'Incheon airport', 'Cocok untuk first timer Korea dan group kecil.', 20, 20, 0),
('PKG-PARIS-6D5N', 'Paris', 'Paris Museum and Riverfront Escape', 'pasangan', 'Paket Eropa inti untuk museum, riverfront, landmark, dan pengalaman kota romantis.', 19800000, '6 Hari / 5 Malam', 'Hotel, transportasi lokal, city pass basic, airport transfer', 1, 6, 'aktif', 'Charles de Gaulle airport / city hotel', 'Bisa digabung dengan London dan Swiss.', 20, 20, 1),
('PKG-LONDON-6D5N', 'London', 'London Heritage and Modern City Tour', 'solo', 'Paket kota London untuk landmark utama, museum, dan jalan kaki kawasan sentral.', 21200000, '6 Hari / 5 Malam', 'Hotel, transfer, oyster top-up starter, city orientation', 1, 6, 'aktif', 'Heathrow airport / central hotel', 'Jadwal fleksibel untuk museum dan shopping day.', 20, 20, 0),
('PKG-SWISS-7D5N', 'Swiss Alps', 'Swiss Alps Scenic Rail Signature', 'pasangan', 'Paket Swiss dengan fokus pada scenic train, mountain view, dan resort alpine.', 22900000, '7 Hari / 5 Malam', 'Hotel, scenic rail pass basic, transfer, itinerary assist', 1, 6, 'aktif', 'Zurich / Geneva arrival point', 'Musim dingin dan summer scenery sama-sama tersedia.', 20, 20, 1),
('PKG-NYC-6D5N', 'New York City', 'New York Skyline Urban Break', 'solo', 'Paket urban trip ke New York untuk skyline, museum, dan district utama Manhattan.', 24500000, '6 Hari / 5 Malam', 'Hotel, airport transfer, city orientation, itinerary plan', 1, 6, 'aktif', 'JFK / Manhattan hotel', 'Cocok untuk city explorer dan shopping trip.', 18, 18, 0),
('PKG-SANTORINI-5D4N', 'Santorini', 'Santorini Sunset Romantic Escape', 'pasangan', 'Paket pulau romantis untuk caldera stay, sunset point, dan aktivitas santai.', 20900000, '5 Hari / 4 Malam', 'Hotel, transfer pelabuhan / bandara, breakfast, itinerary support', 1, 6, 'aktif', 'Santorini airport / ferry port', 'Shoulder season lebih nyaman dan tidak terlalu padat.', 16, 16, 0),
('PKG-DUBAI-4D3N', 'Dubai', 'Dubai Desert and Downtown Experience', 'keluarga', 'Paket Dubai dengan gabungan city highlight, shopping, dan desert safari.', 17600000, '4 Hari / 3 Malam', 'Hotel, airport transfer, city tour, desert safari basic', 1, 8, 'aktif', 'Dubai airport / city hotel', 'City stopover dan family trip tersedia.', 20, 20, 1),
('PKG-MACHU-6D5N', 'Machu Picchu', 'Machu Picchu Andes Discovery', 'group', 'Paket Peru untuk rute Cusco dan Machu Picchu dengan fokus pengalaman sejarah.', 23700000, '6 Hari / 5 Malam', 'Hotel, transport lokal, guide, entrance support', 1, 8, 'aktif', 'Cusco airport', 'Perlu stamina baik untuk itinerary aktif.', 16, 16, 0),
('PKG-MALDIVES-4D3N', 'Maldives', 'Maldives Water Villa Leisure Stay', 'pasangan', 'Paket resort tropis untuk honeymoon, leisure stay, dan aktivitas laut.', 25800000, '4 Hari / 3 Malam', 'Resort, speedboat transfer, breakfast, resort assist', 1, 4, 'aktif', 'Male airport', 'Paling cocok untuk honeymoon dan premium leisure stay.', 12, 12, 0),
('PKG-ROME-5D4N', 'Rome', 'Rome Classical Heritage Route', 'solo', 'Paket sejarah klasik untuk pengalaman kota lama Rome dan landmark utama Italia.', 18400000, '5 Hari / 4 Malam', 'Hotel, airport transfer, city assist, itinerary support', 1, 6, 'aktif', 'Fiumicino airport / city hotel', 'Cocok digabung ke Florence atau Vatican route.', 18, 18, 0),
('PKG-HANOI-5D4N', 'Hanoi', 'Hanoi Old Quarter Culinary Trail', 'solo', 'Paket Vietnam untuk old quarter, kuliner, dan city route yang nyaman bagi first timer.', 11700000, '5 Hari / 4 Malam', 'Hotel, transfer, city orientation, itinerary booklet', 1, 6, 'aktif', 'Noi Bai airport', 'Ideal untuk city trip Asia pertama kali.', 18, 18, 0),
('PKG-PHUKET-4D3N', 'Phuket', 'Phuket Island Leisure Escape', 'keluarga', 'Paket tropis untuk resort stay, island hopping, dan sunset trip ringan.', 12200000, '4 Hari / 3 Malam', 'Hotel, transfer, island hopping basic, itinerary assist', 1, 8, 'aktif', 'Phuket airport / Patong area', 'High season lebih cocok untuk aktivitas laut.', 18, 18, 0),
('TEST-RP1-VERIFY', 'Labuan Bajo', 'Paket Verifikasi Pembayaran Rp1', 'custom', 'Khusus untuk menguji alur pembayaran sebelum website dipakai penuh.', 1, 'Tes pembayaran 1x transaksi', 'Simulasi checkout, verifikasi notifikasi pembayaran', 1, 1, 'aktif', 'Online / koordinasi admin', 'Dipakai untuk uji transfer, QRIS, dan gateway sebelum go-live.', 999, 999, 0);

UPDATE tipe_paket tp
JOIN tmp_package_seed s ON s.kode_paket = tp.kode_paket
JOIN wisata w ON w.id = tp.wisata_id
SET
    tp.nama_paket = s.nama_paket,
    tp.jenis_paket = s.jenis_paket,
    tp.deskripsi = s.deskripsi,
    tp.harga = s.harga,
    tp.durasi = s.durasi,
    tp.fasilitas = s.fasilitas,
    tp.min_orang = s.min_orang,
    tp.max_orang = s.max_orang,
    tp.status_paket = s.status_paket,
    tp.meeting_point = s.meeting_point,
    tp.keberangkatan_info = s.keberangkatan_info,
    tp.kuota_total = s.kuota_total,
    tp.kuota_tersedia = s.kuota_tersedia,
    tp.is_featured = s.is_featured,
    tp.wisata_id = w.id;

INSERT INTO tipe_paket (
    wisata_id, kode_paket, nama_paket, jenis_paket, deskripsi, harga, durasi,
    fasilitas, min_orang, max_orang, status_paket, meeting_point,
    keberangkatan_info, kuota_total, kuota_tersedia, is_featured
)
SELECT
    w.id, s.kode_paket, s.nama_paket, s.jenis_paket, s.deskripsi, s.harga,
    s.durasi, s.fasilitas, s.min_orang, s.max_orang, s.status_paket,
    s.meeting_point, s.keberangkatan_info, s.kuota_total, s.kuota_tersedia,
    s.is_featured
FROM tmp_package_seed s
JOIN wisata w ON w.nama = s.destination_name
LEFT JOIN tipe_paket tp ON tp.kode_paket = s.kode_paket
WHERE tp.id IS NULL;

INSERT INTO promo_destinasi (
    wisata_id, promo_name, promo_label, description, discount_type, discount_value,
    starts_at, ends_at, is_active, created_by_staff_id, created_at, updated_at
)
SELECT
    w.id,
    'Early Booking Escape',
    'Promo Musim Ini',
    'Diskon aktif untuk mendorong user mencoba alur promo, pembayaran, dan katalog penawaran dengan harga yang lebih ringan.',
    'percent',
    15,
    DATE_SUB(NOW(), INTERVAL 1 DAY),
    DATE_ADD(NOW(), INTERVAL 120 DAY),
    1,
    NULL,
    NOW(),
    NOW()
FROM wisata w
WHERE w.nama IN ('Raja Ampat', 'Tokyo', 'Paris')
  AND NOT EXISTS (
      SELECT 1
      FROM promo_destinasi pr
      WHERE pr.wisata_id = w.id
        AND pr.promo_name = 'Early Booking Escape'
  );

UPDATE pemesanan
SET kode_pemesanan = CONCAT('ELT-', LPAD(id, 6, '0'))
WHERE kode_pemesanan IS NULL OR kode_pemesanan = '';

UPDATE pemesanan
SET sumber_pesanan = 'website'
WHERE sumber_pesanan IS NULL OR sumber_pesanan = '';

INSERT INTO operasional_pesanan (
    pemesanan_id, kode_booking, status_operasional, status_tiket,
    status_voucher, status_dokumen, created_at, updated_at
)
SELECT
    p.id,
    CONCAT('ELT-', LPAD(p.id, 6, '0')),
    CASE
        WHEN pb.status_pembayaran = 'menunggu_verifikasi' THEN 'verifikasi_pembayaran'
        WHEN pb.status_pembayaran = 'berhasil' OR p.status = 'confirmed' THEN 'siapkan_tiket'
        WHEN p.status = 'completed' THEN 'selesai'
        WHEN p.status = 'cancelled' THEN 'dibatalkan'
        ELSE 'menunggu_pembayaran'
    END,
    CASE
        WHEN pb.status_pembayaran = 'berhasil' OR p.status IN ('confirmed', 'completed') THEN 'diproses'
        ELSE 'belum_dibuat'
    END,
    'belum_dibuat',
    'belum_lengkap',
    NOW(),
    NOW()
FROM pemesanan p
LEFT JOIN pembayaran pb ON pb.pemesanan_id = p.id
LEFT JOIN operasional_pesanan op ON op.pemesanan_id = p.id
WHERE op.pemesanan_id IS NULL;

DROP TEMPORARY TABLE IF EXISTS tmp_destination_seed;
DROP TEMPORARY TABLE IF EXISTS tmp_package_seed;

-- =============================================
-- SAFE REFRESH COMPLETE
-- Gunakan file ini untuk update master data
-- tanpa drop data transaksi yang sudah ada.
-- =============================================
