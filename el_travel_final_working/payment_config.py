"""Ganti copy pembayaran, mode demo, dan paket uji di file ini."""

PAYMENT_DISPLAY_CONFIG = {
    'page_copy': {
        'subtitle': 'Pilih pembayaran transfer bank, e-wallet, atau QRIS sesuai metode yang paling nyaman untuk Anda.',
        'gateway_note': 'Untuk pembayaran otomatis, isi MIDTRANS_SERVER_KEY dan MIDTRANS_CLIENT_KEY di file .env.',
        'manual_note': 'Kalau gateway belum dihubungkan, user masih bisa bayar manual ke rekening, e-wallet perusahaan, atau memakai QRIS demo akademik untuk presentasi.',
        'account_config_note': 'Semua tujuan pembayaran perusahaan sekarang dikelola dari file company_payment_config.py.',
        'finance_report_note': 'Riwayat pembayaran user juga bisa dipantau dari dashboard keuangan internal.',
        'demo_note': 'Mode Demo Akademik Hybrid akan membuat QRIS simulasi saat user memilih QRIS, lalu status pembayaran bisa disimulasikan sampai berhasil tanpa dana asli.'
    }
}

PAYMENT_DEMO_CONFIG = {
    'enabled': True,
    'label': 'Demo Akademik Hybrid',
    'primary_method': 'qris',
    'expires_minutes': 30,
    'hero_badge': 'Demo Guru Aktif',
    'checkout_note': 'Saat user memilih QRIS, sistem akan membuat kode QR simulasi untuk pengujian kelas tanpa uang asli.',
    'confirm_note': 'Setelah QR demo tampil, lanjutkan dengan tombol simulasi sukses agar guru bisa melihat perubahan status end-to-end.',
    'manual_fallback_note': 'ShopeePay, DANA, dan GoPay manual tetap disimpan sebagai fallback internal jika guru ingin melihat flow verifikasi admin.'
}

TEST_PAYMENT_PACKAGE = {
    'package_name': 'Paket Verifikasi Pembayaran Rp1',
    'description': 'Khusus untuk uji alur pembayaran sebelum go-live. Bukan paket perjalanan publik.',
    'price': 1,
    'duration': 'Tes pembayaran 1x transaksi',
    'facilities': 'Simulasi checkout,Verifikasi notifikasi pembayaran',
    'min_people': 1,
    'max_people': 1
}
