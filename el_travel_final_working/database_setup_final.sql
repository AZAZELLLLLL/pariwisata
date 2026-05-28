-- =============================================
-- EL TRAVEL — Database Setup (FINAL)
-- Database Name: pariwisataDb
-- Jalankan file ini di phpMyAdmin > Import
-- =============================================

CREATE DATABASE IF NOT EXISTS pariwisataDb
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE pariwisataDb;

-- Drop tables jika sudah ada (untuk fresh install)
DROP TABLE IF EXISTS rating_review;
DROP TABLE IF EXISTS payment_detail;
DROP TABLE IF EXISTS pembayaran;
DROP TABLE IF EXISTS pemesanan;
DROP TABLE IF EXISTS tipe_paket;
DROP TABLE IF EXISTS destinasi;
DROP TABLE IF EXISTS wisata;

-- ── Tabel Destinasi (UTAMA) ──
CREATE TABLE destinasi (
    id       INT AUTO_INCREMENT PRIMARY KEY,
    nama     VARCHAR(255) NOT NULL UNIQUE,
    lokasi   VARCHAR(255) NOT NULL,
    deskripsi TEXT,
    foto     VARCHAR(600),
    maps_url VARCHAR(1000),
    rating   DECIMAL(2,1) DEFAULT 4.5,
    tipe     ENUM('lokal','internasional') DEFAULT 'lokal',
    kategori VARCHAR(100),
    total_review INT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── Tabel Wisata (LEGACY - untuk kompatibilitas) ──
CREATE TABLE wisata (
    id       INT AUTO_INCREMENT PRIMARY KEY,
    nama     VARCHAR(255) NOT NULL,
    lokasi   VARCHAR(255) NOT NULL,
    deskripsi TEXT,
    foto     VARCHAR(600),
    maps_url VARCHAR(1000),
    rating   DECIMAL(2,1) DEFAULT 4.5,
    kategori VARCHAR(100)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── Tabel Tipe Paket ──
CREATE TABLE tipe_paket (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    wisata_id  INT NOT NULL,
    nama_paket VARCHAR(255) NOT NULL,
    deskripsi  TEXT,
    harga      DECIMAL(15,0) NOT NULL,
    durasi     VARCHAR(100),
    fasilitas  TEXT,
    min_orang  INT DEFAULT 1,
    max_orang  INT DEFAULT 20,
    FOREIGN KEY (wisata_id) REFERENCES wisata(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── Tabel Pemesanan ──
CREATE TABLE pemesanan (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    paket_id      INT NOT NULL,
    nama_pemesan  VARCHAR(255) NOT NULL,
    email         VARCHAR(255),
    telepon       VARCHAR(50),
    tanggal_pergi DATE NOT NULL,
    jumlah_orang  INT NOT NULL DEFAULT 1,
    total_harga   DECIMAL(15,0) NOT NULL,
    tanggal_pesan DATETIME DEFAULT CURRENT_TIMESTAMP,
    status        ENUM('pending','confirmed','cancelled','completed') DEFAULT 'pending',
    catatan       TEXT,
    FOREIGN KEY (paket_id) REFERENCES tipe_paket(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── Tabel Pembayaran ──
CREATE TABLE pembayaran (
    id                INT AUTO_INCREMENT PRIMARY KEY,
    pemesanan_id      INT NOT NULL UNIQUE,
    metode_pembayaran VARCHAR(40) DEFAULT 'bank_transfer',
    status_pembayaran ENUM('pending','berhasil','gagal','menunggu_verifikasi') DEFAULT 'pending',
    tanggal_pembayaran DATETIME,
    jumlah_dibayar    DECIMAL(15,0) NOT NULL,
    keterangan        TEXT,
    bukti_pembayaran  VARCHAR(600),
    qr_code_path      VARCHAR(600),
    qr_generated_at   DATETIME,
    gateway_provider  VARCHAR(40),
    gateway_order_id  VARCHAR(120),
    gateway_transaction_id VARCHAR(120),
    gateway_status    VARCHAR(40),
    snap_token        VARCHAR(255),
    redirect_url      VARCHAR(600),
    channel_code      VARCHAR(80),
    payment_reference VARCHAR(120),
    paid_at           DATETIME,
    raw_response_json LONGTEXT,
    created_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at        DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (pemesanan_id) REFERENCES pemesanan(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── Tabel Payment Detail ──
CREATE TABLE payment_detail (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    pembayaran_id   INT NOT NULL,
    detail_key      VARCHAR(50),
    detail_value    VARCHAR(255),
    deskripsi_item  VARCHAR(255),
    jumlah_item     INT DEFAULT 1,
    harga_satuan    DECIMAL(15,0),
    subtotal        DECIMAL(15,0),
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (pembayaran_id) REFERENCES pembayaran(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── Tabel Akun User ──
CREATE TABLE akun_user (
    id                    INT AUTO_INCREMENT PRIMARY KEY,
    email                 VARCHAR(190) NOT NULL UNIQUE,
    nama_lengkap          VARCHAR(120) NOT NULL,
    jenis_kelamin         VARCHAR(40) DEFAULT 'Tidak ingin menyebutkan',
    telepon               VARCHAR(25),
    tanggal_lahir         DATE NULL,
    kota_domisili         VARCHAR(120),
    password_hash         VARCHAR(255) NOT NULL,
    email_verified        TINYINT(1) DEFAULT 0,
    verification_code_hash VARCHAR(64),
    verification_expires_at DATETIME NULL,
    verification_attempts INT DEFAULT 0,
    created_at            DATETIME NOT NULL,
    updated_at            DATETIME NOT NULL,
    last_login_at         DATETIME NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── Tabel Rating Review ──
CREATE TABLE rating_review (
    id                   INT AUTO_INCREMENT PRIMARY KEY,
    pemesanan_id         INT NOT NULL UNIQUE,
    destinasi_id         INT,
    nama_pengguna        VARCHAR(255),
    email_pengguna       VARCHAR(255),
    rating_destinasi     DECIMAL(2,1) DEFAULT 5.0,
    rating_pelayanan     DECIMAL(2,1) DEFAULT 5.0,
    rating_keseluruhan   DECIMAL(2,1) DEFAULT 5.0,
    judul_review         VARCHAR(255),
    isi_review           TEXT,
    foto_review          VARCHAR(600),
    status_review        ENUM('pending','published','rejected') DEFAULT 'pending',
    jumlah_likes         INT DEFAULT 0,
    tanggal_review       DATETIME DEFAULT CURRENT_TIMESTAMP,
    tanggal_publish      DATETIME,
    FOREIGN KEY (pemesanan_id) REFERENCES pemesanan(id) ON DELETE CASCADE,
    FOREIGN KEY (destinasi_id) REFERENCES destinasi(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ════════════════════════════════════════
-- INSERT DATA: 21 DESTINASI (FIXED)
-- ════════════════════════════════════════

INSERT INTO destinasi (nama, lokasi, deskripsi, foto, maps_url, rating, tipe, kategori, total_review) VALUES

-- LOKAL
('Labuan Bajo', 'Nusa Tenggara Timur', 'Labuan Bajo adalah sebuah kota kecil yang menjadi pintu gerbang menuju Taman Nasional Komodo.', 'https://images.unsplash.com/photo-1588668214407-6ea9a6d8c272?w=800', 'https://maps.google.com/?q=Labuan+Bajo+NTT+Indonesia', 4.9, 'lokal', 'Bahari', 0),
('Raja Ampat', 'Papua Barat', 'Raja Ampat adalah kepulauan di ujung kepala burung Pulau Papua yang terkenal sebagai salah satu destinasi selam terbaik di dunia.', 'https://images.unsplash.com/photo-1518548419970-58e3b4079ab2?w=800', 'https://maps.google.com/?q=Raja+Ampat+Papua+Barat+Indonesia', 5.0, 'lokal', 'Bahari', 0),
('Candi Borobudur', 'Magelang, Jawa Tengah', 'Borobudur adalah candi Buddha terbesar di dunia yang dibangun pada abad ke-9 Masehi.', 'https://images.unsplash.com/photo-1596402184320-417e7178b2cd?w=800', 'https://maps.google.com/?q=Candi+Borobudur+Magelang+Jawa+Tengah', 4.8, 'lokal', 'Budaya', 0),
('Danau Toba', 'Sumatera Utara', 'Danau Toba adalah danau vulkanik terbesar di dunia dengan luas 1.130 km².', 'https://images.unsplash.com/photo-1590736969955-71cc94901144?w=800', 'https://maps.google.com/?q=Danau+Toba+Sumatera+Utara', 4.7, 'lokal', 'Alam', 0),
('Pulau Komodo', 'Nusa Tenggara Timur', 'Pulau Komodo adalah bagian dari Taman Nasional Komodo yang merupakan habitat asli Komodo.', 'https://images.unsplash.com/photo-1607604276583-eef5d076aa5f?w=800', 'https://maps.google.com/?q=Pulau+Komodo+NTT+Indonesia', 4.9, 'lokal', 'Petualangan', 0),
('Gunung Bromo', 'Jawa Timur', 'Gunung Bromo adalah gunung berapi aktif yang paling terkenal di Jawa Timur.', 'https://images.unsplash.com/photo-1504893524553-b855bce32c67?w=800', 'https://maps.google.com/?q=Gunung+Bromo+Jawa+Timur', 4.8, 'lokal', 'Petualangan', 0),
('Kawah Ijen', 'Banyuwangi, Jawa Timur', 'Kawah Ijen terkenal dengan fenomena blue fire atau api biru yang langka.', 'https://images.unsplash.com/photo-1601142634808-38923eb7c560?w=800', 'https://maps.google.com/?q=Kawah+Ijen+Banyuwangi+Jawa+Timur', 4.7, 'lokal', 'Petualangan', 0),
('Ubud', 'Bali', 'Ubud adalah jantung budaya Bali yang menawarkan perpaduan sempurna antara alam, seni, dan spiritualitas.', 'https://images.unsplash.com/photo-1537996194471-e657df975ab4?w=800', 'https://maps.google.com/?q=Ubud+Bali+Indonesia', 4.8, 'lokal', 'Budaya', 0),

-- INTERNASIONAL
('Tokyo', 'Jepang', 'Tokyo adalah ibu kota Jepang yang menggabungkan tradisi kuno dengan teknologi futuristik.', 'https://images.unsplash.com/photo-1480796927426-f609979314bd?w=800', 'https://maps.google.com/?q=Tokyo+Jepang', 5.0, 'internasional', 'Budaya', 0),
('Seoul', 'Korea Selatan', 'Seoul adalah kota metropolitan yang dinamis dengan seni, fashion, dan kuliner kelas dunia.', 'https://images.unsplash.com/photo-1538485399081-7191377e8241?w=800', 'https://maps.google.com/?q=Seoul+Korea+Selatan', 4.9, 'internasional', 'Budaya', 0),
('Paris', 'Prancis', 'Paris — Kota Cahaya — adalah simbol cinta, seni, dan keanggunan.', 'https://images.unsplash.com/photo-1499856871958-5b9357976b82?w=800', 'https://maps.google.com/?q=Paris+Prancis', 5.0, 'internasional', 'Budaya', 0),
('London', 'Inggris', 'London adalah ibu kota Inggris yang kaya sejarah dan budaya.', 'https://images.unsplash.com/photo-1513635269975-59663e0ac1ad?w=800', 'https://maps.google.com/?q=London+Inggris', 4.9, 'internasional', 'Budaya', 0),
('Swiss Alps', 'Swiss', 'Swiss Alps menawarkan pemandangan gunung yang menakjubkan dan resort ski kelas dunia.', 'https://images.unsplash.com/photo-1530122037265-a5f1f91d3b99?w=800', 'https://maps.google.com/?q=Swiss+Alps+Swiss', 5.0, 'internasional', 'Petualangan', 0),
('New York City', 'USA', 'NYC — The City That Never Sleeps — menawarkan pengalaman urban terbaik.', 'https://images.unsplash.com/photo-1496442226666-8d4d0e62e6e9?w=800', 'https://maps.google.com/?q=New+York+City+USA', 4.9, 'internasional', 'Budaya', 0),
('Santorini', 'Yunani', 'Santorini adalah pulau paling romantis di Yunani dengan pemandangan caldera yang spektakuler.', 'https://images.unsplash.com/photo-1570077188670-e3a8d69ac5ff?w=800', 'https://maps.google.com/?q=Santorini+Yunani', 5.0, 'internasional', 'Budaya', 0),
('Dubai', 'Uni Emirat Arab', 'Dubai adalah kota futuristik dengan Burj Khalifa tertinggi dan inovasi teknologi.', 'https://images.unsplash.com/photo-1512453979798-5ea266f8880c?w=800', 'https://maps.google.com/?q=Dubai+Uni+Emirat+Arab', 4.9, 'internasional', 'Budaya', 0),
('Machu Picchu', 'Peru', 'Machu Picchu adalah situs arkeologi Inca paling terkenal di dunia.', 'https://images.unsplash.com/photo-1587595431973-160d0d94add1?w=800', 'https://maps.google.com/?q=Machu+Picchu+Peru', 5.0, 'internasional', 'Petualangan', 0),
('Maldives', 'Maladewa', 'Maldives adalah surga tropis dengan air turquoise dan resort over-water yang mewah.', 'https://images.unsplash.com/photo-1514282401047-d79a71a590e8?w=800', 'https://maps.google.com/?q=Maldives+Maladewa', 5.0, 'internasional', 'Budaya', 0),
('Rome', 'Italia', 'Rome adalah kota bersejarah dengan lapisan arsitektur klasik, piazza, dan peninggalan kekaisaran yang masih terasa sangat hidup.', 'https://images.unsplash.com/photo-1552832230-c0197dd311b5?w=800', 'https://maps.google.com/?q=Rome+Italia', 4.9, 'internasional', 'Budaya', 0),
('Hanoi', 'Vietnam', 'Hanoi menghadirkan perpaduan kuat antara kota lama, kuliner jalanan, dan ritme urban yang terasa lebih intim.', 'https://images.unsplash.com/photo-1508061253366-f7da158b6d46?w=800', 'https://maps.google.com/?q=Hanoi+Vietnam', 4.8, 'internasional', 'Budaya', 0),
('Phuket', 'Thailand', 'Phuket adalah destinasi pantai tropis yang menawarkan resort, pulau-pulau kecil, dan sunset yang sangat kuat secara visual.', 'https://images.unsplash.com/photo-1589394815804-964ed0be2eb5?w=800', 'https://maps.google.com/?q=Phuket+Thailand', 4.8, 'internasional', 'Bahari', 0);

-- Insert data untuk table wisata (legacy compatibility)
INSERT INTO wisata (nama, lokasi, deskripsi, foto, maps_url, rating, kategori) VALUES
('Labuan Bajo', 'Nusa Tenggara Timur', 'Labuan Bajo adalah sebuah kota kecil yang menjadi pintu gerbang menuju Taman Nasional Komodo.', 'https://images.unsplash.com/photo-1588668214407-6ea9a6d8c272?w=800', 'https://maps.google.com/?q=Labuan+Bajo+NTT+Indonesia', 4.9, 'Bahari'),
('Raja Ampat', 'Papua Barat', 'Raja Ampat adalah kepulauan di ujung kepala burung Pulau Papua yang terkenal sebagai salah satu destinasi selam terbaik di dunia.', 'https://images.unsplash.com/photo-1518548419970-58e3b4079ab2?w=800', 'https://maps.google.com/?q=Raja+Ampat+Papua+Barat+Indonesia', 5.0, 'Bahari'),
('Candi Borobudur', 'Magelang, Jawa Tengah', 'Borobudur adalah candi Buddha terbesar di dunia yang dibangun pada abad ke-9 Masehi.', 'https://images.unsplash.com/photo-1596402184320-417e7178b2cd?w=800', 'https://maps.google.com/?q=Candi+Borobudur+Magelang+Jawa+Tengah', 4.8, 'Budaya'),
('Danau Toba', 'Sumatera Utara', 'Danau Toba adalah danau vulkanik terbesar di dunia dengan luas 1.130 km².', 'https://images.unsplash.com/photo-1590736969955-71cc94901144?w=800', 'https://maps.google.com/?q=Danau+Toba+Sumatera+Utara', 4.7, 'Alam'),
('Pulau Komodo', 'Nusa Tenggara Timur', 'Pulau Komodo adalah bagian dari Taman Nasional Komodo yang merupakan habitat asli Komodo.', 'https://images.unsplash.com/photo-1607604276583-eef5d076aa5f?w=800', 'https://maps.google.com/?q=Pulau+Komodo+NTT+Indonesia', 4.9, 'Petualangan'),
('Gunung Bromo', 'Jawa Timur', 'Gunung Bromo adalah gunung berapi aktif yang paling terkenal di Jawa Timur.', 'https://images.unsplash.com/photo-1504893524553-b855bce32c67?w=800', 'https://maps.google.com/?q=Gunung+Bromo+Jawa+Timur', 4.8, 'Petualangan'),
('Kawah Ijen', 'Banyuwangi, Jawa Timur', 'Kawah Ijen terkenal dengan fenomena blue fire atau api biru yang langka.', 'https://images.unsplash.com/photo-1601142634808-38923eb7c560?w=800', 'https://maps.google.com/?q=Kawah+Ijen+Banyuwangi+Jawa+Timur', 4.7, 'Petualangan'),
('Ubud', 'Bali', 'Ubud adalah jantung budaya Bali yang menawarkan perpaduan sempurna antara alam, seni, dan spiritualitas.', 'https://images.unsplash.com/photo-1537996194471-e657df975ab4?w=800', 'https://maps.google.com/?q=Ubud+Bali+Indonesia', 4.8, 'Budaya'),
('Tokyo', 'Jepang', 'Tokyo adalah ibu kota Jepang yang menggabungkan tradisi kuno dengan teknologi futuristik.', 'https://images.unsplash.com/photo-1480796927426-f609979314bd?w=800', 'https://maps.google.com/?q=Tokyo+Jepang', 5.0, 'Budaya'),
('Seoul', 'Korea Selatan', 'Seoul adalah kota metropolitan yang dinamis dengan seni, fashion, dan kuliner kelas dunia.', 'https://images.unsplash.com/photo-1538485399081-7191377e8241?w=800', 'https://maps.google.com/?q=Seoul+Korea+Selatan', 4.9, 'Budaya'),
('Paris', 'Prancis', 'Paris — Kota Cahaya — adalah simbol cinta, seni, dan keanggunan.', 'https://images.unsplash.com/photo-1499856871958-5b9357976b82?w=800', 'https://maps.google.com/?q=Paris+Prancis', 5.0, 'Budaya'),
('London', 'Inggris', 'London adalah ibu kota Inggris yang kaya sejarah dan budaya.', 'https://images.unsplash.com/photo-1513635269975-59663e0ac1ad?w=800', 'https://maps.google.com/?q=London+Inggris', 4.9, 'Budaya'),
('Swiss Alps', 'Swiss', 'Swiss Alps menawarkan pemandangan gunung yang menakjubkan dan resort ski kelas dunia.', 'https://images.unsplash.com/photo-1530122037265-a5f1f91d3b99?w=800', 'https://maps.google.com/?q=Swiss+Alps+Swiss', 5.0, 'Petualangan'),
('New York City', 'USA', 'NYC — The City That Never Sleeps — menawarkan pengalaman urban terbaik.', 'https://images.unsplash.com/photo-1496442226666-8d4d0e62e6e9?w=800', 'https://maps.google.com/?q=New+York+City+USA', 4.9, 'Budaya'),
('Santorini', 'Yunani', 'Santorini adalah pulau paling romantis di Yunani dengan pemandangan caldera yang spektakuler.', 'https://images.unsplash.com/photo-1570077188670-e3a8d69ac5ff?w=800', 'https://maps.google.com/?q=Santorini+Yunani', 5.0, 'Budaya'),
('Dubai', 'Uni Emirat Arab', 'Dubai adalah kota futuristik dengan Burj Khalifa tertinggi dan inovasi teknologi.', 'https://images.unsplash.com/photo-1512453979798-5ea266f8880c?w=800', 'https://maps.google.com/?q=Dubai+Uni+Emirat+Arab', 4.9, 'Budaya'),
('Machu Picchu', 'Peru', 'Machu Picchu adalah situs arkeologi Inca paling terkenal di dunia.', 'https://images.unsplash.com/photo-1587595431973-160d0d94add1?w=800', 'https://maps.google.com/?q=Machu+Picchu+Peru', 5.0, 'Petualangan'),
('Maldives', 'Maladewa', 'Maldives adalah surga tropis dengan air turquoise dan resort over-water yang mewah.', 'https://images.unsplash.com/photo-1514282401047-d79a71a590e8?w=800', 'https://maps.google.com/?q=Maldives+Maladewa', 5.0, 'Budaya'),
('Rome', 'Italia', 'Rome adalah kota bersejarah dengan lapisan arsitektur klasik, piazza, dan peninggalan kekaisaran yang masih terasa sangat hidup.', 'https://images.unsplash.com/photo-1552832230-c0197dd311b5?w=800', 'https://maps.google.com/?q=Rome+Italia', 4.9, 'Budaya'),
('Hanoi', 'Vietnam', 'Hanoi menghadirkan perpaduan kuat antara kota lama, kuliner jalanan, dan ritme urban yang terasa lebih intim.', 'https://images.unsplash.com/photo-1508061253366-f7da158b6d46?w=800', 'https://maps.google.com/?q=Hanoi+Vietnam', 4.8, 'Budaya'),
('Phuket', 'Thailand', 'Phuket adalah destinasi pantai tropis yang menawarkan resort, pulau-pulau kecil, dan sunset yang sangat kuat secara visual.', 'https://images.unsplash.com/photo-1589394815804-964ed0be2eb5?w=800', 'https://maps.google.com/?q=Phuket+Thailand', 4.8, 'Bahari');

-- Sample Paket (contoh untuk wisata dengan id 1)
INSERT INTO tipe_paket (wisata_id, nama_paket, deskripsi, harga, durasi, fasilitas, min_orang, max_orang) VALUES
(1, 'Paket Komodo 3 Hari', 'Jelajahi Taman Nasional Komodo dengan pemandu lokal berpengalaman', 8500000, '3 Hari', 'Hotel, Makan, Transportasi, Tour Guide', 2, 10),
(1, 'Paket Diving Raja Ampat', 'Pengalaman diving terbaik di salah satu spot terbaik dunia', 15000000, '5 Hari', 'Akomodasi, Meals, Diving Equipment, Instructor', 2, 8),
(1, 'Paket Verifikasi Pembayaran Rp1', 'Khusus untuk uji alur pembayaran sebelum go-live. Bukan paket perjalanan publik.', 1, 'Tes pembayaran 1x transaksi', 'Simulasi checkout,Verifikasi notifikasi pembayaran', 1, 1);

-- Indeks untuk optimasi
CREATE INDEX idx_destinasi_tipe ON destinasi(tipe);
CREATE INDEX idx_destinasi_kategori ON destinasi(kategori);
CREATE INDEX idx_pemesanan_status ON pemesanan(status);
CREATE INDEX idx_pembayaran_status ON pembayaran(status_pembayaran);
CREATE INDEX idx_rating_review_status ON rating_review(status_review);

-- ════════════════════════════════════════
-- DATABASE SETUP COMPLETE
-- Ready untuk production use
-- ════════════════════════════════════════
