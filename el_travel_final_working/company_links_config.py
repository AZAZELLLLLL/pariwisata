from urllib.parse import quote_plus


# Ganti seluruh jalur komunikasi dan tautan resmi perusahaan dari file ini.
# File ini menjadi pusat pengelolaan link agar staff tidak perlu mencari link
# WhatsApp, telepon, email, Instagram, TikTok, atau YouTube di template.

SITE_CONTACT = {
    'company_name': 'EL Travel',
    'tagline': 'Travel lokal dan internasional dengan alur booking yang lebih rapi.',
    'founded_year': 2016,
    'address_lines': [
        'Jl. Pariwisata No. 88, Kebayoran Baru',
        'Jakarta Selatan, DKI Jakarta 12345'
    ],
    'address_short': 'Jl. Pariwisata No. 88, Jakarta Selatan 12345',
    'phone_display': '+62 812-3456-7890',
    'phone_raw': '6281234567890',
    'email': 'info@eltravel.id',
    'hours': [
        'Senin - Sabtu: 08.00 - 21.00 WIB',
        'Minggu: 09.00 - 18.00 WIB'
    ],
    'support_copy': 'Tim EL Travel siap membantu konsultasi itinerary, booking, pembayaran, dan keberangkatan.'
}


# Ganti semua tautan media sosial perusahaan di bagian ini.
SITE_SOCIAL = {
    'instagram': 'https://instagram.com/eltravel.id',
    'facebook': 'https://facebook.com/eltravel.id',
    'tiktok': 'https://tiktok.com/@eltravel.id',
    'youtube': 'https://youtube.com/@eltravelid'
}


def build_whatsapp_link(message='Halo EL Travel, saya ingin bertanya tentang perjalanan.'):
    """Build a WhatsApp deep-link from the configured company number."""
    encoded_message = quote_plus(message)
    return f"https://wa.me/{SITE_CONTACT['phone_raw']}?text={encoded_message}"


def build_phone_link():
    """Return a tel: link for the company phone number."""
    return f"tel:+{SITE_CONTACT['phone_raw']}"


def build_mailto_link(subject=''):
    """Return a mailto: link for the company email."""
    if subject:
        return f"mailto:{SITE_CONTACT['email']}?subject={quote_plus(subject)}"
    return f"mailto:{SITE_CONTACT['email']}"
