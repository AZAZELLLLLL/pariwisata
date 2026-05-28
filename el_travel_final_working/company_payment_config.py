"""Pusat pengaturan kanal pembayaran dan tujuan dana perusahaan.

Semua perubahan rekening, e-wallet, QRIS, dan perilaku kanal pembayaran
sebaiknya dilakukan dari file ini agar tim finance tidak perlu membuka template
atau logic route.
"""

FINANCE_ACCOUNT_CONFIG = {
    # Ganti identitas merchant perusahaan di bagian ini.
    'merchant_name': 'PT. EL TRAVEL INDONESIA',
    'merchant_short_name': 'EL Travel',
    'statement_email': 'finance@eltravel.id',
    'report_currency': 'IDR',

    # Ganti rekening bank perusahaan di bagian ini.
    'bank_accounts': [
        {
            'code': 'bca',
            'bank': 'BCA',
            'account_name': 'PT. EL TRAVEL INDONESIA',
            'account_number': '12345678901',
            'note': 'Ganti dengan rekening BCA resmi perusahaan.'
        },
        {
            'code': 'mandiri',
            'bank': 'Mandiri',
            'account_name': 'PT. EL TRAVEL INDONESIA',
            'account_number': '9876543210',
            'note': 'Ganti dengan rekening Mandiri resmi perusahaan.'
        }
    ],

    # Ganti akun e-wallet perusahaan di bagian ini.
    'ewallet_accounts': [
        {
            'code': 'shopeepay',
            'label': 'ShopeePay',
            'account_name': 'EL Travel Official',
            'account_number': '081234567890',
            'note': 'Ganti dengan akun ShopeePay bisnis resmi perusahaan.'
        },
        {
            'code': 'dana',
            'label': 'DANA',
            'account_name': 'EL Travel Official',
            'account_number': '081234567890',
            'note': 'Ganti dengan akun DANA bisnis resmi perusahaan.'
        },
        {
            'code': 'gopay',
            'label': 'GoPay',
            'account_name': 'EL Travel Official',
            'account_number': '081234567890',
            'note': 'Ganti dengan akun GoPay bisnis resmi perusahaan.'
        }
    ],

    # Isi link gambar QRIS bisnis resmi perusahaan di bagian ini.
    'qris': {
        'image_url': '',
        'payment_url': 'https://app.u.shopeepay.co.id/u/jWpNoQssXuEo6Ttqoe8ug',
        'merchant_name': 'PT. EL TRAVEL INDONESIA',
        'note': 'Ganti dengan link gambar QRIS bisnis resmi perusahaan agar pembayaran manual bisa diterima langsung.'
    }
}


FINANCE_PAYMENT_METHODS = {
    'bank_transfer': {
        'label': 'Transfer Bank',
        'description': 'Gunakan virtual account otomatis atau transfer manual ke rekening resmi perusahaan.',
        'icon': 'fa-building-columns',
        'supports_gateway': True,
        'enabled_payments': ['bni_va', 'bri_va', 'permata_va', 'echannel'],
        'destination_type': 'bank'
    },
    'qris': {
        'label': 'QRIS',
        'description': 'Scan QRIS bisnis perusahaan untuk pembayaran cepat dari mobile banking atau e-wallet.',
        'icon': 'fa-qrcode',
        'supports_gateway': True,
        'enabled_payments': ['qris'],
        'destination_type': 'qris'
    },
    'shopeepay': {
        'label': 'ShopeePay',
        'description': 'Bayar manual ke akun ShopeePay perusahaan, lalu simpan nomor referensi transaksi.',
        'icon': 'fa-wallet',
        'supports_gateway': False,
        'enabled_payments': [],
        'destination_type': 'ewallet'
    },
    'dana': {
        'label': 'DANA',
        'description': 'Bayar manual ke akun DANA perusahaan lalu kirimkan nomor referensi untuk verifikasi.',
        'icon': 'fa-mobile-screen-button',
        'supports_gateway': False,
        'enabled_payments': [],
        'destination_type': 'ewallet'
    },
    'gopay': {
        'label': 'GoPay',
        'description': 'Bayar manual ke akun GoPay perusahaan dengan verifikasi referensi transaksi.',
        'icon': 'fa-money-bill-transfer',
        'supports_gateway': False,
        'enabled_payments': [],
        'destination_type': 'ewallet'
    }
}


def get_ewallet_account(channel_code):
    """Return the configured e-wallet account for a specific channel."""
    for item in FINANCE_ACCOUNT_CONFIG['ewallet_accounts']:
        if item['code'] == channel_code:
            return item
    return None


def list_payment_destination_groups():
    """Return grouped destination settings for finance/admin screens."""
    return [
        {
            'key': 'bank',
            'label': 'Rekening Bank',
            'items': FINANCE_ACCOUNT_CONFIG['bank_accounts']
        },
        {
            'key': 'ewallet',
            'label': 'E-Wallet Perusahaan',
            'items': FINANCE_ACCOUNT_CONFIG['ewallet_accounts']
        },
        {
            'key': 'qris',
            'label': 'QRIS Perusahaan',
            'items': [FINANCE_ACCOUNT_CONFIG['qris']]
        }
    ]


def get_payment_destination(channel_code):
    """Resolve the target destination data for a payment channel."""
    if channel_code == 'bank_transfer':
        return {
            'type': 'bank',
            'items': FINANCE_ACCOUNT_CONFIG['bank_accounts']
        }
    if channel_code == 'qris':
        return {
            'type': 'qris',
            'item': FINANCE_ACCOUNT_CONFIG['qris']
        }
    ewallet = get_ewallet_account(channel_code)
    if ewallet:
        return {
            'type': 'ewallet',
            'item': ewallet
        }
    return {
        'type': 'unknown',
        'items': []
    }
