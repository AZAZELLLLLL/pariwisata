from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, session, Response
import csv
import io
import mysql.connector
from datetime import datetime, timedelta
import os
import json
import secrets
import smtplib
import base64
import hashlib
import re
import tempfile
from decimal import Decimal
from email.message import EmailMessage
from functools import wraps
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from werkzeug.security import generate_password_hash, check_password_hash
try:
    import certifi
except ImportError:  # pragma: no cover - optional dependency in local dev
    certifi = None
from company_links_config import SITE_CONTACT, SITE_SOCIAL, build_whatsapp_link
from contact_config import CONTACT_PAGE_CONTENT
from destination_media import DESTINATION_MEDIA
from company_payment_config import (
    FINANCE_ACCOUNT_CONFIG,
    FINANCE_PAYMENT_METHODS,
    get_payment_destination,
    list_payment_destination_groups,
)
from payment_config import PAYMENT_DEMO_CONFIG, PAYMENT_DISPLAY_CONFIG, TEST_PAYMENT_PACKAGE
from site_content import COMPANY_PROFILE


def load_local_env():
    """Load environment variables from a local .env file when available."""
    env_path = Path(__file__).with_name('.env')
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue

        key, value = line.split('=', 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)


def env_flag(name, default=False):
    """Read boolean-like environment flags with a safe default."""
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {'1', 'true', 'yes', 'on'}


def env_value(*names, default=''):
    """Return the first non-empty environment variable from a list of names."""
    for name in names:
        raw_value = os.getenv(name)
        if raw_value is not None and str(raw_value).strip() != '':
            return str(raw_value).strip()
    return default


def is_tidb_cloud_host(hostname):
    """Detect TiDB Cloud style hostnames so deployment defaults can be smarter."""
    host_value = (hostname or '').strip().lower()
    return host_value.endswith('.tidbcloud.com') or '.tidbcloud.com' in host_value


def resolve_db_ssl_ca_path():
    """Support either a CA file path or PEM content stored in env vars."""
    direct_path = env_value('DB_SSL_CA', 'TIDB_SSL_CA')
    if direct_path:
        return direct_path

    pem_content = env_value('DB_SSL_CA_CONTENT', 'TIDB_SSL_CA_CONTENT')
    if not pem_content:
        db_host = env_value('DB_HOST', 'TIDB_HOST')
        if is_tidb_cloud_host(db_host) and certifi:
            return certifi.where()
        return ''

    pem_text = pem_content.replace('\\n', '\n')
    temp_path = Path(tempfile.gettempdir()) / 'eltravel-db-ca.pem'
    temp_path.write_text(pem_text, encoding='utf-8')
    return str(temp_path)


load_local_env()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'eltravel_secret_key_2024')

REGION_CONFIG = {
    'asia': {
        'label': 'Asia',
        'countries': ['Indonesia', 'Jepang', 'Korea Selatan', 'Maladewa', 'Vietnam', 'Thailand', 'Uni Emirat Arab'],
        'image': 'https://images.unsplash.com/photo-1480796927426-f609979314bd?w=1200&q=80',
        'summary': 'Perpaduan perjalanan lokal Nusantara, city break modern, budaya klasik, dan resort tropis.',
        'accent': 'Asia Explorer',
        'icon': 'fa-earth-asia',
        'hint': 'Indonesia, Jepang, Vietnam, Thailand, Dubai'
    },
    'eropa': {
        'label': 'Eropa',
        'countries': ['Prancis', 'Inggris', 'Swiss', 'Yunani', 'Italia'],
        'image': 'https://images.unsplash.com/photo-1499856871958-5b9357976b82?w=1200&q=80',
        'summary': 'Arsitektur bersejarah, alpine escape, dan perjalanan kota yang lebih sinematik.',
        'accent': 'Classic Europe',
        'icon': 'fa-landmark',
        'hint': 'Prancis, Swiss, Inggris, Italia, Yunani'
    },
    'amerika': {
        'label': 'Amerika',
        'countries': ['USA', 'Peru'],
        'image': 'https://images.unsplash.com/photo-1499092346589-b9b6be3e94b2?w=1200&q=80',
        'summary': 'Pilihan perjalanan lintas benua dari skyline kota besar hingga petualangan bersejarah.',
        'accent': 'Urban & Adventure',
        'icon': 'fa-city',
        'hint': 'USA, Peru'
    },
    'afrika': {
        'label': 'Afrika',
        'countries': [],
        'image': 'https://images.unsplash.com/photo-1516026672322-bc52d61a55d5?w=1200&q=80',
        'summary': 'Safari, lanskap liar, dan perjalanan budaya Afrika akan hadir di katalog berikutnya.',
        'accent': 'Coming Soon',
        'icon': 'fa-binoculars',
        'hint': 'Destinasi Afrika akan segera hadir'
    },
    'oseania': {
        'label': 'Australia & Oseania',
        'countries': [],
        'image': 'https://images.unsplash.com/photo-1506973035872-a4ec16b8e8d9?w=1200&q=80',
        'summary': 'Pilihan Australia dan kepulauan Pasifik sedang kami siapkan untuk ekspansi destinasi berikutnya.',
        'accent': 'Coming Soon',
        'icon': 'fa-globe',
        'hint': 'Australia dan Oceania akan segera hadir'
    }
}

NAV_DESTINATION_REGIONS = [
    {
        'slug': region_slug,
        'label': region_data['label'],
        'icon': region_data['icon'],
        'hint': region_data['hint']
    }
    for region_slug, region_data in REGION_CONFIG.items()
]

NAV_PACKAGE_TYPES = [
    {'slug': 'solo', 'label': 'Paket Solo', 'icon': 'fa-user', 'hint': 'Ritme fleksibel untuk traveler mandiri'},
    {'slug': 'pasangan', 'label': 'Paket Pasangan', 'icon': 'fa-heart', 'hint': 'Trip lebih intim untuk dua orang'},
    {'slug': 'keluarga', 'label': 'Paket Keluarga', 'icon': 'fa-users', 'hint': 'Format nyaman untuk keluarga inti'},
    {'slug': 'grup', 'label': 'Paket Grup', 'icon': 'fa-people-group', 'hint': 'Perjalanan ramai untuk rombongan'}
]

COUNTRY_REGION_MAP = {}
for region_slug, region_data in REGION_CONFIG.items():
    for country_name in region_data['countries']:
        COUNTRY_REGION_MAP[country_name] = region_slug

GLOBE_COUNTRY_NAME_MAP = {
    'Indonesia': 'Indonesia',
    'Jepang': 'Japan',
    'Japan': 'Japan',
    'Korea Selatan': 'South Korea',
    'South Korea': 'South Korea',
    'Vietnam': 'Vietnam',
    'Thailand': 'Thailand',
    'Prancis': 'France',
    'France': 'France',
    'Italia': 'Italy',
    'Italy': 'Italy',
    'Swiss': 'Switzerland',
    'Switzerland': 'Switzerland',
    'Yunani': 'Greece',
    'Greece': 'Greece',
    'Maladewa': 'Maldives',
    'Maldives': 'Maldives',
    'Inggris': 'United Kingdom',
    'United Kingdom': 'United Kingdom',
    'USA': 'United States of America',
    'United States': 'United States of America',
    'United States of America': 'United States of America',
    'Uni Emirat Arab': 'United Arab Emirates',
    'United Arab Emirates': 'United Arab Emirates',
    'Peru': 'Peru',
    'Australia': 'Australia',
    'Selandia Baru': 'New Zealand',
    'New Zealand': 'New Zealand'
}

FEATURED_DESTINATION_ORDER = [
    'Labuan Bajo',
    'Raja Ampat',
    'Tokyo',
    'Paris',
    'Dubai',
    'Swiss Alps'
]

FEATURED_TRIP_META = {
    'Labuan Bajo': {
        'title': 'Labuan Bajo Signature Sailing Escape',
        'duration_code': '03D/02N',
        'duration_text': '3 Hari / 2 Malam',
        'departure_items': ['Berangkat mingguan dari Labuan Bajo', 'Private trip dan sharing trip tersedia'],
        'price': 8500000,
        'compare_price': 9400000
    },
    'Raja Ampat': {
        'title': 'Raja Ampat Reef and Island Journey',
        'duration_code': '04D/03N',
        'duration_text': '4 Hari / 3 Malam',
        'departure_items': ['Musim terbaik Oktober sampai April', 'Cocok untuk island hopping premium'],
        'price': 12800000,
        'compare_price': 13900000
    },
    'Tokyo': {
        'title': 'Tokyo City Lights and Culture Route',
        'duration_code': '05D/04N',
        'duration_text': '5 Hari / 4 Malam',
        'departure_items': ['Fleksibel mengikuti musim sakura atau autumn', 'Cocok untuk first timer Jepang'],
        'price': 16900000,
        'compare_price': 18200000
    },
    'Paris': {
        'title': 'Paris Museum and Riverfront Escape',
        'duration_code': '06D/05N',
        'duration_text': '6 Hari / 5 Malam',
        'departure_items': ['Pilihan itinerary romantis atau art-focused', 'Dapat digabung dengan Swiss dan London'],
        'price': 19800000,
        'compare_price': 21400000
    },
    'Dubai': {
        'title': 'Dubai Desert and Downtown Experience',
        'duration_code': '04D/03N',
        'duration_text': '4 Hari / 3 Malam',
        'departure_items': ['City stopover dan family trip tersedia', 'Gabungan desert safari dan city tour'],
        'price': 17600000,
        'compare_price': 18900000
    },
    'Swiss Alps': {
        'title': 'Swiss Alps Scenic Rail Signature',
        'duration_code': '07D/05N',
        'duration_text': '7 Hari / 5 Malam',
        'departure_items': ['Musim dingin dan summer scenery tersedia', 'Cocok untuk couple dan slow travel'],
        'price': 22900000,
        'compare_price': 24400000
    }
}

PACKAGE_TYPE_CONFIG = {
    'solo': {
        'label': 'Paket Solo',
        'headline': 'Pilihan paket untuk traveler yang ingin bergerak lebih fleksibel dan personal.',
        'summary': 'Cocok untuk user yang ingin itinerary rapi, ritme lebih tenang, dan biaya yang tetap terukur.',
        'multiplier': 1.0,
        'traveler_text': '1 traveler',
        'accent': 'Solo Escape'
    },
    'pasangan': {
        'label': 'Paket Pasangan',
        'headline': 'Format perjalanan untuk dua orang dengan pengalaman yang lebih intim dan terarah.',
        'summary': 'Cocok untuk honeymoon, anniversary trip, atau city break dengan ritme yang tidak terlalu padat.',
        'multiplier': 1.86,
        'traveler_text': '2 travelers',
        'accent': 'Couple Journey'
    },
    'keluarga': {
        'label': 'Paket Keluarga',
        'headline': 'Paket yang lebih nyaman untuk keluarga kecil dengan kebutuhan perjalanan yang lebih stabil.',
        'summary': 'Cocok untuk keluarga yang perlu ritme aman, akomodasi nyaman, dan koordinasi perjalanan yang jelas.',
        'multiplier': 3.45,
        'traveler_text': '3-4 travelers',
        'accent': 'Family Comfort'
    },
    'grup': {
        'label': 'Paket Grup',
        'headline': 'Pilihan trip untuk rombongan yang ingin berangkat bersama dengan harga lebih efisien.',
        'summary': 'Cocok untuk gathering, company trip, komunitas, atau perjalanan ramai dengan itinerary khusus.',
        'multiplier': 5.85,
        'traveler_text': '5+ travelers',
        'accent': 'Group Escape'
    }
}

DEFAULT_REGION_PRICE = {
    'asia': 15800000,
    'eropa': 20500000,
    'amerika': 21900000,
    'afrika': 21400000,
    'oseania': 23800000
}

DEFAULT_REGION_DURATION_CODE = {
    'asia': '05D/04N',
    'eropa': '06D/05N',
    'amerika': '07D/05N',
    'afrika': '07D/06N',
    'oseania': '06D/05N'
}

DEFAULT_REGION_DURATION_TEXT = {
    'asia': '5 Hari / 4 Malam',
    'eropa': '6 Hari / 5 Malam',
    'amerika': '7 Hari / 5 Malam',
    'afrika': '7 Hari / 6 Malam',
    'oseania': '6 Hari / 5 Malam'
}

GOOGLE_AUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
GOOGLE_TOKEN_URL = 'https://oauth2.googleapis.com/token'
GOOGLE_USERINFO_URL = 'https://openidconnect.googleapis.com/v1/userinfo'
GOOGLE_SCOPE = 'openid email profile'
LOGIN_OTP_TTL_MINUTES = 10
LOGIN_OTP_MAX_ATTEMPTS = 5
LOGIN_OTP_STORE = {}
EMAIL_PATTERN = re.compile(r'^[A-Za-z0-9._%+-]+@gmail\.com$', re.IGNORECASE)
GENERIC_EMAIL_PATTERN = re.compile(r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$', re.IGNORECASE)
PASSWORD_MIN_LENGTH = 8
GENDER_OPTIONS = [
    'Laki-laki',
    'Perempuan',
    'Lainnya',
    'Tidak ingin menyebutkan'
]
MIDTRANS_SANDBOX_BASE_URL = 'https://app.sandbox.midtrans.com'
MIDTRANS_PRODUCTION_BASE_URL = 'https://app.midtrans.com'
MIDTRANS_SNAP_SANDBOX_JS = 'https://app.sandbox.midtrans.com/snap/snap.js'
MIDTRANS_SNAP_PRODUCTION_JS = 'https://app.midtrans.com/snap/snap.js'
PAYMENT_METHOD_CONFIG = FINANCE_PAYMENT_METHODS

ORDER_STATUS_META = {
    'payment_pending': {
        'label': 'Menunggu Pembayaran',
        'description': 'Lengkapi pembayaran untuk mengunci kursi dan jadwal keberangkatan Anda.',
        'badge_class': 'pending',
        'icon': 'fa-wallet'
    },
    'verifying': {
        'label': 'Menunggu Verifikasi',
        'description': 'Pembayaran sudah masuk dan sedang diperiksa oleh tim kami.',
        'badge_class': 'verifying',
        'icon': 'fa-hourglass-half'
    },
    'confirmed': {
        'label': 'Terkonfirmasi',
        'description': 'Pesanan sudah diproses dan siap dilanjutkan ke koordinasi keberangkatan.',
        'badge_class': 'confirmed',
        'icon': 'fa-circle-check'
    },
    'completed': {
        'label': 'Perjalanan Selesai',
        'description': 'Trip sudah selesai. Anda bisa melihat ulang detail atau menulis review.',
        'badge_class': 'completed',
        'icon': 'fa-plane-arrival'
    },
    'cancelled': {
        'label': 'Dibatalkan',
        'description': 'Pesanan ini dibatalkan atau tidak dilanjutkan.',
        'badge_class': 'cancelled',
        'icon': 'fa-ban'
    }
}

STAFF_ROLE_LABELS = {
    'owner': 'Owner',
    'finance': 'Finance',
    'operasional': 'Operasional',
    'customer_service': 'Customer Service'
}

STAFF_ROLE_OPTIONS = [
    {'value': role_key, 'label': role_label}
    for role_key, role_label in STAFF_ROLE_LABELS.items()
]

BACKOFFICE_OPERATIONAL_STATUS_OPTIONS = [
    'baru',
    'menunggu_pembayaran',
    'verifikasi_pembayaran',
    'siapkan_tiket',
    'siapkan_voucher',
    'siap_berangkat',
    'selesai',
    'dibatalkan'
]

BACKOFFICE_TICKET_STATUS_OPTIONS = [
    'belum_dibuat',
    'diproses',
    'terbit'
]

BACKOFFICE_VOUCHER_STATUS_OPTIONS = [
    'belum_dibuat',
    'diproses',
    'terkirim'
]

BACKOFFICE_DOCUMENT_STATUS_OPTIONS = [
    'belum_lengkap',
    'menunggu_user',
    'lengkap'
]

BACKOFFICE_DESTINATION_TYPES = ['lokal', 'internasional']
BACKOFFICE_CATEGORY_OPTIONS = [
    'Bahari',
    'Budaya',
    'Alam',
    'Petualangan',
    'Religi',
    'Kota',
    'Kuliner',
    'Pegunungan'
]
BACKOFFICE_PACKAGE_KIND_OPTIONS = ['solo', 'pasangan', 'keluarga', 'grup', 'custom']
BACKOFFICE_PACKAGE_STATUS_OPTIONS = ['aktif', 'draft', 'nonaktif']
BACKOFFICE_REGION_OPTIONS = [
    {'slug': slug, 'label': data['label']}
    for slug, data in REGION_CONFIG.items()
]
PROMO_DISCOUNT_TYPE_OPTIONS = [
    {'value': 'percent', 'label': 'Persentase'},
    {'value': 'amount', 'label': 'Nominal Rupiah'}
]
PROMO_STATUS_META = {
    'active': {'label': 'Aktif', 'tone': 'success'},
    'upcoming': {'label': 'Terjadwal', 'tone': 'info'},
    'expired': {'label': 'Berakhir', 'tone': 'muted'},
    'inactive': {'label': 'Nonaktif', 'tone': 'warning'}
}

DESTINATION_MOMENT_META = {
    'Labuan Bajo': {
        'moment_title': 'Golden hour di atas bukit Padar dan laut yang berubah tembaga',
        'best_time': 'April - Oktober, menjelang sunset',
        'moment_image': 'https://images.unsplash.com/photo-1534008897995-27a23e859048?w=1400&q=80',
        'moment_copy': 'Saat matahari mulai turun, siluet perbukitan dan lekuk pantai di sekitar Labuan Bajo terasa jauh lebih dramatis. Ini adalah momen yang paling sering membuat traveler merasa destinasi ini lebih indah dari ekspektasi awalnya.'
    },
    'Raja Ampat': {
        'moment_title': 'Pagi yang jernih ketika gugusan pulau muncul dari kabut tipis',
        'best_time': 'Oktober - April, pukul 06.00 - 08.00',
        'moment_image': 'https://images.unsplash.com/photo-1518509562904-e7ef99cdcc86?w=1400&q=80',
        'moment_copy': 'Raja Ampat terasa paling magis saat air tenang, langit cerah, dan pulau-pulau karst muncul perlahan dari cahaya pagi. Ini momen yang biasanya dicari untuk island hopping dan foto panorama.'
    },
    'Candi Borobudur': {
        'moment_title': 'Sunrise ketika relief dan stupa mulai tersentuh cahaya pertama',
        'best_time': 'Musim kemarau, sebelum pukul 06.00',
        'moment_image': 'https://images.unsplash.com/photo-1555400038-63f5ba517a47?w=1400&q=80',
        'moment_copy': 'Borobudur tidak hanya kuat secara visual, tetapi juga atmosfernya. Saat cahaya pagi menyapu stupa dan kabut di sekitar lembah belum benar-benar hilang, suasana spiritualnya terasa lebih penuh.'
    },
    'Gunung Bromo': {
        'moment_title': 'Lautan pasir dan kaldera yang menyala di waktu sunrise',
        'best_time': 'Juni - September, sebelum matahari terbit',
        'moment_image': 'https://images.unsplash.com/photo-1504893524553-b855bce32c67?w=1400&q=80',
        'moment_copy': 'Momen terbaik Bromo biasanya datang saat langit masih gelap lalu perlahan berubah jingga. Perubahan warna di atas kaldera memberi pengalaman yang sangat ikonik bagi first timer maupun traveler yang kembali lagi.'
    },
    'Tokyo': {
        'moment_title': 'Blue hour di persimpangan kota ketika lampu mulai menyala',
        'best_time': 'Maret - April atau Oktober - November, sore menuju malam',
        'moment_image': 'https://images.unsplash.com/photo-1540959733332-eab4deabeeaf?w=1400&q=80',
        'moment_copy': 'Tokyo terasa paling kuat justru di jeda antara sore dan malam. Lampu kota mulai hidup, ritme jalanan meningkat, dan perpaduan modernitas dengan detail budaya lokal terasa lebih jelas.'
    },
    'Paris': {
        'moment_title': 'Sore keemasan di tepi Seine dengan langit yang lembut',
        'best_time': 'April - Juni atau September, menjelang sunset',
        'moment_image': 'https://images.unsplash.com/photo-1522093007474-d86e9bf7ba6f?w=1400&q=80',
        'moment_copy': 'Paris punya banyak wajah, tetapi momen yang paling membekas biasanya terjadi saat sore mulai turun. Pantulan cahaya di sungai, fasad bangunan tua, dan ritme kota membuat suasananya terasa sangat sinematik.'
    },
    'Swiss Alps': {
        'moment_title': 'Panorama alpine ketika cahaya tipis membuka lapisan pegunungan',
        'best_time': 'Desember - Februari untuk salju, Juni - Agustus untuk green season',
        'moment_image': 'https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?w=1400&q=80',
        'moment_copy': 'Swiss Alps paling memikat ketika horizon terbuka dan pegunungan muncul berlapis-lapis. Baik saat bersalju maupun saat hijau, sensasinya tetap menawarkan rasa hening dan megah sekaligus.'
    },
    'Dubai': {
        'moment_title': 'Peralihan dari skyline modern ke warna gurun di golden hour',
        'best_time': 'November - Maret, sore hari',
        'moment_image': 'https://images.unsplash.com/photo-1518684079-3c830dcef090?w=1400&q=80',
        'moment_copy': 'Dubai bukan hanya kota tinggi dan pusat belanja. Di jam emas, kontras antara gedung modern dan bentang gurun di sekitarnya memberi pengalaman visual yang sangat kuat dan berbeda dari city trip biasa.'
    },
    'Machu Picchu': {
        'moment_title': 'Kabut tipis yang membuka situs perlahan dari lereng pegunungan',
        'best_time': 'Mei - September, pagi hari',
        'moment_image': 'https://images.unsplash.com/photo-1587595431973-160d0d94add1?w=1400&q=80',
        'moment_copy': 'Machu Picchu paling berkesan saat kabut belum sepenuhnya naik. Situs ini terasa muncul perlahan dari lanskap, membuat pengalaman pertama melihatnya jadi jauh lebih emosional.'
    },
    'Maldives': {
        'moment_title': 'Sunset di atas laut tenang dengan warna langit yang sangat bersih',
        'best_time': 'November - April, menjelang matahari terbenam',
        'moment_image': 'https://images.unsplash.com/photo-1514282401047-d79a71a590e8?w=1400&q=80',
        'moment_copy': 'Maldives terasa paling memikat saat laut sedang sangat tenang dan langit sore berubah bertahap. Ini momen yang sering membuat destinasi ini terasa benar-benar seperti escape yang tenang dan privat.'
    },
    'Rome': {
        'moment_title': 'Senja hangat ketika bangunan batu tua berubah lebih dramatis',
        'best_time': 'April - Juni atau September, sore hingga malam awal',
        'moment_image': 'https://images.unsplash.com/photo-1552832230-c0197dd311b5?w=1400&q=80',
        'moment_copy': 'Rome terasa paling kuat saat cahaya sore mulai rendah dan tekstur kota tua lebih muncul. Ini waktu terbaik untuk merasakan sisi sejarah, jalan kaki santai, dan suasana klasik Eropa yang lebih hidup.'
    },
    'Hanoi': {
        'moment_title': 'Pagi tenang ketika kota lama mulai hidup perlahan',
        'best_time': 'Oktober - April, pagi hari',
        'moment_image': 'https://images.unsplash.com/photo-1508061253366-f7da158b6d46?w=1400&q=80',
        'moment_copy': 'Hanoi paling menarik ketika aktivitas kota mulai naik pelan-pelan. Perpaduan arsitektur lama, ritme jalan, dan kuliner pagi membuat pengalaman berkunjung terasa lebih dekat dan autentik.'
    },
    'Phuket': {
        'moment_title': 'Golden hour di pantai saat warna laut dan langit sama-sama hangat',
        'best_time': 'November - April, menjelang sunset',
        'moment_image': 'https://images.unsplash.com/photo-1589394815804-964ed0be2eb5?w=1400&q=80',
        'moment_copy': 'Phuket biasanya terasa paling memikat saat langit sore mulai turun dan garis pantai terlihat lebih bersih. Ini momen yang pas untuk menikmati sisi tropisnya sebelum malam mulai ramai.'
    }
}


def safe_int(value, default=0):
    """Convert Decimal/None/string values to integer for UI display."""
    try:
        if value is None:
            return default
        if isinstance(value, Decimal):
            return int(value)
        return int(Decimal(str(value)))
    except (TypeError, ValueError, ArithmeticError):
        return default


def format_idr(value):
    """Format integer to IDR text used in templates."""
    amount = safe_int(value)
    return f"IDR {amount:,.0f}".replace(',', '.')


def get_country_name(wisata_item):
    """Return display country name for local and international destinations."""
    explicit_country = (wisata_item.get('negara') or '').strip()
    if explicit_country:
        return explicit_country
    if (wisata_item.get('tipe') or '').lower() == 'lokal':
        return 'Indonesia'
    return (wisata_item.get('lokasi') or '').strip() or 'Internasional'


def get_globe_geo_name(country_name):
    """Translate local country labels into the names used by the globe dataset."""
    normalized_country = (country_name or '').strip()
    return GLOBE_COUNTRY_NAME_MAP.get(normalized_country, normalized_country)


def build_globe_country_targets(destinations):
    """Build supported globe click targets from the destinations stored in the database."""
    seen_geo_names = set()
    target_rows = []

    for item in destinations or []:
        db_country_name = get_country_name(item)
        if not db_country_name:
            continue

        geo_name = get_globe_geo_name(db_country_name)
        if not geo_name or geo_name in seen_geo_names:
            continue

        seen_geo_names.add(geo_name)
        target_rows.append({
            'db_name': db_country_name,
            'geo_name': geo_name
        })

    return sorted(target_rows, key=lambda row: row['db_name'])


def is_gmail_address(value):
    """Validate Gmail addresses used as local account identifiers."""
    return bool(EMAIL_PATTERN.match((value or '').strip()))


def is_valid_email_address(value):
    """Validate a generic email address used by staff/backoffice accounts."""
    return bool(GENERIC_EMAIL_PATTERN.match((value or '').strip()))


def sanitize_phone_number(value):
    """Keep only numeric phone data and leading plus sign for display/use."""
    cleaned = re.sub(r'[^0-9+]', '', (value or '').strip())
    if cleaned.startswith('00'):
        cleaned = '+' + cleaned[2:]
    return cleaned[:20]


def normalize_gender(value):
    """Normalize gender input against the supported registration options."""
    normalized = (value or '').strip()
    return normalized if normalized in GENDER_OPTIONS else GENDER_OPTIONS[-1]


def hash_verification_code(code_value):
    """Hash OTP codes before storing them in the database."""
    return hashlib.sha256((code_value or '').encode('utf-8')).hexdigest()


def generate_human_challenge(scope):
    """Create a simple arithmetic challenge to slow down bots."""
    left = secrets.randbelow(7) + 2
    right = secrets.randbelow(7) + 2
    answer = left + right
    session[f'{scope}_captcha_question'] = f'{left} + {right}'
    session[f'{scope}_captcha_answer'] = str(answer)
    return session[f'{scope}_captcha_question']


def get_human_challenge(scope):
    """Read or create the arithmetic challenge for a form scope."""
    question = session.get(f'{scope}_captcha_question')
    if not question or f'{scope}_captcha_answer' not in session:
        question = generate_human_challenge(scope)
    return question


def refresh_human_challenge(scope):
    """Replace the current arithmetic challenge after every attempt."""
    session.pop(f'{scope}_captcha_question', None)
    session.pop(f'{scope}_captcha_answer', None)
    return generate_human_challenge(scope)


def validate_human_challenge(scope, answer_value, honeypot_value=''):
    """Validate the visible captcha answer and the hidden honeypot field."""
    expected = session.get(f'{scope}_captcha_answer', '')
    submitted = (answer_value or '').strip()
    if honeypot_value:
        refresh_human_challenge(scope)
        return False
    is_valid = bool(expected and secrets.compare_digest(expected, submitted))
    refresh_human_challenge(scope)
    return is_valid


def mask_phone_number(phone_value):
    """Mask phone numbers for UI confirmations."""
    digits = re.sub(r'[^0-9]', '', phone_value or '')
    if len(digits) <= 4:
        return digits
    return f"{digits[:3]}{'*' * max(len(digits) - 5, 1)}{digits[-2:]}"


def midtrans_is_production():
    """Return whether Midtrans live mode should be used."""
    return os.getenv('MIDTRANS_IS_PRODUCTION', '').strip().lower() in ['1', 'true', 'yes', 'on']


def midtrans_base_url():
    """Resolve Midtrans API base URL from environment."""
    return MIDTRANS_PRODUCTION_BASE_URL if midtrans_is_production() else MIDTRANS_SANDBOX_BASE_URL


def midtrans_snap_js_url():
    """Resolve Midtrans Snap JS URL from environment."""
    return MIDTRANS_SNAP_PRODUCTION_JS if midtrans_is_production() else MIDTRANS_SNAP_SANDBOX_JS


def midtrans_is_configured():
    """Check whether Midtrans credentials are available."""
    return bool(os.getenv('MIDTRANS_SERVER_KEY') and os.getenv('MIDTRANS_CLIENT_KEY'))


def get_midtrans_client_key():
    """Return Midtrans client key for Snap.js."""
    return os.getenv('MIDTRANS_CLIENT_KEY', '').strip()


def payment_demo_enabled():
    """Return whether the local academic demo payment flow is active."""
    return env_flag('PAYMENT_DEMO_ENABLED', PAYMENT_DEMO_CONFIG.get('enabled', False))


def build_demo_payment_reference(pemesanan_id):
    """Create a readable local reference for simulated QRIS transactions."""
    suffix = datetime.now().strftime('%H%M%S')
    return f"DEMOQR-{safe_int(pemesanan_id):06d}-{suffix}"


def build_demo_qris_data_uri(pemesanan_id, amount, reference_code):
    """Generate a visual pseudo-QR image for classroom payment demos."""
    grid_size = 25
    module_size = 8
    margin = 18
    canvas_size = grid_size * module_size + margin * 2
    digest = hashlib.sha256(f"{pemesanan_id}|{amount}|{reference_code}".encode('utf-8')).digest()
    bits = ''.join(f'{byte:08b}' for byte in digest)
    finder_positions = {(0, 0), (0, grid_size - 7), (grid_size - 7, 0)}
    rects = [
        f"<rect x='0' y='0' width='{canvas_size}' height='{canvas_size + 82}' rx='28' fill='#fffaf0'/>",
        f"<rect x='12' y='12' width='{canvas_size - 24}' height='{canvas_size + 58}' rx='22' fill='white' stroke='#ead7a1' stroke-width='2'/>"
    ]

    def append_finder(x_index, y_index):
        x_base = margin + x_index * module_size
        y_base = margin + y_index * module_size
        rects.append(f"<rect x='{x_base}' y='{y_base}' width='{module_size * 7}' height='{module_size * 7}' rx='10' fill='#1f2f5a'/>")
        rects.append(f"<rect x='{x_base + module_size}' y='{y_base + module_size}' width='{module_size * 5}' height='{module_size * 5}' rx='6' fill='white'/>")
        rects.append(f"<rect x='{x_base + module_size * 2}' y='{y_base + module_size * 2}' width='{module_size * 3}' height='{module_size * 3}' rx='4' fill='#1f2f5a'/>")

    for x_index, y_index in finder_positions:
        append_finder(x_index, y_index)

    bit_index = 0
    for y_index in range(grid_size):
        for x_index in range(grid_size):
            in_finder = any(
                fx <= x_index <= fx + 6 and fy <= y_index <= fy + 6
                for fx, fy in finder_positions
            )
            if in_finder:
                continue
            bit_value = bits[bit_index % len(bits)]
            bit_index += 1
            if bit_value == '1':
                x_base = margin + x_index * module_size
                y_base = margin + y_index * module_size
                rects.append(
                    f"<rect x='{x_base}' y='{y_base}' width='{module_size}' height='{module_size}' rx='1.6' fill='#1f2f5a'/>"
                )

    safe_reference = (reference_code or 'DEMO-QR').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    rects.append(
        f"<text x='{canvas_size / 2}' y='{canvas_size + 30}' text-anchor='middle' "
        "font-family='Arial, sans-serif' font-size='18' font-weight='700' fill='#1f2f5a'>DEMO QRIS</text>"
    )
    rects.append(
        f"<text x='{canvas_size / 2}' y='{canvas_size + 52}' text-anchor='middle' "
        "font-family='Arial, sans-serif' font-size='12' fill='#6b7280'>Simulasi akademik - tidak memotong saldo</text>"
    )
    rects.append(
        f"<text x='{canvas_size / 2}' y='{canvas_size + 70}' text-anchor='middle' "
        f"font-family='Arial, sans-serif' font-size='11' fill='#8b6a1b'>{safe_reference}</text>"
    )

    svg_markup = (
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{canvas_size}' height='{canvas_size + 82}' "
        f"viewBox='0 0 {canvas_size} {canvas_size + 82}'>{''.join(rects)}</svg>"
    )
    encoded_svg = base64.b64encode(svg_markup.encode('utf-8')).decode('ascii')
    return f"data:image/svg+xml;base64,{encoded_svg}"


def create_demo_qris_transaction_for_booking(pemesanan, metode_pembayaran):
    """Build a local QRIS demo transaction for classroom presentations."""
    expires_minutes = safe_int(PAYMENT_DEMO_CONFIG.get('expires_minutes'), 30) or 30
    amount = safe_int(pemesanan.get('total_harga'))
    reference_code = build_demo_payment_reference(pemesanan.get('id'))
    expires_at = datetime.now() + timedelta(minutes=expires_minutes)
    payment_method = PAYMENT_METHOD_CONFIG.get(metode_pembayaran, {})

    detail_map = {
        'demo_mode': '1',
        'demo_label': PAYMENT_DEMO_CONFIG.get('label', 'Demo Akademik Hybrid'),
        'demo_reference': reference_code,
        'demo_expires_at': expires_at.isoformat(timespec='seconds'),
        'demo_expires_label': expires_at.strftime('%d %b %Y %H:%M'),
        'demo_total': str(amount),
        'demo_instruction': PAYMENT_DEMO_CONFIG.get('confirm_note', ''),
        'payment_label': payment_method.get('label', 'QRIS')
    }

    return {
        'gateway_order_id': f"DEMO-{pemesanan.get('id')}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        'payment_reference': reference_code,
        'detail_map': detail_map,
        'raw_payload': {
            'provider': 'demo_qris',
            'label': PAYMENT_DEMO_CONFIG.get('label', 'Demo Akademik Hybrid'),
            'booking_id': pemesanan.get('id'),
            'amount': amount,
            'reference_code': reference_code,
            'expires_at': expires_at.isoformat(timespec='seconds')
        }
    }


def enrich_demo_payment_detail_map(pemesanan, pembayaran, payment_detail_map):
    """Attach derived QR image and helper labels for demo QRIS transactions."""
    enriched_map = dict(payment_detail_map or {})
    if not pembayaran or pembayaran.get('gateway_provider') != 'demo_qris':
        return enriched_map

    reference_code = enriched_map.get('demo_reference') or pembayaran.get('payment_reference') or build_demo_payment_reference(pemesanan.get('id'))
    amount = pembayaran.get('jumlah_dibayar') or pemesanan.get('total_harga') or 0
    enriched_map['demo_reference'] = reference_code
    enriched_map['demo_qr_image'] = build_demo_qris_data_uri(pemesanan.get('id'), amount, reference_code)

    expires_label = enriched_map.get('demo_expires_label', '').strip()
    expires_raw = enriched_map.get('demo_expires_at', '').strip()
    if not expires_label and expires_raw:
        try:
            expires_label = datetime.fromisoformat(expires_raw).strftime('%d %b %Y %H:%M')
        except ValueError:
            expires_label = expires_raw
    if expires_label:
        enriched_map['demo_expires_label'] = expires_label

    return enriched_map


def complete_demo_qris_payment(cursor, pembayaran, pemesanan, payment_detail_map):
    """Mark a demo QRIS transaction as paid for classroom verification flows."""
    timestamp_now = datetime.now()
    reference_code = (payment_detail_map or {}).get('demo_reference') or pembayaran.get('payment_reference') or build_demo_payment_reference(pemesanan.get('id'))
    transaction_id = f"DEMO-TXN-{pembayaran['id']}-{timestamp_now.strftime('%H%M%S')}"
    updated_detail_map = dict(payment_detail_map or {})
    updated_detail_map['demo_reference'] = reference_code
    updated_detail_map['demo_paid_at'] = timestamp_now.isoformat(timespec='seconds')
    updated_detail_map['demo_paid_label'] = timestamp_now.strftime('%d %b %Y %H:%M')
    updated_detail_map['demo_transaction_id'] = transaction_id

    cursor.execute("""
        UPDATE pembayaran
        SET metode_pembayaran = 'qris',
            status_pembayaran = 'berhasil',
            tanggal_pembayaran = %s,
            jumlah_dibayar = %s,
            gateway_provider = 'demo_qris',
            gateway_status = 'settlement_demo',
            gateway_transaction_id = %s,
            channel_code = 'qris_demo',
            payment_reference = %s,
            paid_at = %s,
            raw_response_json = %s
        WHERE id = %s
    """, (
        timestamp_now,
        pemesanan.get('total_harga'),
        transaction_id,
        reference_code,
        timestamp_now,
        json.dumps({
            'provider': 'demo_qris',
            'status': 'settlement_demo',
            'transaction_id': transaction_id,
            'paid_at': timestamp_now.isoformat(timespec='seconds'),
            'reference_code': reference_code
        }),
        pembayaran['id']
    ))
    replace_payment_details(cursor, pembayaran['id'], updated_detail_map)
    cursor.execute("UPDATE pemesanan SET status = 'confirmed' WHERE id = %s", (pemesanan['id'],))
    ensure_operational_order_record(cursor, pemesanan['id'])
    sync_operational_status(cursor, pemesanan['id'], order_status='confirmed', payment_status='berhasil')
    append_payment_audit_log(
        cursor,
        pembayaran['id'],
        pemesanan['id'],
        'Simulasi pembayaran demo berhasil',
        f"QRIS demo ditandai berhasil untuk kebutuhan presentasi dengan referensi {reference_code}.",
        actor_type='customer',
        actor_name=pemesanan.get('nama_pemesan') or 'Customer'
    )
    append_order_status_log(
        cursor,
        pemesanan['id'],
        'Pembayaran demo berhasil',
        'Sistem menandai simulasi QRIS akademik sebagai lunas agar alur operasional bisa dipresentasikan end-to-end.',
        actor_type='system',
        actor_name='Demo Payment'
    )
    return updated_detail_map


def get_manual_qris_image():
    """Read optional company QRIS image URL from config or environment."""
    return os.getenv('COMPANY_QRIS_IMAGE_URL', '').strip() or FINANCE_ACCOUNT_CONFIG['qris'].get('image_url', '').strip()


def get_destination_media(destination_name):
    """Return fallback image metadata for a destination when database data is missing."""
    return DESTINATION_MEDIA.get(destination_name, {})


def apply_destination_media(destination_item):
    """Prefer database media fields, then fall back to curated static metadata."""
    if not destination_item:
        return destination_item
    updated_item = dict(destination_item)
    media = get_destination_media(updated_item.get('nama'))

    updated_item['foto'] = (updated_item.get('foto') or '').strip() or media.get('image', '')
    updated_item['moment_image'] = (updated_item.get('moment_foto') or '').strip() or media.get('moment_image') or updated_item.get('foto')
    updated_item['image_thumbnail'] = (updated_item.get('thumbnail_foto') or '').strip() or media.get('thumbnail') or updated_item.get('foto')
    updated_item['image_source_url'] = (updated_item.get('foto_source_url') or '').strip() or media.get('source_url', '')
    updated_item['image_source_label'] = (updated_item.get('foto_source_label') or '').strip() or media.get('source_label', '')
    return updated_item


def apply_destination_media_list(destination_rows):
    """Apply curated image overrides to a list of destination rows."""
    return [apply_destination_media(item) for item in (destination_rows or [])]


def get_default_price(region_slug, tipe=''):
    """Return fallback price when package data is not present."""
    if (tipe or '').strip().lower() == 'lokal':
        return 7900000
    return DEFAULT_REGION_PRICE.get(region_slug, DEFAULT_REGION_PRICE['asia'])


def get_default_duration_code(region_slug, tipe=''):
    """Return fallback duration code for destination cards."""
    if (tipe or '').strip().lower() == 'lokal':
        return '03D/02N'
    return DEFAULT_REGION_DURATION_CODE.get(region_slug, DEFAULT_REGION_DURATION_CODE['asia'])


def get_default_duration_text(region_slug, tipe=''):
    """Return fallback duration text for destination cards."""
    if (tipe or '').strip().lower() == 'lokal':
        return '3 Hari / 2 Malam'
    return DEFAULT_REGION_DURATION_TEXT.get(region_slug, DEFAULT_REGION_DURATION_TEXT['asia'])


def get_region_slug(country_name='', tipe=''):
    """Map destination country to a region slug used across filters and UI."""
    normalized_tipe = (tipe or '').strip().lower()
    normalized_country = (country_name or '').strip()

    if normalized_tipe == 'lokal' or normalized_country.lower() == 'indonesia':
        return 'asia'
    return COUNTRY_REGION_MAP.get(normalized_country, 'asia')


def append_country_condition(conditions, params, country_name):
    """Apply country-level filter for local and international destinations."""
    normalized_country = (country_name or '').strip()
    if not normalized_country:
        return

    if normalized_country.lower() == 'indonesia':
        conditions.append("(d.tipe = %s OR COALESCE(NULLIF(w.negara, ''), %s) = %s)")
        params.extend(['lokal', 'Indonesia', 'Indonesia'])
        return

    conditions.append("COALESCE(NULLIF(w.negara, ''), w.lokasi) = %s")
    params.append(normalized_country)


def append_region_condition(conditions, params, region_slug):
    """Apply continent filter while keeping Indonesia grouped inside Asia."""
    if region_slug not in REGION_CONFIG:
        return

    countries = list(REGION_CONFIG[region_slug]['countries'])
    subconditions = []

    if 'Indonesia' in countries:
        subconditions.append("(d.tipe = %s OR COALESCE(NULLIF(w.negara, ''), %s) = %s)")
        params.extend(['lokal', 'Indonesia', 'Indonesia'])
        countries.remove('Indonesia')

    if countries:
        placeholders = ', '.join(['%s'] * len(countries))
        subconditions.append(f"COALESCE(NULLIF(w.negara, ''), w.lokasi) IN ({placeholders})")
        params.extend(countries)

    if subconditions:
        conditions.append(f"({' OR '.join(subconditions)})")
    else:
        conditions.append("1 = 0")


def build_country_filters(region_slug, destinations):
    """Build contextual country chips from the available destination data."""
    if region_slug not in REGION_CONFIG:
        return []

    counts = {}
    for item in destinations:
        country_label = get_country_name(item)
        counts[country_label] = counts.get(country_label, 0) + 1

    ordered_countries = [
        country_name for country_name in REGION_CONFIG[region_slug]['countries']
        if country_name in counts
    ]
    ordered_countries.extend(sorted(country for country in counts if country not in ordered_countries))

    return [
        {
            'label': country_name,
            'count': counts[country_name]
        }
        for country_name in ordered_countries
    ]


def normalize_next_url(next_url):
    """Keep redirect targets inside this application."""
    if not next_url:
        return url_for('index')
    if next_url.startswith('http://') or next_url.startswith('https://'):
        return url_for('index')
    if not next_url.startswith('/'):
        return url_for('index')
    return next_url


def generate_login_code():
    """Create a random six-digit code for email verification."""
    digits = '0123456789'
    return ''.join(secrets.choice(digits) for _ in range(6))


def mask_email(email_value):
    """Return partially masked Gmail for OTP status UI."""
    email_value = (email_value or '').strip()
    if '@' not in email_value:
        return email_value
    local_part, domain_part = email_value.split('@', 1)
    if len(local_part) <= 2:
        masked_local = local_part[0] + '*'
    else:
        masked_local = local_part[:2] + ('*' * max(len(local_part) - 3, 1)) + local_part[-1]
    return f"{masked_local}@{domain_part}"


def cleanup_login_otp_store():
    """Remove expired OTP challenges from the in-memory store."""
    now = datetime.utcnow()
    expired_keys = [
        token for token, challenge in LOGIN_OTP_STORE.items()
        if challenge.get('expires_at') <= now
    ]
    for token in expired_keys:
        LOGIN_OTP_STORE.pop(token, None)


def get_login_challenge():
    """Read the active OTP challenge for the current browser session."""
    cleanup_login_otp_store()
    token = session.get('login_challenge_id')
    if not token:
        return None

    challenge = LOGIN_OTP_STORE.get(token)
    if not challenge:
        session.pop('login_challenge_id', None)
        return None
    return challenge


def clear_login_challenge():
    """Remove OTP challenge state from store and browser session."""
    token = session.pop('login_challenge_id', None)
    if token:
        LOGIN_OTP_STORE.pop(token, None)


def get_smtp_settings():
    """Resolve SMTP settings with Gmail-friendly defaults and aliases."""
    username = os.getenv('SMTP_USERNAME') or os.getenv('GMAIL_SENDER_EMAIL', '')
    password = os.getenv('SMTP_PASSWORD') or os.getenv('GMAIL_APP_PASSWORD', '')
    host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
    port = int(os.getenv('SMTP_PORT', '587'))
    from_email = os.getenv('SMTP_FROM_EMAIL') or username
    from_name = os.getenv('SMTP_FROM_NAME', SITE_CONTACT['company_name'])
    use_ssl = os.getenv('SMTP_USE_SSL', 'false').strip().lower() == 'true'

    return {
        'host': host,
        'port': port,
        'username': username,
        'password': password,
        'from_email': from_email,
        'from_name': from_name,
        'use_ssl': use_ssl
    }


def is_smtp_configured():
    """SMTP delivery is available only when all required credentials exist."""
    settings = get_smtp_settings()
    required = [
        settings['host'],
        settings['port'],
        settings['username'],
        settings['password'],
        settings['from_email']
    ]
    return all(required)


def send_login_code_email(email_value, code_value, display_name='', purpose_label='verifikasi akun'):
    """Send a six-digit email code. Falls back to preview mode in development."""
    if not is_smtp_configured():
        return {'mode': 'preview', 'preview_code': code_value}

    smtp_settings = get_smtp_settings()
    smtp_host = smtp_settings['host']
    smtp_port = smtp_settings['port']
    smtp_username = smtp_settings['username']
    smtp_password = smtp_settings['password']
    smtp_from_email = smtp_settings['from_email']
    smtp_from_name = smtp_settings['from_name']
    use_ssl = smtp_settings['use_ssl']

    greeting_name = display_name or email_value.split('@')[0].title()
    message = EmailMessage()
    message['Subject'] = f'Kode {purpose_label.title()} EL Travel: {code_value}'
    message['From'] = f'{smtp_from_name} <{smtp_from_email}>'
    message['To'] = email_value
    message.set_content(
        f"""Halo {greeting_name},

Kode {purpose_label} EL Travel Anda adalah: {code_value}

Kode ini berlaku selama {LOGIN_OTP_TTL_MINUTES} menit dan hanya bisa dipakai untuk satu sesi verifikasi.
Jika Anda tidak merasa meminta kode ini, abaikan email ini.

Salam,
EL Travel
"""
    )

    if use_ssl:
        with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=15) as server:
            server.login(smtp_username, smtp_password)
            server.send_message(message)
    else:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(message)

    return {'mode': 'smtp', 'preview_code': ''}


def start_email_otp_login(email_value, display_name, next_url):
    """Create or refresh an OTP challenge and deliver the code."""
    clear_login_challenge()
    code_value = generate_login_code()
    delivery_result = send_login_code_email(email_value, code_value, display_name)
    token = secrets.token_urlsafe(24)
    LOGIN_OTP_STORE[token] = {
        'email': email_value,
        'display_name': display_name,
        'code': code_value,
        'expires_at': datetime.utcnow() + timedelta(minutes=LOGIN_OTP_TTL_MINUTES),
        'attempts': 0,
        'next_url': next_url,
        'delivery_mode': delivery_result['mode'],
        'preview_code': delivery_result.get('preview_code', ''),
        'last_sent_at': datetime.utcnow()
    }
    session['login_challenge_id'] = token
    session['login_next'] = next_url
    return LOGIN_OTP_STORE[token]


def get_current_user():
    """Return the logged-in user stored in session."""
    return session.get('user')


def get_current_user_email():
    """Normalized email for ownership checks."""
    user = get_current_user() or {}
    return (user.get('email') or '').strip().lower()


def get_current_staff():
    """Return the currently logged-in staff member from session if still valid."""
    staff_session = session.get('staff_user') or {}
    staff_email = (staff_session.get('email') or '').strip().lower()
    if not staff_email:
        return None

    account = fetch_staff_by_email(staff_email)
    if not account or not safe_int(account.get('is_active'), 0):
        session.pop('staff_user', None)
        return None

    normalized_staff = build_session_staff_from_account(account)
    if normalized_staff != staff_session:
        session['staff_user'] = normalized_staff
    return normalized_staff


def get_current_staff_id():
    """Numeric staff id for owner/backoffice actions."""
    staff = get_current_staff() or {}
    return safe_int(staff.get('id'))


def get_current_staff_role():
    """Current staff role from session."""
    staff = get_current_staff() or {}
    return (staff.get('role') or '').strip().lower()


def is_google_auth_configured():
    """Google OAuth can run when both client id and secret are provided."""
    return bool(os.getenv('GOOGLE_CLIENT_ID') and os.getenv('GOOGLE_CLIENT_SECRET'))


def allow_local_google_fallback():
    """Allow local Gmail login only when OAuth credentials are not configured."""
    return not is_google_auth_configured()


def redirect_to_login(message='Silakan login terlebih dahulu untuk melanjutkan.', next_url=None):
    """Store next target and send user to the login page."""
    target = normalize_next_url(next_url or request.full_path or request.path)
    session['login_next'] = target
    flash(message, 'info')
    return redirect(url_for('login', next=target))


def login_required_route(message='Silakan login terlebih dahulu untuk melanjutkan.'):
    """Decorator for routes that require a logged-in user."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            if not get_current_user():
                return redirect_to_login(message=message)
            return view_func(*args, **kwargs)
        return wrapped
    return decorator


def user_owns_booking(email_value):
    """Check whether the logged-in user owns the booking email."""
    return bool(get_current_user_email() and get_current_user_email() == (email_value or '').strip().lower())


def get_booking_status_info(order_row):
    """Map booking/payment data into a single ticket-status presentation model."""
    if order_row.get('status') == 'cancelled':
        status_key = 'cancelled'
    elif order_row.get('status') == 'completed':
        status_key = 'completed'
    elif order_row.get('status_pembayaran') == 'menunggu_verifikasi':
        status_key = 'verifying'
    elif order_row.get('status_pembayaran') == 'berhasil' or order_row.get('status') == 'confirmed':
        status_key = 'confirmed'
    else:
        status_key = 'payment_pending'

    return {
        'key': status_key,
        **ORDER_STATUS_META[status_key]
    }


def get_destination_story_meta(wisata_item):
    """Return editorial copy and best-moment metadata for destination detail pages."""
    wisata_item = apply_destination_media(wisata_item)
    destination_name = wisata_item.get('nama')
    category = (wisata_item.get('kategori') or 'wisata').lower()
    base_description = (wisata_item.get('deskripsi') or '').strip()
    country_label = get_country_name(wisata_item)
    moment_meta = DESTINATION_MOMENT_META.get(destination_name, {})
    media_meta = get_destination_media(destination_name)

    if not moment_meta:
        fallback_title = {
            'bahari': 'Cahaya terbaik saat lanskap air dan langit bertemu dengan lebih tenang',
            'petualangan': 'Jam terbaik ketika lanskap terasa paling dramatis dan lebih bersih',
            'budaya': 'Waktu ketika suasana destinasi terasa paling hidup dan paling berkarakter',
            'alam': 'Momen ketika bentang alam membuka detail paling indahnya'
        }.get(category, 'Waktu terbaik ketika destinasi ini terasa paling berkesan')
        moment_meta = {
            'moment_title': fallback_title,
            'best_time': (wisata_item.get('best_time') or '').strip() or 'Pagi hari atau menjelang sunset, tergantung musim terbaik setempat',
            'moment_image': wisata_item.get('moment_foto') or wisata_item.get('foto') or 'https://images.unsplash.com/photo-1537996194471-e657df975ab4?w=1400&q=80',
            'moment_copy': f"{destination_name} terasa paling menarik ketika ritme tempat ini melambat sedikit dan detail lanskapnya mulai terlihat lebih jelas. Pada momen seperti ini, pengalaman berkunjung terasa lebih imersif dan lebih mudah diingat."
        }

    if (wisata_item.get('best_time') or '').strip():
        moment_meta['best_time'] = wisata_item.get('best_time').strip()

    if (wisata_item.get('moment_foto') or '').strip():
        moment_meta['moment_image'] = wisata_item.get('moment_foto').strip()
    elif media_meta.get('moment_image'):
        moment_meta['moment_image'] = media_meta['moment_image']
    elif media_meta.get('image'):
        moment_meta['moment_image'] = media_meta['image']

    intro_paragraph_one = (
        f"{destination_name} berada di {wisata_item.get('lokasi')} dan menjadi salah satu destinasi "
        f"yang paling menarik untuk kategori {wisata_item.get('kategori') or 'wisata'} di {country_label}. "
        f"{base_description if base_description else 'Karakter tempat ini kuat karena pemandangannya, atmosfer lokasinya, dan pengalaman yang terasa berbeda begitu Anda benar-benar berada di sana.'}"
    )

    intro_paragraph_two = (
        f"Untuk traveler yang tidak hanya mencari foto, {destination_name} punya kekuatan pada suasananya. "
        f"Anda tidak datang hanya untuk melihat satu titik, tetapi untuk merasakan alur perjalanan, perubahan cahaya, "
        f"dan detail kecil yang membuat destinasi ini terasa pantas diperjuangkan."
    )

    audience_copy = {
        'bahari': 'Cocok untuk traveler yang ingin suasana lebih tenang, island hopping, dan visual laut yang kuat.',
        'petualangan': 'Cocok untuk traveler yang suka ritme aktif, eksplorasi, dan pengalaman yang terasa menantang.',
        'budaya': 'Cocok untuk traveler yang ingin memahami tempat lewat cerita, arsitektur, dan kebiasaan lokal.',
        'alam': 'Cocok untuk traveler yang mencari lanskap besar, udara terbuka, dan suasana yang lebih hening.'
    }.get(category, 'Cocok untuk traveler yang ingin pengalaman yang terasa lebih hidup daripada sekadar singgah singkat.')

    return {
        'headline': f"Kenapa {destination_name} layak dijelajahi lebih dalam",
        'paragraphs': [intro_paragraph_one, intro_paragraph_two],
        'moment_title': moment_meta['moment_title'],
        'moment_copy': moment_meta['moment_copy'],
        'moment_image': moment_meta['moment_image'],
        'best_time': moment_meta['best_time'],
        'highlights': [
            {
                'title': 'Karakter Pengalaman',
                'text': f"Destinasi ini menonjol karena perpaduan antara {wisata_item.get('kategori') or 'pengalaman wisata'} dan suasana lokasi yang tidak terasa generik."
            },
            {
                'title': 'Waktu Paling Menarik',
                'text': f"{moment_meta['best_time']}. Di waktu ini, pencahayaan, cuaca, dan ritme tempat biasanya terasa paling mendukung."
            },
            {
                'title': 'Cocok Untuk',
                'text': audience_copy
            }
        ]
    }


def build_region_cards(destinations):
    """Create region cards with live counts from current destination data."""
    grouped_destinations = {region['slug']: [] for region in NAV_DESTINATION_REGIONS}

    for item in destinations:
        slug = get_region_slug(item.get('negara') or item.get('lokasi'), item.get('tipe'))
        grouped_destinations.setdefault(slug, []).append(item)

    cards = []
    for region in NAV_DESTINATION_REGIONS:
        items = grouped_destinations.get(region['slug'], [])
        if not items:
            continue

        config = REGION_CONFIG[region['slug']]
        cards.append({
            'slug': region['slug'],
            'label': config['label'],
            'image': config['image'],
            'summary': config['summary'],
            'accent': config['accent'],
            'count': len(items),
            'sample_names': ', '.join(item['nama'] for item in items[:3])
        })

    return cards


def build_featured_trips(destinations):
    """Transform destination rows into more editorial trip cards for the homepage."""
    destination_by_name = {item['nama']: item for item in destinations}
    selected = []

    for name in FEATURED_DESTINATION_ORDER:
        if name in destination_by_name:
            selected.append(destination_by_name[name])

    if len(selected) < 6:
        for item in destinations:
            if item not in selected:
                selected.append(item)
            if len(selected) >= 6:
                break

    featured = []
    for item in selected[:6]:
        region_slug = get_region_slug(item.get('negara') or item.get('lokasi'), item.get('tipe'))
        meta = FEATURED_TRIP_META.get(item['nama'], {})
        start_price = safe_int(item.get('min_harga')) or meta.get('price') or get_default_price(region_slug, item.get('tipe'))
        compare_price = meta.get('compare_price') or (start_price + 1200000)

        featured.append({
            **item,
            'country': get_country_name(item),
            'region_slug': region_slug,
            'region_label': REGION_CONFIG[region_slug]['label'],
            'trip_title': meta.get('title') or f"{item['nama']} Signature Journey",
            'duration_code': meta.get('duration_code') or get_default_duration_code(region_slug, item.get('tipe')),
            'duration_text': item.get('paket_durasi') or meta.get('duration_text') or get_default_duration_text(region_slug, item.get('tipe')),
            'departure_items': meta.get('departure_items') or ['Jadwal berangkat fleksibel', 'Konsultasi itinerary tersedia'],
            'start_price': start_price,
            'compare_price': compare_price,
            'package_total': max(safe_int(item.get('paket_count'), 0), 1),
            'type_label': 'Lokal' if (item.get('tipe') or '').lower() == 'lokal' else 'Internasional'
        })

    return featured


def build_package_catalog(destinations, package_type_slug):
    """Create package cards per package type using destination and base package data."""
    package_type = PACKAGE_TYPE_CONFIG.get(package_type_slug, PACKAGE_TYPE_CONFIG['solo'])
    catalog_items = []

    for item in destinations:
        region_slug = get_region_slug(item.get('negara') or item.get('lokasi'), item.get('tipe'))
        meta = FEATURED_TRIP_META.get(item['nama'], {})
        promo_adjusted_base_price = safe_int(item.get('display_discounted_price'))
        source_base_price = safe_int(item.get('display_original_price'))
        base_price = promo_adjusted_base_price or safe_int(item.get('min_harga')) or meta.get('price') or get_default_price(region_slug, item.get('tipe'))
        original_reference_price = source_base_price or safe_int(item.get('min_harga')) or base_price
        start_price = int(round(base_price * package_type['multiplier']))
        compare_price = int(round(start_price * 1.12))
        original_start_price = int(round(original_reference_price * package_type['multiplier']))
        if original_start_price > start_price:
            compare_price = max(compare_price, original_start_price)

        if package_type_slug == 'solo':
            price_caption = 'Harga per traveler'
        elif package_type_slug == 'pasangan':
            price_caption = 'Harga untuk 2 traveler'
        elif package_type_slug == 'keluarga':
            price_caption = 'Harga estimasi 3-4 traveler'
        else:
            price_caption = 'Harga mulai 5 traveler'

        catalog_items.append({
            **item,
            'country': get_country_name(item),
            'region_slug': region_slug,
            'region_label': REGION_CONFIG[region_slug]['label'],
            'package_variant': package_type['label'],
            'package_variant_accent': package_type['accent'],
            'trip_title': f"{package_type['label']} {item['nama']}",
            'duration_code': meta.get('duration_code') or get_default_duration_code(region_slug, item.get('tipe')),
            'duration_text': item.get('paket_durasi') or meta.get('duration_text') or get_default_duration_text(region_slug, item.get('tipe')),
            'departure_items': meta.get('departure_items') or ['Jadwal fleksibel sesuai musim terbaik', 'Admin membantu penyesuaian itinerary'],
            'start_price': start_price,
            'compare_price': compare_price,
            'original_start_price': original_start_price,
            'price_caption': price_caption,
            'traveler_text': package_type['traveler_text'],
            'package_summary': package_type['summary'],
            'detail_url': url_for('detail_wisata', id=item['id']),
            'booking_url': url_for('detail_wisata', id=item['id']),
            'has_active_promo': bool(item.get('has_active_promo')),
            'promo_badge': item.get('promo_badge', ''),
            'promo_title': item.get('promo_title', ''),
            'promo_caption': item.get('promo_caption', '')
        })

    return catalog_items


def normalize_discount_type(value):
    """Keep discount types inside the allowed promo modes."""
    value = (value or '').strip().lower()
    return value if value in {'percent', 'amount'} else 'percent'


def parse_backoffice_datetime(value):
    """Parse datetime-local values coming from backoffice forms."""
    raw_value = (value or '').strip()
    if not raw_value:
        return None
    for pattern in ('%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M'):
        try:
            return datetime.strptime(raw_value, pattern)
        except ValueError:
            continue
    return None


def get_promo_status_key(promo_row, now_value=None):
    """Map promo schedule into active / upcoming / expired / inactive status."""
    if not promo_row:
        return 'inactive'

    now_value = now_value or datetime.now()
    starts_at = promo_row.get('starts_at')
    ends_at = promo_row.get('ends_at')
    is_active = bool(safe_int(promo_row.get('is_active'), 0))

    if not is_active:
        return 'inactive'
    if starts_at and now_value < starts_at:
        return 'upcoming'
    if ends_at and now_value > ends_at:
        return 'expired'
    return 'active'


def format_promo_badge(promo_row):
    """Build a short badge label for cards and finance rows."""
    if not promo_row:
        return ''

    discount_type = normalize_discount_type(promo_row.get('discount_type'))
    discount_value = safe_int(promo_row.get('discount_value'))
    if discount_type == 'percent':
        return f"{discount_value}% OFF"
    return f"Diskon {format_idr(discount_value)}"


def calculate_discounted_price(base_price, promo_row=None):
    """Apply active promo math to a base price and return a normalized summary."""
    original_price = max(0, safe_int(base_price))
    if not promo_row:
        return {
            'original_price': original_price,
            'final_price': original_price,
            'discount_amount': 0,
            'has_discount': False
        }

    discount_type = normalize_discount_type(promo_row.get('discount_type'))
    discount_value = safe_int(promo_row.get('discount_value'))

    if discount_type == 'percent':
        discount_amount = int(round(original_price * (discount_value / 100)))
    else:
        discount_amount = discount_value

    discount_amount = max(0, min(original_price, discount_amount))
    final_price = original_price - discount_amount
    if original_price > 0 and final_price < 1:
        final_price = 1
        discount_amount = max(0, original_price - final_price)

    return {
        'original_price': original_price,
        'final_price': final_price,
        'discount_amount': discount_amount,
        'has_discount': discount_amount > 0
    }


def fetch_promos_for_wisata_ids(cursor, wisata_ids):
    """Load every promo row for a list of destination ids."""
    unique_ids = [safe_int(item) for item in wisata_ids if safe_int(item) > 0]
    if not unique_ids or not table_exists(cursor, 'promo_destinasi'):
        return {}

    placeholders = ', '.join(['%s'] * len(unique_ids))
    cursor.execute(f"""
        SELECT
            pr.*,
            s.nama_lengkap AS created_by_name
        FROM promo_destinasi pr
        LEFT JOIN akun_staff s ON s.id = pr.created_by_staff_id
        WHERE pr.wisata_id IN ({placeholders})
        ORDER BY pr.wisata_id ASC, pr.created_at DESC, pr.id DESC
    """, tuple(unique_ids))

    promo_map = {}
    for row in cursor.fetchall():
        row['discount_type'] = normalize_discount_type(row.get('discount_type'))
        row['discount_value'] = safe_int(row.get('discount_value'))
        row['status_key'] = get_promo_status_key(row)
        row['status_meta'] = PROMO_STATUS_META[row['status_key']]
        row['badge_text'] = format_promo_badge(row)
        promo_map.setdefault(safe_int(row.get('wisata_id')), []).append(row)
    return promo_map


def pick_current_active_promo(promo_rows):
    """Return the promo row that is currently active and most relevant."""
    if not promo_rows:
        return None

    for row in promo_rows:
        if get_promo_status_key(row) == 'active':
            return row
    return None


def attach_promo_metadata_to_destinations(cursor, destination_rows):
    """Attach active promo and display prices to destination-like rows."""
    rows = destination_rows or []
    promo_map = fetch_promos_for_wisata_ids(cursor, [row.get('id') for row in rows])

    for row in rows:
        promo_rows = promo_map.get(safe_int(row.get('id')), [])
        active_promo = pick_current_active_promo(promo_rows)
        base_price = (
            safe_int(row.get('min_harga'))
            or safe_int(row.get('min_price'))
            or safe_int(row.get('harga'))
        )
        pricing = calculate_discounted_price(base_price, active_promo)
        row['promo_rows'] = promo_rows
        row['active_promo'] = active_promo
        row['has_active_promo'] = bool(active_promo and pricing['has_discount'])
        row['promo_badge'] = active_promo.get('badge_text') if active_promo else ''
        row['promo_status_key'] = get_promo_status_key(active_promo) if active_promo else ''
        row['display_original_price'] = pricing['original_price']
        row['display_discounted_price'] = pricing['final_price']
        row['promo_discount_amount'] = pricing['discount_amount']
        row['promo_title'] = (active_promo or {}).get('promo_name', '')
        row['promo_caption'] = (active_promo or {}).get('description', '')
        if active_promo:
            row['promo_period_text'] = (
                f"{active_promo['starts_at'].strftime('%d %b %Y')} - {active_promo['ends_at'].strftime('%d %b %Y')}"
                if active_promo.get('starts_at') and active_promo.get('ends_at')
                else 'Promo aktif'
            )
        else:
            row['promo_period_text'] = ''

    return rows


def apply_promo_to_package_row(package_row, active_promo=None):
    """Attach promo-aware pricing to a package row."""
    pricing = calculate_discounted_price(package_row.get('harga'), active_promo)
    package_row['active_promo'] = active_promo
    package_row['has_active_promo'] = bool(active_promo and pricing['has_discount'])
    package_row['display_original_price'] = pricing['original_price']
    package_row['display_discounted_price'] = pricing['final_price']
    package_row['promo_discount_amount'] = pricing['discount_amount']
    package_row['promo_badge'] = active_promo.get('badge_text') if active_promo else ''
    package_row['promo_title'] = (active_promo or {}).get('promo_name', '')
    return package_row


@app.template_filter('idr')
def idr_filter(value):
    return format_idr(value)


@app.context_processor
def inject_navigation_regions():
    return {
        'nav_destination_regions': NAV_DESTINATION_REGIONS,
        'nav_package_types': NAV_PACKAGE_TYPES,
        'current_user': get_current_user(),
        'current_staff': get_current_staff(),
        'google_auth_configured': is_google_auth_configured(),
        'local_google_fallback': allow_local_google_fallback(),
        'site_contact': SITE_CONTACT,
        'contact_page': CONTACT_PAGE_CONTENT,
        'site_social': SITE_SOCIAL,
        'company_profile': COMPANY_PROFILE,
        'whatsapp_link': build_whatsapp_link
    }

# ════════════════════════════════════════
# DATABASE CONNECTION
# ════════════════════════════════════════

def create_db_connection():
    """Create database connection using local or deployed environment variables."""
    db_host = env_value('DB_HOST', 'TIDB_HOST', default='localhost')
    db_port_raw = env_value('DB_PORT', 'TIDB_PORT', default='3306')
    db_user = env_value('DB_USER', 'TIDB_USER', default='root')
    db_password = env_value('DB_PASSWORD', 'TIDB_PASSWORD', default='')
    db_name = env_value('DB_NAME', 'TIDB_DATABASE', default='pariwisataDb')
    db_config = {
        'host': db_host,
        'port': safe_int(db_port_raw, 3306),
        'user': db_user,
        'password': db_password,
        'database': db_name
    }

    ssl_mode = env_value('DB_SSL_MODE', 'TIDB_SSL_MODE', default='').strip().lower()
    default_tls_enabled = is_tidb_cloud_host(db_host)
    ssl_enabled = env_flag(
        'DB_SSL_ENABLED',
        env_flag('TIDB_SSL_ENABLED', default_tls_enabled or ssl_mode not in {'', 'disable', 'disabled', 'false', 'off'})
    )
    ssl_ca_path = resolve_db_ssl_ca_path()

    if ssl_enabled:
        db_config['ssl_disabled'] = False
        if ssl_ca_path:
            db_config['ssl_ca'] = ssl_ca_path
        db_config['ssl_verify_cert'] = env_flag(
            'DB_SSL_VERIFY_CERT',
            env_flag('TIDB_SSL_VERIFY_CERT', default=bool(ssl_ca_path) or default_tls_enabled)
        )
        db_config['ssl_verify_identity'] = env_flag(
            'DB_SSL_VERIFY_IDENTITY',
            env_flag('TIDB_SSL_VERIFY_IDENTITY', default=default_tls_enabled)
        )
    elif ssl_mode in {'disable', 'disabled', 'false', 'off'}:
        db_config['ssl_disabled'] = True

    return mysql.connector.connect(**db_config)


def column_exists(cursor, table_name, column_name):
    """Check whether a database column exists."""
    cursor.execute(f"SHOW COLUMNS FROM `{table_name}` LIKE %s", (column_name,))
    return cursor.fetchone() is not None


def table_exists(cursor, table_name):
    """Check whether a table exists in the current database."""
    cursor.execute("SHOW TABLES LIKE %s", (table_name,))
    return cursor.fetchone() is not None


def build_booking_code(booking_id):
    """Create a readable booking code for owner and customer references."""
    return f"ELT-{safe_int(booking_id):06d}"


def append_order_status_log(cursor, pemesanan_id, status_label, message, actor_type='system', actor_name='System'):
    """Store a lightweight operational log entry when the log table is available."""
    if not table_exists(cursor, 'pemesanan_status_log'):
        return

    cursor.execute("""
        INSERT INTO pemesanan_status_log (
            pemesanan_id, actor_type, actor_name, status_label, message, created_at
        ) VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        pemesanan_id,
        actor_type,
        actor_name[:120],
        status_label[:120],
        message[:600],
        datetime.now()
    ))


def append_payment_audit_log(cursor, pembayaran_id, pemesanan_id, event_label, message, actor_type='system', actor_name='System'):
    """Store finance-side payment audit history when the table is available."""
    if not pembayaran_id or not table_exists(cursor, 'payment_audit_log'):
        return

    cursor.execute("""
        INSERT INTO payment_audit_log (
            pembayaran_id, pemesanan_id, actor_type, actor_name, event_label, message, created_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (
        pembayaran_id,
        pemesanan_id,
        actor_type,
        actor_name[:120],
        event_label[:160],
        message[:700],
        datetime.now()
    ))


def ensure_operational_order_record(cursor, pemesanan_id):
    """Create or refresh the owner-side operational row for a booking."""
    if not table_exists(cursor, 'operasional_pesanan'):
        return

    booking_code = build_booking_code(pemesanan_id)
    cursor.execute("SELECT id FROM operasional_pesanan WHERE pemesanan_id = %s LIMIT 1", (pemesanan_id,))
    existing_row = cursor.fetchone()
    if existing_row:
        cursor.execute("""
            UPDATE operasional_pesanan
            SET kode_booking = %s,
                updated_at = %s
            WHERE pemesanan_id = %s
        """, (booking_code, datetime.now(), pemesanan_id))
        return

    cursor.execute("""
        INSERT INTO operasional_pesanan (
            pemesanan_id, kode_booking, status_operasional, status_tiket,
            status_voucher, status_dokumen, created_at, updated_at
        ) VALUES (%s, %s, 'baru', 'belum_dibuat', 'belum_dibuat', 'belum_lengkap', %s, %s)
    """, (pemesanan_id, booking_code, datetime.now(), datetime.now()))


def sync_operational_status(cursor, pemesanan_id, order_status='', payment_status=''):
    """Sync the owner-side operational status with booking and payment progress."""
    if not table_exists(cursor, 'operasional_pesanan'):
        return

    operational_status = 'menunggu_pembayaran'
    ticket_status = 'belum_dibuat'

    if order_status == 'cancelled':
        operational_status = 'dibatalkan'
    elif order_status == 'completed':
        operational_status = 'selesai'
        ticket_status = 'terbit'
    elif payment_status == 'menunggu_verifikasi':
        operational_status = 'verifikasi_pembayaran'
    elif payment_status == 'berhasil' or order_status == 'confirmed':
        operational_status = 'siapkan_tiket'
        ticket_status = 'diproses'
    elif order_status == 'pending':
        operational_status = 'menunggu_pembayaran'

    ensure_operational_order_record(cursor, pemesanan_id)
    cursor.execute("""
        UPDATE operasional_pesanan
        SET status_operasional = %s,
            status_tiket = %s,
            updated_at = %s
        WHERE pemesanan_id = %s
    """, (operational_status, ticket_status, datetime.now(), pemesanan_id))


def ensure_database_schema():
    """Create and patch tables required by the latest auth and payment flow."""
    db = create_db_connection()
    cur = db.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS akun_user (
            id INT PRIMARY KEY AUTO_INCREMENT,
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
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS akun_staff (
            id INT PRIMARY KEY AUTO_INCREMENT,
            nama_lengkap VARCHAR(120) NOT NULL,
            email VARCHAR(190) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            role ENUM('owner', 'finance', 'operasional', 'customer_service') DEFAULT 'operasional',
            is_active TINYINT(1) DEFAULT 1,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            last_login_at DATETIME NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    if table_exists(cur, 'pemesanan'):
        cur.execute("""
            CREATE TABLE IF NOT EXISTS operasional_pesanan (
                id INT PRIMARY KEY AUTO_INCREMENT,
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
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS pemesanan_status_log (
                id INT PRIMARY KEY AUTO_INCREMENT,
                pemesanan_id INT NOT NULL,
                actor_type ENUM('system', 'customer', 'staff') DEFAULT 'system',
                actor_name VARCHAR(120),
                status_label VARCHAR(120) NOT NULL,
                message VARCHAR(600),
                created_at DATETIME NOT NULL,
                FOREIGN KEY (pemesanan_id) REFERENCES pemesanan(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS detail_peserta_pesanan (
                id INT PRIMARY KEY AUTO_INCREMENT,
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
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

    if table_exists(cur, 'pembayaran') and table_exists(cur, 'pemesanan'):
        cur.execute("""
            CREATE TABLE IF NOT EXISTS payment_audit_log (
                id INT PRIMARY KEY AUTO_INCREMENT,
                pembayaran_id INT NOT NULL,
                pemesanan_id INT NOT NULL,
                actor_type ENUM('system', 'customer', 'staff') DEFAULT 'system',
                actor_name VARCHAR(120),
                event_label VARCHAR(160) NOT NULL,
                message VARCHAR(700),
                created_at DATETIME NOT NULL,
                FOREIGN KEY (pembayaran_id) REFERENCES pembayaran(id) ON DELETE CASCADE,
                FOREIGN KEY (pemesanan_id) REFERENCES pemesanan(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

    destination_column_statements = {
        'negara': "ALTER TABLE destinasi ADD COLUMN negara VARCHAR(120) NULL AFTER lokasi",
        'benua': "ALTER TABLE destinasi ADD COLUMN benua VARCHAR(60) NULL AFTER negara",
        'thumbnail_foto': "ALTER TABLE destinasi ADD COLUMN thumbnail_foto VARCHAR(600) NULL AFTER foto",
        'moment_foto': "ALTER TABLE destinasi ADD COLUMN moment_foto VARCHAR(600) NULL AFTER thumbnail_foto",
        'foto_source_url': "ALTER TABLE destinasi ADD COLUMN foto_source_url VARCHAR(1000) NULL AFTER moment_foto",
        'foto_source_label': "ALTER TABLE destinasi ADD COLUMN foto_source_label VARCHAR(255) NULL AFTER foto_source_url",
        'best_time': "ALTER TABLE destinasi ADD COLUMN best_time VARCHAR(255) NULL AFTER foto_source_label",
        'display_order': "ALTER TABLE destinasi ADD COLUMN display_order INT NULL AFTER total_review",
        'is_active': "ALTER TABLE destinasi ADD COLUMN is_active TINYINT(1) DEFAULT 1 AFTER display_order"
    }
    if table_exists(cur, 'destinasi'):
        for column_name, alter_sql in destination_column_statements.items():
            if not column_exists(cur, 'destinasi', column_name):
                cur.execute(alter_sql)

    wisata_column_statements = {
        'negara': "ALTER TABLE wisata ADD COLUMN negara VARCHAR(120) NULL AFTER lokasi",
        'benua': "ALTER TABLE wisata ADD COLUMN benua VARCHAR(60) NULL AFTER negara",
        'thumbnail_foto': "ALTER TABLE wisata ADD COLUMN thumbnail_foto VARCHAR(600) NULL AFTER foto",
        'moment_foto': "ALTER TABLE wisata ADD COLUMN moment_foto VARCHAR(600) NULL AFTER thumbnail_foto",
        'foto_source_url': "ALTER TABLE wisata ADD COLUMN foto_source_url VARCHAR(1000) NULL AFTER moment_foto",
        'foto_source_label': "ALTER TABLE wisata ADD COLUMN foto_source_label VARCHAR(255) NULL AFTER foto_source_url",
        'best_time': "ALTER TABLE wisata ADD COLUMN best_time VARCHAR(255) NULL AFTER foto_source_label",
        'display_order': "ALTER TABLE wisata ADD COLUMN display_order INT NULL AFTER rating",
        'is_active': "ALTER TABLE wisata ADD COLUMN is_active TINYINT(1) DEFAULT 1 AFTER display_order"
    }
    if table_exists(cur, 'wisata'):
        for column_name, alter_sql in wisata_column_statements.items():
            if not column_exists(cur, 'wisata', column_name):
                cur.execute(alter_sql)

    package_column_statements = {
        'kode_paket': "ALTER TABLE tipe_paket ADD COLUMN kode_paket VARCHAR(80) NULL AFTER wisata_id",
        'jenis_paket': "ALTER TABLE tipe_paket ADD COLUMN jenis_paket VARCHAR(40) DEFAULT 'custom' AFTER nama_paket",
        'status_paket': "ALTER TABLE tipe_paket ADD COLUMN status_paket VARCHAR(30) DEFAULT 'aktif' AFTER max_orang",
        'meeting_point': "ALTER TABLE tipe_paket ADD COLUMN meeting_point VARCHAR(255) NULL AFTER status_paket",
        'keberangkatan_info': "ALTER TABLE tipe_paket ADD COLUMN keberangkatan_info TEXT NULL AFTER meeting_point",
        'kuota_total': "ALTER TABLE tipe_paket ADD COLUMN kuota_total INT DEFAULT 20 AFTER keberangkatan_info",
        'kuota_tersedia': "ALTER TABLE tipe_paket ADD COLUMN kuota_tersedia INT DEFAULT 20 AFTER kuota_total",
        'is_featured': "ALTER TABLE tipe_paket ADD COLUMN is_featured TINYINT(1) DEFAULT 0 AFTER kuota_tersedia"
    }
    if table_exists(cur, 'tipe_paket'):
        for column_name, alter_sql in package_column_statements.items():
            if not column_exists(cur, 'tipe_paket', column_name):
                cur.execute(alter_sql)

    order_column_statements = {
        'kode_pemesanan': "ALTER TABLE pemesanan ADD COLUMN kode_pemesanan VARCHAR(30) NULL AFTER id",
        'sumber_pesanan': "ALTER TABLE pemesanan ADD COLUMN sumber_pesanan VARCHAR(40) DEFAULT 'website' AFTER catatan",
        'harga_awal': "ALTER TABLE pemesanan ADD COLUMN harga_awal INT DEFAULT 0 AFTER total_harga",
        'total_diskon': "ALTER TABLE pemesanan ADD COLUMN total_diskon INT DEFAULT 0 AFTER harga_awal",
        'promo_id': "ALTER TABLE pemesanan ADD COLUMN promo_id INT NULL AFTER total_diskon",
        'promo_snapshot_title': "ALTER TABLE pemesanan ADD COLUMN promo_snapshot_title VARCHAR(180) NULL AFTER promo_id",
        'promo_snapshot_value': "ALTER TABLE pemesanan ADD COLUMN promo_snapshot_value VARCHAR(80) NULL AFTER promo_snapshot_title"
    }
    if table_exists(cur, 'pemesanan'):
        for column_name, alter_sql in order_column_statements.items():
            if not column_exists(cur, 'pemesanan', column_name):
                cur.execute(alter_sql)

    payment_column_statements = {
        'gateway_provider': "ALTER TABLE pembayaran ADD COLUMN gateway_provider VARCHAR(40) NULL AFTER bukti_pembayaran",
        'gateway_order_id': "ALTER TABLE pembayaran ADD COLUMN gateway_order_id VARCHAR(120) NULL AFTER gateway_provider",
        'gateway_transaction_id': "ALTER TABLE pembayaran ADD COLUMN gateway_transaction_id VARCHAR(120) NULL AFTER gateway_order_id",
        'gateway_status': "ALTER TABLE pembayaran ADD COLUMN gateway_status VARCHAR(40) NULL AFTER gateway_transaction_id",
        'snap_token': "ALTER TABLE pembayaran ADD COLUMN snap_token VARCHAR(255) NULL AFTER gateway_status",
        'redirect_url': "ALTER TABLE pembayaran ADD COLUMN redirect_url VARCHAR(600) NULL AFTER snap_token",
        'channel_code': "ALTER TABLE pembayaran ADD COLUMN channel_code VARCHAR(80) NULL AFTER redirect_url",
        'payment_reference': "ALTER TABLE pembayaran ADD COLUMN payment_reference VARCHAR(120) NULL AFTER channel_code",
        'paid_at': "ALTER TABLE pembayaran ADD COLUMN paid_at DATETIME NULL AFTER payment_reference",
        'verified_by_staff_id': "ALTER TABLE pembayaran ADD COLUMN verified_by_staff_id INT NULL AFTER paid_at",
        'verified_at': "ALTER TABLE pembayaran ADD COLUMN verified_at DATETIME NULL AFTER verified_by_staff_id",
        'verification_note': "ALTER TABLE pembayaran ADD COLUMN verification_note TEXT NULL AFTER verified_at",
        'raw_response_json': "ALTER TABLE pembayaran ADD COLUMN raw_response_json LONGTEXT NULL AFTER verification_note"
    }
    if table_exists(cur, 'pembayaran'):
        cur.execute("""
            ALTER TABLE pembayaran
            MODIFY COLUMN metode_pembayaran VARCHAR(40) DEFAULT 'bank_transfer'
        """)
        for column_name, alter_sql in payment_column_statements.items():
            if not column_exists(cur, 'pembayaran', column_name):
                cur.execute(alter_sql)

    payment_detail_column_statements = {
        'detail_key': "ALTER TABLE payment_detail ADD COLUMN detail_key VARCHAR(50) NULL AFTER pembayaran_id",
        'detail_value': "ALTER TABLE payment_detail ADD COLUMN detail_value VARCHAR(255) NULL AFTER detail_key"
    }
    if table_exists(cur, 'payment_detail'):
        for column_name, alter_sql in payment_detail_column_statements.items():
            if not column_exists(cur, 'payment_detail', column_name):
                cur.execute(alter_sql)

    if table_exists(cur, 'wisata'):
        cur.execute("""
            CREATE TABLE IF NOT EXISTS promo_destinasi (
                id INT PRIMARY KEY AUTO_INCREMENT,
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
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

    if table_exists(cur, 'wisata') and table_exists(cur, 'tipe_paket'):
        cur.execute("SELECT id FROM wisata WHERE nama = %s LIMIT 1", ('Labuan Bajo',))
        wisata_row = cur.fetchone()
    else:
        wisata_row = None

    if wisata_row:
        cur.execute("SELECT id FROM tipe_paket WHERE nama_paket = %s LIMIT 1", (TEST_PAYMENT_PACKAGE['package_name'],))
        if not cur.fetchone():
            cur.execute("""
                INSERT INTO tipe_paket (
                    wisata_id, kode_paket, nama_paket, jenis_paket, deskripsi, harga, durasi, fasilitas,
                    min_orang, max_orang, status_paket, meeting_point, keberangkatan_info,
                    kuota_total, kuota_tersedia, is_featured
                ) VALUES (%s, %s, %s, 'custom', %s, %s, %s, %s, %s, %s, 'aktif', %s, %s, %s, %s, 0)
            """, (
                wisata_row[0],
                'TEST-RP1-VERIFY',
                TEST_PAYMENT_PACKAGE['package_name'],
                TEST_PAYMENT_PACKAGE['description'],
                TEST_PAYMENT_PACKAGE['price'],
                TEST_PAYMENT_PACKAGE['duration'],
                TEST_PAYMENT_PACKAGE['facilities'],
                TEST_PAYMENT_PACKAGE['min_people'],
                TEST_PAYMENT_PACKAGE['max_people'],
                'Online / koordinasi admin',
                'Dipakai untuk uji alur pembayaran sebelum go-live.',
                TEST_PAYMENT_PACKAGE['max_people'],
                TEST_PAYMENT_PACKAGE['max_people']
            ))

    if table_exists(cur, 'pemesanan'):
        cur.execute("""
            UPDATE pemesanan
            SET kode_pemesanan = CONCAT('ELT-', LPAD(id, 6, '0'))
            WHERE kode_pemesanan IS NULL OR kode_pemesanan = ''
        """)

        if table_exists(cur, 'operasional_pesanan'):
            cur.execute("""
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
                WHERE op.pemesanan_id IS NULL
            """)

    db.commit()
    cur.close()
    db.close()


def get_db():
    """Create database connection to pariwisataDb."""
    return create_db_connection()


def fetch_account_by_email(email_value):
    """Load a user account by email."""
    if not email_value:
        return None
    db = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute("SELECT * FROM akun_user WHERE LOWER(email) = %s LIMIT 1", ((email_value or '').strip().lower(),))
    account = cur.fetchone()
    cur.close()
    db.close()
    return account


def fetch_staff_by_email(email_value):
    """Load a staff account by email."""
    if not email_value:
        return None
    db = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute("SELECT * FROM akun_staff WHERE LOWER(email) = %s LIMIT 1", ((email_value or '').strip().lower(),))
    account = cur.fetchone()
    cur.close()
    db.close()
    return account


def get_staff_count():
    """Return how many staff accounts currently exist."""
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT COUNT(*) FROM akun_staff")
    total = safe_int(cur.fetchone()[0])
    cur.close()
    db.close()
    return total


def backoffice_has_staff():
    """Check whether at least one staff account already exists."""
    return get_staff_count() > 0


def build_session_user_from_account(account_row):
    """Convert an account row into the session structure used by the app."""
    return {
        'id': account_row['id'],
        'name': account_row['nama_lengkap'],
        'email': account_row['email'],
        'picture': '',
        'provider': 'local-account',
        'gender': account_row.get('jenis_kelamin', '')
    }


def build_session_staff_from_account(account_row):
    """Convert a staff row into the session structure used by backoffice."""
    return {
        'id': account_row['id'],
        'name': account_row['nama_lengkap'],
        'email': account_row['email'],
        'role': account_row.get('role', 'operasional'),
        'role_label': STAFF_ROLE_LABELS.get(account_row.get('role', 'operasional'), 'Staff')
    }


def remember_logged_in_account(account_row):
    """Persist the current account into Flask session."""
    session['user'] = build_session_user_from_account(account_row)


def remember_logged_in_staff(account_row):
    """Persist the current staff account into Flask session."""
    session['staff_user'] = build_session_staff_from_account(account_row)


def clear_pending_registration():
    """Drop temporary registration state from the browser session."""
    session.pop('pending_registration_email', None)


def get_pending_registration_account():
    """Read pending registration account from the current session."""
    pending_email = session.get('pending_registration_email', '').strip().lower()
    if not pending_email:
        return None
    return fetch_account_by_email(pending_email)


def issue_account_verification(email_value):
    """Generate and send a verification code for account activation."""
    account = fetch_account_by_email(email_value)
    if not account:
        raise ValueError('Akun yang akan diverifikasi tidak ditemukan.')

    code_value = generate_login_code()
    delivery_result = send_login_code_email(
        account['email'],
        code_value,
        account.get('nama_lengkap', ''),
        purpose_label='verifikasi akun'
    )

    db = get_db()
    cur = db.cursor()
    cur.execute("""
        UPDATE akun_user
        SET verification_code_hash = %s,
            verification_expires_at = %s,
            verification_attempts = 0,
            updated_at = %s
        WHERE id = %s
    """, (
        hash_verification_code(code_value),
        datetime.now() + timedelta(minutes=LOGIN_OTP_TTL_MINUTES),
        datetime.now(),
        account['id']
    ))
    db.commit()
    cur.close()
    db.close()

    session['pending_registration_email'] = account['email']
    return {
        'email': account['email'],
        'delivery_mode': delivery_result['mode'],
        'preview_code': delivery_result.get('preview_code', '')
    }


def verify_account_registration(email_value, code_input):
    """Verify a pending account against the six-digit email code."""
    account = fetch_account_by_email(email_value)
    if not account:
        return None, 'Akun yang sedang diverifikasi tidak ditemukan.'
    if account.get('email_verified'):
        return account, ''

    expires_at = account.get('verification_expires_at')
    if not expires_at or expires_at < datetime.now():
        return None, 'Kode verifikasi sudah habis. Silakan minta kode baru.'
    if account.get('verification_attempts', 0) >= LOGIN_OTP_MAX_ATTEMPTS:
        return None, 'Percobaan verifikasi sudah terlalu banyak. Silakan minta kode baru.'

    expected_hash = account.get('verification_code_hash') or ''
    submitted_hash = hash_verification_code(code_input)
    if not expected_hash or not secrets.compare_digest(expected_hash, submitted_hash):
        db = get_db()
        cur = db.cursor()
        cur.execute("""
            UPDATE akun_user
            SET verification_attempts = verification_attempts + 1,
                updated_at = %s
            WHERE id = %s
        """, (datetime.now(), account['id']))
        db.commit()
        cur.close()
        db.close()
        return None, 'Kode verifikasi belum cocok. Periksa lagi 6 digit yang masuk ke email Anda.'

    db = get_db()
    cur = db.cursor()
    cur.execute("""
        UPDATE akun_user
        SET email_verified = 1,
            verification_code_hash = NULL,
            verification_expires_at = NULL,
            verification_attempts = 0,
            updated_at = %s,
            last_login_at = %s
        WHERE id = %s
    """, (datetime.now(), datetime.now(), account['id']))
    db.commit()
    cur.close()
    db.close()

    clear_pending_registration()
    return fetch_account_by_email(email_value), ''


def update_account_last_login(account_id):
    """Store the latest login timestamp for account audit trails."""
    db = get_db()
    cur = db.cursor()
    cur.execute("UPDATE akun_user SET last_login_at = %s, updated_at = %s WHERE id = %s", (
        datetime.now(),
        datetime.now(),
        account_id
    ))
    db.commit()
    cur.close()
    db.close()


def update_staff_last_login(staff_id):
    """Store the latest login timestamp for staff/backoffice audit trails."""
    db = get_db()
    cur = db.cursor()
    cur.execute("UPDATE akun_staff SET last_login_at = %s, updated_at = %s WHERE id = %s", (
        datetime.now(),
        datetime.now(),
        staff_id
    ))
    db.commit()
    cur.close()
    db.close()


def clear_staff_session():
    """Drop the current backoffice session safely."""
    session.pop('staff_user', None)
    session.pop('backoffice_next', None)


def normalize_backoffice_next_url(next_url):
    """Keep redirects inside the backoffice namespace."""
    if not next_url:
        return url_for('backoffice_dashboard')
    if not next_url.startswith('/backoffice'):
        return url_for('backoffice_dashboard')
    return normalize_next_url(next_url)


def redirect_to_backoffice_login(message='Silakan login sebagai staff untuk membuka dashboard.', next_url=None):
    """Store the target route and redirect to staff login."""
    target = normalize_backoffice_next_url(next_url or request.full_path or request.path)
    session['backoffice_next'] = target
    flash(message, 'info')
    return redirect(url_for('backoffice_login', next=target))


def backoffice_login_required(view_func):
    """Require a logged-in staff session for backoffice routes."""
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not get_current_staff():
            return redirect_to_backoffice_login()
        return view_func(*args, **kwargs)
    return wrapped


def backoffice_role_required(*allowed_roles):
    """Restrict selected backoffice modules to specific staff roles."""
    allowed = {role.strip().lower() for role in allowed_roles if role}

    def decorator(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            if not get_current_staff():
                return redirect_to_backoffice_login()
            if allowed and get_current_staff_role() not in allowed:
                flash('Akses modul ini dibatasi untuk role staff tertentu.', 'error')
                return redirect(url_for('backoffice_dashboard'))
            return view_func(*args, **kwargs)
        return wrapped

    return decorator


def replace_payment_details(cursor, pembayaran_id, detail_map):
    """Replace flexible key-value details stored for a payment record."""
    cursor.execute("DELETE FROM payment_detail WHERE pembayaran_id = %s", (pembayaran_id,))
    for key, value in detail_map.items():
        text_value = (str(value) if value is not None else '').strip()
        if not text_value:
            continue
        cursor.execute("""
            INSERT INTO payment_detail (pembayaran_id, detail_key, detail_value)
            VALUES (%s, %s, %s)
        """, (pembayaran_id, key[:50], text_value[:255]))


def payment_details_rows_to_map(payment_rows):
    """Convert key-value detail rows into a template-friendly dictionary."""
    detail_map = {}
    for row in payment_rows or []:
        detail_map[row['detail_key']] = row['detail_value']
    return detail_map


def fetch_payment_audit_rows(cursor, pembayaran_id, limit=25):
    """Load recent payment audit entries when the ledger table is available."""
    if not pembayaran_id or not table_exists(cursor, 'payment_audit_log'):
        return []

    cursor.execute("""
        SELECT *
        FROM payment_audit_log
        WHERE pembayaran_id = %s
        ORDER BY created_at DESC, id DESC
        LIMIT %s
    """, (pembayaran_id, safe_int(limit, 25)))
    return cursor.fetchall()


def extract_midtrans_detail_map(response_payload):
    """Flatten important Midtrans response fields for templates and status pages."""
    detail_map = {
        'payment_type': response_payload.get('payment_type', ''),
        'transaction_status': response_payload.get('transaction_status', ''),
        'transaction_id': response_payload.get('transaction_id', ''),
        'expiry_time': response_payload.get('expiry_time', ''),
        'currency': response_payload.get('currency', 'IDR')
    }

    for index, va_item in enumerate(response_payload.get('va_numbers', []) or [], start=1):
        bank_name = (va_item.get('bank') or f'bank_{index}').strip().lower().replace(' ', '_')
        detail_map[f'va_{bank_name}'] = va_item.get('va_number', '')

    if response_payload.get('permata_va_number'):
        detail_map['va_permata'] = response_payload['permata_va_number']
    if response_payload.get('bill_key'):
        detail_map['bill_key'] = response_payload['bill_key']
    if response_payload.get('biller_code'):
        detail_map['biller_code'] = response_payload['biller_code']

    for action in response_payload.get('actions', []) or []:
        action_name = (action.get('name') or '').strip().lower().replace('-', '_')
        action_url = action.get('url', '')
        if action_name and action_url:
            detail_map[f'action_{action_name}'] = action_url

    return detail_map


def map_midtrans_transaction_status(transaction_status, fraud_status=''):
    """Translate Midtrans transaction states into local payment and booking statuses."""
    normalized_status = (transaction_status or '').strip().lower()
    normalized_fraud = (fraud_status or '').strip().lower()

    if normalized_status in ['capture', 'settlement'] and normalized_fraud not in ['deny', 'challenge']:
        return 'berhasil', 'confirmed'
    if normalized_status in ['deny', 'cancel', 'expire', 'failure']:
        return 'gagal', 'pending'
    return 'pending', 'pending'


def verify_midtrans_signature(payload):
    """Verify Midtrans webhook authenticity using the official SHA512 formula."""
    server_key = os.getenv('MIDTRANS_SERVER_KEY', '').strip()
    if not server_key:
        return False
    raw_order_id = str(payload.get('order_id', ''))
    raw_status_code = str(payload.get('status_code', ''))
    raw_gross_amount = str(payload.get('gross_amount', ''))
    expected_signature = hashlib.sha512(f"{raw_order_id}{raw_status_code}{raw_gross_amount}{server_key}".encode('utf-8')).hexdigest()
    return secrets.compare_digest(expected_signature, str(payload.get('signature_key', '')))


def midtrans_api_request(path, payload=None, method='POST'):
    """Send authenticated request to Midtrans without extra dependencies."""
    if not midtrans_is_configured():
        raise ValueError('Midtrans belum dikonfigurasi.')

    server_key = os.getenv('MIDTRANS_SERVER_KEY', '').strip()
    auth_value = base64.b64encode(f"{server_key}:".encode('utf-8')).decode('utf-8')
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': f'Basic {auth_value}'
    }
    body = json.dumps(payload).encode('utf-8') if payload is not None else None
    request_object = Request(
        f"{midtrans_base_url()}{path}",
        data=body,
        headers=headers,
        method=method
    )
    try:
        with urlopen(request_object, timeout=20) as response:
            return json.loads(response.read().decode('utf-8'))
    except HTTPError as error:
        error_body = error.read().decode('utf-8') if error.fp else ''
        try:
            parsed_error = json.loads(error_body)
            message = parsed_error.get('status_message') or parsed_error.get('error_messages') or error_body
        except json.JSONDecodeError:
            message = error_body or str(error)
        raise ValueError(f"Midtrans error {error.code}: {message}") from error
    except URLError as error:
        raise ValueError(f'Koneksi ke Midtrans gagal: {error.reason}') from error


def build_midtrans_order_id(pemesanan_id):
    """Build a unique Midtrans order id."""
    return f"ELT-{pemesanan_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}-{secrets.randbelow(9000) + 1000}"


def create_midtrans_transaction_for_booking(pemesanan, metode_pembayaran):
    """Create a Midtrans Snap transaction for a booking."""
    payment_method = PAYMENT_METHOD_CONFIG.get(metode_pembayaran)
    if not payment_method:
        raise ValueError('Metode pembayaran tidak valid.')

    order_id = build_midtrans_order_id(pemesanan['id'])
    gross_amount = safe_int(pemesanan.get('total_harga'))
    item_name = f"{pemesanan.get('wisata_nama', 'Destinasi')} - {pemesanan.get('nama_paket', 'Paket Wisata')}"
    customer_name = (pemesanan.get('nama_pemesan') or 'EL Travel Guest').strip()
    first_name, _, last_name = customer_name.partition(' ')

    payload = {
        'transaction_details': {
            'order_id': order_id,
            'gross_amount': gross_amount
        },
        'enabled_payments': payment_method['enabled_payments'],
        'item_details': [
            {
                'id': f"PKT-{pemesanan['paket_id']}",
                'price': gross_amount,
                'quantity': 1,
                'name': item_name[:50],
                'category': 'Travel Package',
                'merchant_name': FINANCE_ACCOUNT_CONFIG['merchant_short_name']
            }
        ],
        'customer_details': {
            'first_name': first_name or customer_name,
            'last_name': last_name,
            'email': pemesanan.get('email', ''),
            'phone': pemesanan.get('telepon', '')
        },
        'callbacks': {
            'finish': url_for('konfirmasi_pembayaran', pemesanan_id=pemesanan['id'], _external=True)
        }
    }
    response_payload = midtrans_api_request('/snap/v1/transactions', payload=payload, method='POST')
    response_payload['gateway_order_id'] = order_id
    return response_payload


def sync_midtrans_payment_payload(payload):
    """Persist Midtrans transaction updates into local payment and booking records."""
    order_id = payload.get('order_id', '')
    if not order_id:
        return None

    db = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute("""
        SELECT pb.id, pb.pemesanan_id
        FROM pembayaran pb
        WHERE pb.gateway_order_id = %s
        LIMIT 1
    """, (order_id,))
    payment_row = cur.fetchone()

    if not payment_row:
        cur.close()
        db.close()
        return None

    local_status, booking_status = map_midtrans_transaction_status(
        payload.get('transaction_status'),
        payload.get('fraud_status', '')
    )
    paid_at = payload.get('settlement_time') or payload.get('transaction_time') or None
    detail_map = extract_midtrans_detail_map(payload)

    cur.execute("""
        UPDATE pembayaran
        SET metode_pembayaran = %s,
            status_pembayaran = %s,
            tanggal_pembayaran = %s,
            jumlah_dibayar = %s,
            gateway_provider = 'midtrans',
            gateway_transaction_id = %s,
            gateway_status = %s,
            channel_code = %s,
            payment_reference = %s,
            paid_at = %s,
            raw_response_json = %s
        WHERE id = %s
    """, (
        'qris' if payload.get('payment_type') == 'qris' else 'bank_transfer',
        local_status,
        paid_at,
        safe_int(payload.get('gross_amount'), 0),
        payload.get('transaction_id', ''),
        payload.get('transaction_status', ''),
        payload.get('payment_type', ''),
        detail_map.get('va_bni') or detail_map.get('va_bri') or detail_map.get('va_permata') or detail_map.get('bill_key') or '',
        paid_at,
        json.dumps(payload),
        payment_row['id']
    ))

    if local_status == 'berhasil':
        cur.execute("UPDATE pemesanan SET status = %s WHERE id = %s", ('confirmed', payment_row['pemesanan_id']))
    elif local_status == 'gagal':
        cur.execute("UPDATE pemesanan SET status = %s WHERE id = %s", ('pending', payment_row['pemesanan_id']))
    else:
        cur.execute("UPDATE pemesanan SET status = %s WHERE id = %s", (booking_status, payment_row['pemesanan_id']))

    replace_payment_details(cur, payment_row['id'], detail_map)
    append_payment_audit_log(
        cur,
        payment_row['id'],
        payment_row['pemesanan_id'],
        f"Status gateway {local_status}",
        f"Midtrans memperbarui transaksi ke status {payload.get('transaction_status', 'pending')} dengan channel {payload.get('payment_type', 'gateway')}.",
        actor_type='system',
        actor_name='Midtrans Sync'
    )
    ensure_operational_order_record(cur, payment_row['pemesanan_id'])
    sync_operational_status(cur, payment_row['pemesanan_id'], order_status='confirmed' if local_status == 'berhasil' else booking_status, payment_status=local_status)
    append_order_status_log(
        cur,
        payment_row['pemesanan_id'],
        f"Pembayaran {local_status.replace('_', ' ')}",
        f"Status transaksi diperbarui dari jalur Midtrans dengan metode {payload.get('payment_type', 'gateway')}.",
        actor_type='system',
        actor_name='Midtrans Sync'
    )
    db.commit()
    cur.close()
    db.close()
    return payment_row['pemesanan_id']


def sync_midtrans_payment_for_booking(pemesanan_id):
    """Fetch the latest payment status from Midtrans for a booking."""
    if not midtrans_is_configured():
        return
    db = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute("""
        SELECT gateway_order_id
        FROM pembayaran
        WHERE pemesanan_id = %s AND gateway_provider = 'midtrans' AND gateway_order_id IS NOT NULL
        LIMIT 1
    """, (pemesanan_id,))
    payment_row = cur.fetchone()
    cur.close()
    db.close()
    if not payment_row:
        return
    status_payload = midtrans_api_request(f"/v2/{payment_row['gateway_order_id']}/status", payload=None, method='GET')
    sync_midtrans_payment_payload(status_payload)


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page with local account sign-in and account registration."""
    if get_current_user():
        next_url = normalize_next_url(request.args.get('next') or session.get('login_next') or url_for('status_pesanan'))
        session.pop('login_next', None)
        return redirect(next_url)

    next_url = normalize_next_url(request.args.get('next') or session.get('login_next') or url_for('status_pesanan'))
    session['login_next'] = next_url
    otp_preview_code = ''
    pending_registration = get_pending_registration_account()
    show_register_panel = request.args.get('show_register') == '1'
    show_register_prompt = False
    query_register_email = request.args.get('register_email', '').strip().lower()
    suggested_registration_email = query_register_email if is_gmail_address(query_register_email) else ''

    if pending_registration and pending_registration.get('email_verified'):
        clear_pending_registration()
        pending_registration = None

    if request.method == 'POST':
        action = request.form.get('action', 'existing_login')

        if action == 'existing_login':
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')
            captcha_answer = request.form.get('login_captcha_answer', '')
            honeypot = request.form.get('company_website', '')

            if not is_gmail_address(email):
                flash('Masukkan alamat Gmail yang valid untuk login ke akun Anda.', 'error')
            elif not password:
                flash('Password akun masih kosong.', 'error')
            elif not validate_human_challenge('login', captcha_answer, honeypot):
                flash('Verifikasi manusia belum cocok. Coba hitung ulang captcha-nya.', 'error')
            else:
                account = fetch_account_by_email(email)
                if not account:
                    flash('Akun belum ditemukan. Silakan buat akun baru terlebih dahulu.', 'error')
                    show_register_prompt = True
                    suggested_registration_email = email
                elif not account.get('email_verified'):
                    try:
                        delivery = issue_account_verification(email)
                        otp_preview_code = delivery.get('preview_code', '')
                        pending_registration = get_pending_registration_account()
                        flash('Akun ini belum aktif. Kami kirim ulang kode verifikasi 6 digit ke Gmail Anda.', 'info')
                    except Exception as error:
                        print(f"Resend registration code error: {error}")
                        flash('Kode verifikasi akun belum berhasil dikirim ulang.', 'error')
                elif not check_password_hash(account['password_hash'], password):
                    flash('Email atau password belum cocok.', 'error')
                else:
                    remember_logged_in_account(account)
                    update_account_last_login(account['id'])
                    session.pop('login_next', None)
                    flash('Login berhasil. Anda sekarang bisa melanjutkan pemesanan.', 'success')
                    return redirect(next_url)

        elif action == 'start_register':
            show_register_panel = True
            full_name = request.form.get('nama_lengkap', '').strip()
            email = request.form.get('register_email', '').strip().lower()
            password = request.form.get('register_password', '')
            confirm_password = request.form.get('confirm_password', '')
            gender = normalize_gender(request.form.get('jenis_kelamin', ''))
            phone = sanitize_phone_number(request.form.get('telepon', ''))
            birth_date = request.form.get('tanggal_lahir', '').strip() or None
            city = request.form.get('kota_domisili', '').strip()
            captcha_answer = request.form.get('register_captcha_answer', '')
            honeypot = request.form.get('register_website', '')

            if not full_name:
                flash('Nama lengkap wajib diisi untuk membuat akun baru.', 'error')
            elif not is_gmail_address(email):
                flash('Akun baru saat ini menggunakan alamat Gmail sebagai identitas login.', 'error')
            elif len(password) < PASSWORD_MIN_LENGTH:
                flash('Password minimal 8 karakter agar akun lebih aman.', 'error')
            elif password != confirm_password:
                flash('Konfirmasi password belum cocok.', 'error')
            elif not validate_human_challenge('register', captcha_answer, honeypot):
                flash('Verifikasi manusia pada formulir daftar belum cocok.', 'error')
            else:
                existing_account = fetch_account_by_email(email)
                if existing_account and existing_account.get('email_verified'):
                    flash('Email ini sudah terdaftar. Silakan gunakan formulir login akun yang sudah ada.', 'error')
                else:
                    db = get_db()
                    cur = db.cursor()
                    password_hash = generate_password_hash(password)
                    timestamp_now = datetime.now()

                    if existing_account:
                        cur.execute("""
                            UPDATE akun_user
                            SET nama_lengkap = %s,
                                jenis_kelamin = %s,
                                telepon = %s,
                                tanggal_lahir = %s,
                                kota_domisili = %s,
                                password_hash = %s,
                                email_verified = 0,
                                updated_at = %s
                            WHERE id = %s
                        """, (
                            full_name,
                            gender,
                            phone,
                            birth_date,
                            city[:120],
                            password_hash,
                            timestamp_now,
                            existing_account['id']
                        ))
                    else:
                        cur.execute("""
                            INSERT INTO akun_user (
                                email, nama_lengkap, jenis_kelamin, telepon, tanggal_lahir,
                                kota_domisili, password_hash, email_verified, created_at, updated_at
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, 0, %s, %s)
                        """, (
                            email,
                            full_name,
                            gender,
                            phone,
                            birth_date,
                            city[:120],
                            password_hash,
                            timestamp_now,
                            timestamp_now
                        ))

                    db.commit()
                    cur.close()
                    db.close()

                    try:
                        delivery = issue_account_verification(email)
                        otp_preview_code = delivery.get('preview_code', '')
                        pending_registration = get_pending_registration_account()
                        if delivery['delivery_mode'] == 'smtp':
                            flash('Akun hampir siap. Kode verifikasi 6 digit sudah dikirim ke Gmail Anda.', 'success')
                        else:
                            flash('Mode development aktif. Kode verifikasi akun ditampilkan di halaman ini untuk testing lokal.', 'info')
                    except Exception as error:
                        print(f"Registration verification send error: {error}")
                        flash('Akun tersimpan, tetapi kode verifikasi belum berhasil dikirim. Coba kirim ulang.', 'error')

        elif action == 'verify_registration':
            pending_email = session.get('pending_registration_email', '').strip().lower()
            code_input = ''.join(ch for ch in request.form.get('verification_code', '') if ch.isdigit())

            if not pending_email:
                flash('Sesi pembuatan akun sudah habis. Isi formulir pendaftaran lagi ya.', 'error')
            elif len(code_input) != 6:
                flash('Masukkan 6 digit kode verifikasi akun yang dikirim ke Gmail Anda.', 'error')
            else:
                account, error_message = verify_account_registration(pending_email, code_input)
                if error_message:
                    flash(error_message, 'error')
                elif account:
                    remember_logged_in_account(account)
                    session.pop('login_next', None)
                    flash('Akun berhasil dibuat dan langsung aktif dipakai untuk booking.', 'success')
                    return redirect(next_url)

        elif action == 'resend_registration_code':
            pending_registration = get_pending_registration_account()
            if not pending_registration:
                flash('Tidak ada akun yang sedang menunggu verifikasi.', 'error')
            else:
                try:
                    delivery = issue_account_verification(pending_registration['email'])
                    otp_preview_code = delivery.get('preview_code', '')
                    pending_registration = get_pending_registration_account()
                    flash('Kode verifikasi baru sudah kami kirim ke Gmail Anda.', 'success')
                except Exception as error:
                    print(f"Resend code error: {error}")
                    flash('Kode verifikasi belum berhasil dikirim ulang.', 'error')

        elif action == 'cancel_registration':
            clear_pending_registration()
            flash('Sesi pembuatan akun dibatalkan. Anda bisa mulai lagi kapan saja.', 'info')
            return redirect(url_for('login', next=next_url))

    pending_registration = get_pending_registration_account()
    return render_template(
        'login.html',
        next_url=next_url,
        pending_registration=pending_registration,
        show_register_prompt=show_register_prompt,
        show_register_panel=show_register_panel,
        suggested_registration_email=suggested_registration_email,
        masked_pending_email=mask_email(pending_registration['email']) if pending_registration else '',
        otp_preview_code=otp_preview_code,
        smtp_configured=is_smtp_configured(),
        login_captcha_question=get_human_challenge('login'),
        register_captcha_question=get_human_challenge('register'),
        gender_options=GENDER_OPTIONS
    )


@app.route('/login/google')
def login_google():
    """Redirect to Google OAuth consent screen."""
    next_url = normalize_next_url(request.args.get('next') or session.get('login_next') or url_for('status_pesanan'))
    session['login_next'] = next_url

    if not is_google_auth_configured():
        flash('Google OAuth belum dikonfigurasi. Gunakan mode lokal sementara atau isi GOOGLE_CLIENT_ID dan GOOGLE_CLIENT_SECRET.', 'info')
        return redirect(url_for('login', next=next_url))

    state = secrets.token_urlsafe(24)
    session['oauth_state'] = state

    params = {
        'client_id': os.getenv('GOOGLE_CLIENT_ID'),
        'redirect_uri': url_for('auth_google_callback', _external=True),
        'response_type': 'code',
        'scope': GOOGLE_SCOPE,
        'state': state,
        'access_type': 'offline',
        'include_granted_scopes': 'true'
    }
    return redirect(f"{GOOGLE_AUTH_URL}?{urlencode(params)}")


@app.route('/auth/google/callback')
def auth_google_callback():
    """Handle Google OAuth callback."""
    if request.args.get('error'):
        flash('Login Google dibatalkan atau gagal disetujui.', 'error')
        return redirect(url_for('login'))

    if not is_google_auth_configured():
        flash('Google OAuth belum dikonfigurasi.', 'error')
        return redirect(url_for('login'))

    if request.args.get('state') != session.get('oauth_state'):
        flash('Sesi login tidak valid. Silakan coba lagi.', 'error')
        return redirect(url_for('login'))

    code = request.args.get('code')
    if not code:
        flash('Kode otorisasi Google tidak ditemukan.', 'error')
        return redirect(url_for('login'))

    token_payload = {
        'code': code,
        'client_id': os.getenv('GOOGLE_CLIENT_ID'),
        'client_secret': os.getenv('GOOGLE_CLIENT_SECRET'),
        'redirect_uri': url_for('auth_google_callback', _external=True),
        'grant_type': 'authorization_code'
    }

    try:
        token_request = Request(
            GOOGLE_TOKEN_URL,
            data=urlencode(token_payload).encode('utf-8'),
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        with urlopen(token_request, timeout=10) as response:
            token_response = json.loads(response.read().decode('utf-8'))

        access_token = token_response.get('access_token')
        if not access_token:
            raise ValueError('Access token tidak tersedia dari Google.')

        user_request = Request(
            GOOGLE_USERINFO_URL,
            headers={'Authorization': f'Bearer {access_token}'}
        )
        with urlopen(user_request, timeout=10) as response:
            user_info = json.loads(response.read().decode('utf-8'))

        if not user_info.get('email'):
            raise ValueError('Email akun Google tidak tersedia.')
        if user_info.get('email_verified') is False:
            raise ValueError('Email Google belum terverifikasi.')

        session['user'] = {
            'name': user_info.get('name') or user_info['email'].split('@')[0].title(),
            'email': user_info['email'],
            'picture': user_info.get('picture', ''),
            'provider': 'google'
        }
        session.pop('oauth_state', None)
        next_url = normalize_next_url(session.pop('login_next', url_for('status_pesanan')))
        flash('Login Google berhasil.', 'success')
        return redirect(next_url)
    except (HTTPError, URLError, ValueError, json.JSONDecodeError) as error:
        print(f"Google auth error: {error}")
        flash('Login Google belum berhasil diproses. Silakan coba lagi.', 'error')
        return redirect(url_for('login'))


@app.route('/logout')
def logout():
    """Clear current session."""
    session.pop('user', None)
    session.pop('oauth_state', None)
    session.pop('login_next', None)
    flash('Anda sudah logout dari sesi ini.', 'success')
    return redirect(url_for('index'))


BACKOFFICE_OPERATIONAL_META = {
    'baru': {'label': 'Baru Masuk', 'tone': 'warning'},
    'menunggu_pembayaran': {'label': 'Menunggu Pembayaran', 'tone': 'muted'},
    'verifikasi_pembayaran': {'label': 'Verifikasi Pembayaran', 'tone': 'info'},
    'siapkan_tiket': {'label': 'Siapkan Tiket', 'tone': 'primary'},
    'siapkan_voucher': {'label': 'Siapkan Voucher', 'tone': 'primary'},
    'siap_berangkat': {'label': 'Siap Berangkat', 'tone': 'success'},
    'selesai': {'label': 'Selesai', 'tone': 'success'},
    'dibatalkan': {'label': 'Dibatalkan', 'tone': 'danger'}
}

BACKOFFICE_PAYMENT_META = {
    'pending': {'label': 'Belum Bayar', 'tone': 'muted'},
    'menunggu_verifikasi': {'label': 'Perlu Dicek', 'tone': 'info'},
    'berhasil': {'label': 'Lunas', 'tone': 'success'},
    'gagal': {'label': 'Gagal', 'tone': 'danger'}
}

BACKOFFICE_TICKET_META = {
    'belum_dibuat': {'label': 'Belum Dibuat', 'tone': 'muted'},
    'diproses': {'label': 'Sedang Diproses', 'tone': 'primary'},
    'terbit': {'label': 'Sudah Terbit', 'tone': 'success'}
}

BACKOFFICE_VOUCHER_META = {
    'belum_dibuat': {'label': 'Belum Dibuat', 'tone': 'muted'},
    'diproses': {'label': 'Sedang Diproses', 'tone': 'primary'},
    'terkirim': {'label': 'Sudah Terkirim', 'tone': 'success'}
}

BACKOFFICE_DOCUMENT_META = {
    'belum_lengkap': {'label': 'Belum Lengkap', 'tone': 'warning'},
    'menunggu_user': {'label': 'Menunggu User', 'tone': 'info'},
    'lengkap': {'label': 'Lengkap', 'tone': 'success'}
}


def get_backoffice_meta(meta_map, status_value, default_label='Belum Diatur'):
    """Return template metadata for a backoffice status enum."""
    meta = meta_map.get((status_value or '').strip().lower())
    if meta:
        return meta
    return {'label': default_label, 'tone': 'muted'}


def get_gateway_provider_label(gateway_provider):
    """Return a friendlier label for payment source/provider names."""
    normalized_value = (gateway_provider or '').strip().lower()
    provider_map = {
        'manual': 'Manual Transfer',
        'midtrans': 'Midtrans Gateway',
        'demo_qris': 'Demo QRIS Akademik'
    }
    if normalized_value in provider_map:
        return provider_map[normalized_value]
    if not normalized_value:
        return 'Manual / belum ada'
    return normalized_value.replace('_', ' ').title()


def build_backoffice_payment_detail_display(order_row, payment_detail_rows):
    """Curate payment detail rows so backoffice sees readable payment metadata."""
    detail_map = payment_details_rows_to_map(payment_detail_rows)
    if not detail_map:
        return []

    if (order_row or {}).get('gateway_provider') == 'demo_qris':
        display_rows = []
        demo_pairs = [
            ('Mode Presentasi', detail_map.get('demo_label') or PAYMENT_DEMO_CONFIG.get('label', 'Demo Akademik Hybrid')),
            ('Referensi Demo', detail_map.get('demo_reference') or (order_row or {}).get('payment_reference') or ''),
            ('Berlaku Sampai', detail_map.get('demo_expires_label') or detail_map.get('demo_expires_at') or ''),
            ('Instruksi Demo', detail_map.get('demo_instruction') or PAYMENT_DEMO_CONFIG.get('confirm_note', '')),
            ('Waktu Simulasi Berhasil', detail_map.get('demo_paid_label') or detail_map.get('demo_paid_at') or ''),
            ('ID Simulasi', detail_map.get('demo_transaction_id') or (order_row or {}).get('gateway_transaction_id') or '')
        ]
        for label, value in demo_pairs:
            clean_value = (str(value) if value is not None else '').strip()
            if clean_value:
                display_rows.append({'label': label, 'value': clean_value})
        return display_rows

    display_rows = []
    ignored_keys = {'destination_json', 'manual_qris_image'}
    for detail_row in payment_detail_rows or []:
        key_name = (detail_row.get('detail_key') or '').strip()
        if not key_name or key_name in ignored_keys:
            continue
        display_rows.append({
            'label': key_name.replace('_', ' ').title(),
            'value': detail_row.get('detail_value', '')
        })
    return display_rows


def prepare_backoffice_order_row(order_row):
    """Normalize a backoffice order row for templates."""
    item = apply_destination_media(order_row or {})
    if not item:
        return item

    item['operational_meta'] = get_backoffice_meta(
        BACKOFFICE_OPERATIONAL_META,
        item.get('status_operasional'),
        default_label='Belum Diproses'
    )
    item['payment_meta'] = get_backoffice_meta(
        BACKOFFICE_PAYMENT_META,
        item.get('status_pembayaran'),
        default_label='Belum Ada Pembayaran'
    )
    item['ticket_meta'] = get_backoffice_meta(
        BACKOFFICE_TICKET_META,
        item.get('status_tiket'),
        default_label='Belum Dibuat'
    )
    item['voucher_meta'] = get_backoffice_meta(
        BACKOFFICE_VOUCHER_META,
        item.get('status_voucher'),
        default_label='Belum Dibuat'
    )
    item['document_meta'] = get_backoffice_meta(
        BACKOFFICE_DOCUMENT_META,
        item.get('status_dokumen'),
        default_label='Belum Lengkap'
    )
    item['booking_code_display'] = item.get('kode_pemesanan') or build_booking_code(item.get('id'))
    item['traveler_summary'] = f"{safe_int(item.get('jumlah_orang'), 1)} pax"
    item['country_label'] = get_country_name(item)
    item['customer_initial'] = (item.get('nama_pemesan') or '?')[:1].upper()
    item['gateway_provider_label'] = get_gateway_provider_label(item.get('gateway_provider'))
    item['payment_method_label'] = PAYMENT_METHOD_CONFIG.get(item.get('metode_pembayaran'), {}).get(
        'label',
        (item.get('metode_pembayaran') or 'Belum ada').replace('_', ' ').title()
    )
    item['is_demo_payment'] = (item.get('gateway_provider') or '').strip().lower() == 'demo_qris'
    return item


def fetch_backoffice_staff_members():
    """Load active staff options for assignment dropdowns."""
    db = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute("""
        SELECT id, nama_lengkap, email, role
        FROM akun_staff
        WHERE is_active = 1
        ORDER BY FIELD(role, 'owner', 'finance', 'operasional', 'customer_service'), nama_lengkap ASC
    """)
    staff_rows = cur.fetchall()
    cur.close()
    db.close()

    for row in staff_rows:
        row['role_label'] = STAFF_ROLE_LABELS.get(row.get('role'), 'Staff')
    return staff_rows


def fetch_backoffice_staff_directory():
    """Load full staff roster with light operational metrics for owner management."""
    db = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute("""
        SELECT
            s.id,
            s.nama_lengkap,
            s.email,
            s.role,
            s.is_active,
            s.created_at,
            s.updated_at,
            s.last_login_at,
            COUNT(DISTINCT op.id) AS assigned_order_total,
            COUNT(DISTINCT CASE WHEN pb.verified_by_staff_id = s.id THEN pb.id END) AS verified_payment_total
        FROM akun_staff s
        LEFT JOIN operasional_pesanan op ON op.assigned_staff_id = s.id
        LEFT JOIN pembayaran pb ON pb.verified_by_staff_id = s.id
        GROUP BY
            s.id,
            s.nama_lengkap,
            s.email,
            s.role,
            s.is_active,
            s.created_at,
            s.updated_at,
            s.last_login_at
        ORDER BY FIELD(s.role, 'owner', 'finance', 'operasional', 'customer_service'), s.nama_lengkap ASC
    """)
    rows = cur.fetchall()
    cur.close()
    db.close()

    for row in rows:
        row['role_label'] = STAFF_ROLE_LABELS.get(row.get('role'), 'Staff')
        row['assigned_order_total'] = safe_int(row.get('assigned_order_total'))
        row['verified_payment_total'] = safe_int(row.get('verified_payment_total'))

    return rows


def normalize_backoffice_destination_type(value):
    """Keep destination type within supported values."""
    normalized = (value or '').strip().lower()
    return normalized if normalized in BACKOFFICE_DESTINATION_TYPES else 'internasional'


def normalize_backoffice_region_slug(value):
    """Keep region slug within known continent buckets."""
    normalized = (value or '').strip().lower()
    return normalized if normalized in REGION_CONFIG else 'asia'


def normalize_backoffice_category(value):
    """Keep category labels readable and consistent."""
    normalized = (value or '').strip()
    return normalized if normalized in BACKOFFICE_CATEGORY_OPTIONS else 'Alam'


def normalize_package_kind(value):
    """Keep package kind within supported values."""
    normalized = (value or '').strip().lower()
    return normalized if normalized in BACKOFFICE_PACKAGE_KIND_OPTIONS else 'custom'


def normalize_package_status(value):
    """Keep package status within supported values."""
    normalized = (value or '').strip().lower()
    return normalized if normalized in BACKOFFICE_PACKAGE_STATUS_OPTIONS else 'aktif'


def generate_package_code(destination_name, package_name):
    """Create a readable internal package code when staff leaves it blank."""
    base_destination = re.sub(r'[^A-Za-z0-9]+', '-', (destination_name or '').upper()).strip('-')
    base_package = re.sub(r'[^A-Za-z0-9]+', '-', (package_name or '').upper()).strip('-')
    joined = '-'.join(part for part in [base_destination[:12], base_package[:16]] if part)
    return joined[:40] or f"PKG-{secrets.randbelow(900000) + 100000}"


def fetch_backoffice_destinations(search_query='', region_filter='', type_filter=''):
    """Load destination catalog for internal management."""
    conditions = []
    params = []

    if search_query:
        like_value = f"%{search_query}%"
        conditions.append("""
            (
                w.nama LIKE %s OR
                COALESCE(w.negara, '') LIKE %s OR
                COALESCE(w.lokasi, '') LIKE %s OR
                COALESCE(w.kategori, '') LIKE %s
            )
        """)
        params.extend([like_value, like_value, like_value, like_value])

    normalized_region = normalize_backoffice_region_slug(region_filter) if region_filter else ''
    if normalized_region:
        append_region_condition(conditions, params, normalized_region)

    normalized_type = normalize_backoffice_destination_type(type_filter) if type_filter else ''
    if normalized_type:
        conditions.append("COALESCE(d.tipe, %s) = %s")
        params.extend([normalized_type, normalized_type])

    where_sql = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    db = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute(f"""
        SELECT
            w.id,
            w.nama,
            w.lokasi,
            w.negara,
            w.benua,
            w.kategori,
            w.deskripsi,
            w.foto,
            w.rating,
            w.display_order,
            w.is_active,
            COALESCE(d.tipe, 'internasional') AS tipe,
            COUNT(DISTINCT tp.id) AS package_total,
            COUNT(DISTINCT p.id) AS booking_total,
            MIN(tp.harga) AS min_price
        FROM wisata w
        LEFT JOIN destinasi d ON d.nama = w.nama
        LEFT JOIN tipe_paket tp ON tp.wisata_id = w.id
        LEFT JOIN pemesanan p ON p.paket_id = tp.id
        {where_sql}
        GROUP BY
            w.id, w.nama, w.lokasi, w.negara, w.benua, w.kategori, w.deskripsi,
            w.foto, w.rating, w.display_order, w.is_active, d.tipe
        ORDER BY
            COALESCE(w.display_order, 9999) ASC,
            w.nama ASC
    """, tuple(params))
    rows = apply_destination_media_list(cur.fetchall())
    rows = attach_promo_metadata_to_destinations(cur, rows)
    cur.close()
    db.close()

    for row in rows:
        row['type_label'] = 'Lokal' if (row.get('tipe') or '').lower() == 'lokal' else 'Internasional'
        row['region_slug'] = get_region_slug(row.get('negara') or row.get('lokasi'), row.get('tipe'))
        row['package_total'] = safe_int(row.get('package_total'))
        row['booking_total'] = safe_int(row.get('booking_total'))
        row['min_price'] = safe_int(row.get('min_price'))

    return rows


def fetch_backoffice_finance_rows(search_query='', status_filter='', method_filter=''):
    """Load payment history rows for finance and owner reporting."""
    db = get_db()
    cur = db.cursor(dictionary=True)

    conditions = []
    params = []

    if search_query:
        like_value = f"%{search_query}%"
        conditions.append("""
            (
                COALESCE(p.kode_pemesanan, '') LIKE %s OR
                COALESCE(p.nama_pemesan, '') LIKE %s OR
                COALESCE(p.email, '') LIKE %s OR
                COALESCE(w.nama, '') LIKE %s OR
                COALESCE(pb.payment_reference, '') LIKE %s
            )
        """)
        params.extend([like_value, like_value, like_value, like_value, like_value])

    if status_filter:
        conditions.append("pb.status_pembayaran = %s")
        params.append(status_filter)

    if method_filter and method_filter in PAYMENT_METHOD_CONFIG:
        conditions.append("pb.metode_pembayaran = %s")
        params.append(method_filter)

    where_sql = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    cur.execute(f"""
        SELECT
            pb.*,
            p.kode_pemesanan,
            p.nama_pemesan,
            p.email,
            p.total_harga,
            p.total_diskon,
            p.harga_awal,
            p.tanggal_pergi,
            tp.nama_paket,
            w.nama AS wisata_nama,
            w.negara,
            verifier.nama_lengkap AS verified_by_name
        FROM pembayaran pb
        JOIN pemesanan p ON p.id = pb.pemesanan_id
        JOIN tipe_paket tp ON tp.id = p.paket_id
        JOIN wisata w ON w.id = tp.wisata_id
        LEFT JOIN akun_staff verifier ON verifier.id = pb.verified_by_staff_id
        {where_sql}
        ORDER BY
            COALESCE(pb.tanggal_pembayaran, pb.created_at, NOW()) DESC,
            pb.id DESC
    """, tuple(params))
    rows = cur.fetchall()

    cur.execute("""
        SELECT
            COUNT(*) AS total_transactions,
            SUM(CASE WHEN status_pembayaran = 'menunggu_verifikasi' THEN 1 ELSE 0 END) AS waiting_review,
            SUM(CASE WHEN status_pembayaran = 'berhasil' THEN jumlah_dibayar ELSE 0 END) AS confirmed_amount,
            SUM(CASE WHEN gateway_provider = 'manual' THEN jumlah_dibayar ELSE 0 END) AS manual_amount,
            SUM(CASE WHEN gateway_provider = 'demo_qris' THEN 1 ELSE 0 END) AS demo_transactions,
            SUM(CASE WHEN gateway_provider = 'demo_qris' AND status_pembayaran = 'berhasil' THEN jumlah_dibayar ELSE 0 END) AS demo_amount
        FROM pembayaran
    """)
    summary = cur.fetchone() or {}

    cur.close()
    db.close()

    for row in rows:
        row['payment_method_meta'] = PAYMENT_METHOD_CONFIG.get(row.get('metode_pembayaran'), {})
        row['country_label'] = get_country_name(row)
        row['jumlah_dibayar'] = safe_int(row.get('jumlah_dibayar'))
        row['total_harga'] = safe_int(row.get('total_harga'))
        row['harga_awal'] = safe_int(row.get('harga_awal'))
        row['total_diskon'] = safe_int(row.get('total_diskon'))
        row['payment_label'] = row['payment_method_meta'].get('label', row.get('metode_pembayaran', '-'))
        row['gateway_provider_label'] = get_gateway_provider_label(row.get('gateway_provider'))
        row['is_demo_payment'] = (row.get('gateway_provider') or '').strip().lower() == 'demo_qris'
        
        # Parse JSON detail map for evidence and other things
        detail_map = {}
        if row.get('raw_response_json'):
            try:
                import json
                detail_map = json.loads(row['raw_response_json'])
            except:
                pass
        row['detail_map'] = detail_map

    return rows, {
        'total_transactions': safe_int(summary.get('total_transactions')),
        'waiting_review': safe_int(summary.get('waiting_review')),
        'confirmed_amount': safe_int(summary.get('confirmed_amount')),
        'manual_amount': safe_int(summary.get('manual_amount')),
        'demo_transactions': safe_int(summary.get('demo_transactions')),
        'demo_amount': safe_int(summary.get('demo_amount'))
    }


def fetch_backoffice_promo_rows(status_filter=''):
    """Load promo records and destination options for the admin module."""
    db = get_db()
    cur = db.cursor(dictionary=True)

    cur.execute("""
        SELECT
            w.id,
            w.nama,
            w.negara,
            w.benua,
            w.is_active
        FROM wisata w
        ORDER BY COALESCE(w.display_order, 9999) ASC, w.nama ASC
    """)
    destination_options = cur.fetchall()

    cur.execute("""
        SELECT
            pr.*,
            w.nama AS wisata_nama,
            w.negara,
            w.benua,
            MIN(tp.harga) AS min_package_price,
            s.nama_lengkap AS created_by_name
        FROM promo_destinasi pr
        JOIN wisata w ON w.id = pr.wisata_id
        LEFT JOIN tipe_paket tp ON tp.wisata_id = w.id
        LEFT JOIN akun_staff s ON s.id = pr.created_by_staff_id
        GROUP BY pr.id
        ORDER BY pr.created_at DESC, pr.id DESC
    """)
    rows = cur.fetchall()
    cur.close()
    db.close()

    prepared_rows = []
    for row in rows:
        row['discount_type'] = normalize_discount_type(row.get('discount_type'))
        row['discount_value'] = safe_int(row.get('discount_value'))
        row['status_key'] = get_promo_status_key(row)
        row['status_meta'] = PROMO_STATUS_META[row['status_key']]
        row['badge_text'] = format_promo_badge(row)
        row['min_package_price'] = safe_int(row.get('min_package_price'))
        row['price_meta'] = calculate_discounted_price(row['min_package_price'], row if row['status_key'] == 'active' else None)
        if not status_filter or row['status_key'] == status_filter:
            prepared_rows.append(row)

    destination_options = [item for item in destination_options if safe_int(item.get('is_active'), 1)]
    return destination_options, prepared_rows


def fetch_backoffice_destination_detail(wisata_id):
    """Load one destination and its package roster for internal editing."""
    db = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute("""
        SELECT
            w.*,
            COALESCE(d.id, 0) AS destinasi_id,
            COALESCE(d.tipe, 'internasional') AS tipe,
            COALESCE(d.maps_url, w.maps_url) AS maps_url,
            COALESCE(d.total_review, 0) AS total_review
        FROM wisata w
        LEFT JOIN destinasi d ON d.nama = w.nama
        WHERE w.id = %s
        LIMIT 1
    """, (wisata_id,))
    destination_row = apply_destination_media(cur.fetchone())

    package_rows = []
    if destination_row:
        cur.execute("""
            SELECT
                tp.*,
                COUNT(DISTINCT p.id) AS booking_total
            FROM tipe_paket tp
            LEFT JOIN pemesanan p ON p.paket_id = tp.id
            WHERE tp.wisata_id = %s
            GROUP BY tp.id
            ORDER BY FIELD(tp.status_paket, 'aktif', 'draft', 'nonaktif'), tp.harga ASC, tp.id ASC
        """, (wisata_id,))
        package_rows = cur.fetchall()
        promo_map = fetch_promos_for_wisata_ids(cur, [wisata_id])
        active_promo = pick_current_active_promo(promo_map.get(wisata_id, []))
        attach_promo_metadata_to_destinations(cur, [destination_row])
        destination_row['active_promo'] = active_promo
        destination_row['all_promo_rows'] = promo_map.get(wisata_id, [])
        for package_row in package_rows:
            apply_promo_to_package_row(package_row, active_promo)

    cur.close()
    db.close()

    if destination_row:
        destination_row['region_slug'] = get_region_slug(destination_row.get('negara') or destination_row.get('lokasi'), destination_row.get('tipe'))

    for package_row in package_rows:
        package_row['booking_total'] = safe_int(package_row.get('booking_total'))
        package_row['harga'] = safe_int(package_row.get('harga'))
        package_row['kuota_total'] = safe_int(package_row.get('kuota_total'), 20)
        package_row['kuota_tersedia'] = safe_int(package_row.get('kuota_tersedia'), package_row['kuota_total'])

    return destination_row, package_rows


def fetch_backoffice_order_detail(pemesanan_id):
    """Load a full operational order record for owner/staff views."""
    db = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute("""
        SELECT
            p.*,
            tp.nama_paket,
            tp.kode_paket,
            tp.jenis_paket,
            tp.durasi,
            tp.harga,
            tp.keberangkatan_info,
            tp.meeting_point,
            w.nama AS wisata_nama,
            w.lokasi,
            w.negara,
            w.foto,
            w.moment_foto,
            pb.id AS pembayaran_id,
            pb.metode_pembayaran,
            pb.status_pembayaran,
            pb.tanggal_pembayaran,
            pb.jumlah_dibayar,
            pb.keterangan AS payment_note,
            pb.payment_reference,
            pb.channel_code,
            pb.gateway_provider,
            pb.gateway_status,
            pb.verified_at,
            pb.verification_note,
            pb.bukti_pembayaran,
            pb.qr_code_path,
            verifier.nama_lengkap AS payment_verified_by_name,
            op.status_operasional,
            op.status_tiket,
            op.status_voucher,
            op.status_dokumen,
            op.assigned_staff_id,
            op.payment_checked_by,
            op.payment_checked_at,
            op.deadline_follow_up,
            op.catatan_internal,
            assigned.nama_lengkap AS assigned_staff_name
        FROM pemesanan p
        JOIN tipe_paket tp ON p.paket_id = tp.id
        JOIN wisata w ON tp.wisata_id = w.id
        LEFT JOIN pembayaran pb ON pb.pemesanan_id = p.id
        LEFT JOIN operasional_pesanan op ON op.pemesanan_id = p.id
        LEFT JOIN akun_staff assigned ON assigned.id = op.assigned_staff_id
        LEFT JOIN akun_staff verifier ON verifier.id = pb.verified_by_staff_id
        WHERE p.id = %s
        LIMIT 1
    """, (pemesanan_id,))
    order_row = cur.fetchone()

    payment_detail_rows = []
    payment_audit_rows = []
    status_logs = []
    participant_rows = []

    if order_row and order_row.get('pembayaran_id'):
        cur.execute("SELECT * FROM payment_detail WHERE pembayaran_id = %s ORDER BY id ASC", (order_row['pembayaran_id'],))
        payment_detail_rows = cur.fetchall()
        payment_audit_rows = fetch_payment_audit_rows(cur, order_row['pembayaran_id'])

    if order_row and table_exists(cur, 'pemesanan_status_log'):
        cur.execute("""
            SELECT *
            FROM pemesanan_status_log
            WHERE pemesanan_id = %s
            ORDER BY created_at DESC, id DESC
            LIMIT 20
        """, (pemesanan_id,))
        status_logs = cur.fetchall()

    if order_row and table_exists(cur, 'detail_peserta_pesanan'):
        cur.execute("""
            SELECT *
            FROM detail_peserta_pesanan
            WHERE pemesanan_id = %s
            ORDER BY id ASC
        """, (pemesanan_id,))
        participant_rows = cur.fetchall()

    cur.close()
    db.close()

    prepared_order_row = prepare_backoffice_order_row(order_row)
    if prepared_order_row:
        prepared_order_row['payment_detail_display_rows'] = build_backoffice_payment_detail_display(prepared_order_row, payment_detail_rows)

    return (
        prepared_order_row,
        payment_detail_rows,
        payment_audit_rows,
        status_logs,
        participant_rows
    )


@app.route('/backoffice/setup-owner', methods=['GET', 'POST'])
def backoffice_setup_owner():
    """Bootstrap the first owner account for the operational dashboard."""
    if get_current_staff():
        return redirect(url_for('backoffice_dashboard'))

    if backoffice_has_staff():
        flash('Akun staff sudah tersedia. Gunakan halaman login backoffice.', 'info')
        return redirect(url_for('backoffice_login'))

    if request.method == 'POST':
        full_name = request.form.get('nama_lengkap', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        captcha_answer = request.form.get('setup_captcha_answer', '')
        honeypot = request.form.get('office_website', '')

        if not full_name:
            flash('Nama lengkap owner masih kosong.', 'error')
        elif not is_valid_email_address(email):
            flash('Masukkan email owner yang valid untuk login backoffice.', 'error')
        elif len(password) < PASSWORD_MIN_LENGTH:
            flash('Password owner minimal 8 karakter.', 'error')
        elif password != confirm_password:
            flash('Konfirmasi password owner belum cocok.', 'error')
        elif not validate_human_challenge('backoffice_setup', captcha_answer, honeypot):
            flash('Verifikasi manusia belum cocok. Coba isi ulang captcha setup owner.', 'error')
        else:
            db = get_db()
            cur = db.cursor(dictionary=True)
            cur.execute("SELECT id FROM akun_staff WHERE LOWER(email) = %s LIMIT 1", (email,))
            existing_staff = cur.fetchone()

            if existing_staff:
                cur.close()
                db.close()
                flash('Email ini sudah terpakai sebagai akun staff.', 'error')
            else:
                timestamp_now = datetime.now()
                cur.execute("""
                    INSERT INTO akun_staff (
                        nama_lengkap, email, password_hash, role, is_active, created_at, updated_at
                    ) VALUES (%s, %s, %s, 'owner', 1, %s, %s)
                """, (
                    full_name,
                    email,
                    generate_password_hash(password),
                    timestamp_now,
                    timestamp_now
                ))
                staff_id = cur.lastrowid
                db.commit()

                cur.execute("SELECT * FROM akun_staff WHERE id = %s LIMIT 1", (staff_id,))
                staff_row = cur.fetchone()
                cur.close()
                db.close()

                remember_logged_in_staff(staff_row)
                update_staff_last_login(staff_row['id'])
                flash('Akun owner pertama berhasil dibuat. Dashboard backoffice sudah siap dipakai.', 'success')
                return redirect(url_for('backoffice_dashboard'))

    return render_template(
        'backoffice/setup_owner.html',
        setup_captcha_question=get_human_challenge('backoffice_setup')
    )


@app.route('/backoffice/login', methods=['GET', 'POST'])
def backoffice_login():
    """Login page for owner/staff dashboard."""
    if get_current_staff():
        next_url = normalize_backoffice_next_url(request.args.get('next') or session.get('backoffice_next') or url_for('backoffice_dashboard'))
        session.pop('backoffice_next', None)
        return redirect(next_url)

    if not backoffice_has_staff():
        flash('Buat akun owner pertama dulu sebelum login ke dashboard.', 'info')
        return redirect(url_for('backoffice_setup_owner'))

    next_url = normalize_backoffice_next_url(request.args.get('next') or session.get('backoffice_next') or url_for('backoffice_dashboard'))
    session['backoffice_next'] = next_url

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        captcha_answer = request.form.get('staff_captcha_answer', '')
        honeypot = request.form.get('office_login_website', '')

        if not is_valid_email_address(email):
            flash('Masukkan email staff yang valid.', 'error')
        elif not password:
            flash('Password staff masih kosong.', 'error')
        elif not validate_human_challenge('backoffice_login', captcha_answer, honeypot):
            flash('Verifikasi manusia di halaman staff belum cocok.', 'error')
        else:
            staff_row = fetch_staff_by_email(email)
            if not staff_row:
                flash('Akun staff belum ditemukan.', 'error')
            elif not staff_row.get('is_active'):
                flash('Akun staff ini sedang nonaktif.', 'error')
            elif not check_password_hash(staff_row['password_hash'], password):
                flash('Email staff atau password belum cocok.', 'error')
            else:
                remember_logged_in_staff(staff_row)
                update_staff_last_login(staff_row['id'])
                session.pop('backoffice_next', None)
                flash('Login backoffice berhasil.', 'success')
                return redirect(next_url)

    return render_template(
        'backoffice/login.html',
        next_url=next_url,
        staff_captcha_question=get_human_challenge('backoffice_login')
    )


@app.route('/backoffice/logout')
def backoffice_logout():
    """Logout for staff dashboard only."""
    clear_staff_session()
    flash('Sesi backoffice sudah ditutup.', 'success')
    return redirect(url_for('backoffice_login'))


@app.route('/backoffice')
@backoffice_login_required
def backoffice_dashboard():
    """Separate owner/staff dashboard for operational order processing."""
    summary = {
        'total_orders': 0,
        'new_orders': 0,
        'waiting_payment': 0,
        'payment_review': 0,
        'ticket_queue': 0,
        'ready_to_depart': 0,
        'completed_orders': 0,
        'gross_revenue': 0,
        'confirmed_revenue': 0,
        'demo_transactions': 0,
        'demo_revenue': 0,
        'active_destinations': 0,
        'active_promos': 0,
        'active_staff': 0
    }
    recent_orders = []
    recent_logs = []

    db = get_db()
    cur = db.cursor(dictionary=True)

    cur.execute("""
        SELECT
            COUNT(*) AS total_orders,
            SUM(CASE WHEN COALESCE(op.status_operasional, 'baru') = 'baru' THEN 1 ELSE 0 END) AS new_orders,
            SUM(CASE WHEN COALESCE(op.status_operasional, 'menunggu_pembayaran') = 'menunggu_pembayaran' THEN 1 ELSE 0 END) AS waiting_payment,
            SUM(CASE WHEN COALESCE(op.status_operasional, '') = 'verifikasi_pembayaran' THEN 1 ELSE 0 END) AS payment_review,
            SUM(CASE WHEN COALESCE(op.status_tiket, '') = 'diproses' THEN 1 ELSE 0 END) AS ticket_queue,
            SUM(CASE WHEN COALESCE(op.status_operasional, '') = 'siap_berangkat' THEN 1 ELSE 0 END) AS ready_to_depart,
            SUM(CASE WHEN p.status = 'completed' THEN 1 ELSE 0 END) AS completed_orders,
            SUM(COALESCE(p.total_harga, 0)) AS gross_revenue,
            SUM(CASE WHEN COALESCE(pb.status_pembayaran, '') = 'berhasil' THEN COALESCE(p.total_harga, 0) ELSE 0 END) AS confirmed_revenue,
            SUM(CASE WHEN COALESCE(pb.gateway_provider, '') = 'demo_qris' THEN 1 ELSE 0 END) AS demo_transactions,
            SUM(CASE WHEN COALESCE(pb.gateway_provider, '') = 'demo_qris' AND COALESCE(pb.status_pembayaran, '') = 'berhasil' THEN COALESCE(p.total_harga, 0) ELSE 0 END) AS demo_revenue
        FROM pemesanan p
        LEFT JOIN operasional_pesanan op ON op.pemesanan_id = p.id
        LEFT JOIN pembayaran pb ON pb.pemesanan_id = p.id
    """)
    summary_row = cur.fetchone() or {}
    for key in summary:
        if key in summary_row:
            summary[key] = safe_int(summary_row.get(key))

    cur.execute("""
        SELECT
            (SELECT COUNT(*) FROM wisata WHERE COALESCE(is_active, 1) = 1) AS active_destinations,
            (SELECT COUNT(*) FROM akun_staff WHERE is_active = 1) AS active_staff,
            (
                SELECT COUNT(*)
                FROM promo_destinasi
                WHERE is_active = 1
                  AND starts_at <= NOW()
                  AND ends_at > NOW()
            ) AS active_promos
    """)
    extra_summary_row = cur.fetchone() or {}
    summary['active_destinations'] = safe_int(extra_summary_row.get('active_destinations'))
    summary['active_promos'] = safe_int(extra_summary_row.get('active_promos'))
    summary['active_staff'] = safe_int(extra_summary_row.get('active_staff'))

    cur.execute("""
        SELECT
            p.id,
            p.kode_pemesanan,
            p.nama_pemesan,
            p.email,
            p.tanggal_pesan,
            p.tanggal_pergi,
            p.jumlah_orang,
            p.total_harga,
            p.status,
            tp.nama_paket,
            w.nama AS wisata_nama,
            w.lokasi,
            w.negara,
            w.foto,
            pb.status_pembayaran,
            pb.metode_pembayaran,
            op.status_operasional,
            op.status_tiket,
            assigned.nama_lengkap AS assigned_staff_name
        FROM pemesanan p
        JOIN tipe_paket tp ON tp.id = p.paket_id
        JOIN wisata w ON w.id = tp.wisata_id
        LEFT JOIN pembayaran pb ON pb.pemesanan_id = p.id
        LEFT JOIN operasional_pesanan op ON op.pemesanan_id = p.id
        LEFT JOIN akun_staff assigned ON assigned.id = op.assigned_staff_id
        ORDER BY
            FIELD(COALESCE(op.status_operasional, 'baru'),
                'verifikasi_pembayaran', 'baru', 'menunggu_pembayaran', 'siapkan_tiket', 'siapkan_voucher', 'siap_berangkat', 'selesai', 'dibatalkan'
            ),
            p.tanggal_pesan DESC
        LIMIT 8
    """)
    recent_orders = [prepare_backoffice_order_row(row) for row in cur.fetchall()]

    if table_exists(cur, 'pemesanan_status_log'):
        cur.execute("""
            SELECT
                log.*,
                p.kode_pemesanan,
                p.nama_pemesan,
                w.nama AS wisata_nama
            FROM pemesanan_status_log log
            JOIN pemesanan p ON p.id = log.pemesanan_id
            JOIN tipe_paket tp ON tp.id = p.paket_id
            JOIN wisata w ON w.id = tp.wisata_id
            ORDER BY log.created_at DESC, log.id DESC
            LIMIT 10
        """)
        recent_logs = cur.fetchall()



    cur.execute("""
        SELECT
            DATE_FORMAT(p.tanggal_pesan, '%Y-%m') as month,
            SUM(p.total_harga) as total
        FROM pemesanan p
        JOIN pembayaran pb ON pb.pemesanan_id = p.id
        WHERE pb.status_pembayaran = 'berhasil'
        GROUP BY month
        ORDER BY month DESC
        LIMIT 6
    """)
    chart_rows = cur.fetchall()
    chart_labels = []
    chart_data = []
    
    # Reverse to show chronological order
    for row in reversed(chart_rows):
        chart_labels.append(row['month'])
        chart_data.append(safe_int(row['total']))

    # Fallback if no data
    if not chart_labels:
        from datetime import datetime
        chart_labels = [datetime.now().strftime('%Y-%m')]
        chart_data = [0]

    cur.close()
    db.close()


    return render_template(
        'backoffice/dashboard.html',
        summary=summary,
        recent_orders=recent_orders,
        recent_logs=recent_logs,
        chart_labels=chart_labels,
        chart_data=chart_data
    )


@app.route('/backoffice/keuangan')
@backoffice_role_required('owner', 'finance')
def backoffice_finance():
    """Finance and payment history workspace for internal reconciliation."""
    search_query = (request.args.get('q') or '').strip()
    status_filter = (request.args.get('status') or '').strip()
    method_filter = (request.args.get('method') or '').strip()

    finance_rows, finance_summary = fetch_backoffice_finance_rows(search_query, status_filter, method_filter)
    payment_status_options = ['pending', 'menunggu_verifikasi', 'berhasil', 'gagal']

    return render_template(
        'backoffice/finance.html',
        finance_rows=finance_rows,
        finance_summary=finance_summary,
        current_search_query=search_query,
        current_status_filter=status_filter,
        current_method_filter=method_filter,
        payment_status_options=payment_status_options,
        payment_methods=PAYMENT_METHOD_CONFIG,
        payment_destination_groups=list_payment_destination_groups(),
        payment_config=PAYMENT_DISPLAY_CONFIG
    )


@app.route('/backoffice/keuangan/export')
@backoffice_role_required('owner', 'finance')
def backoffice_finance_export():
    """Export filtered payment history as CSV for finance reconciliation."""
    search_query = (request.args.get('q') or '').strip()
    status_filter = (request.args.get('status') or '').strip()
    method_filter = (request.args.get('method') or '').strip()
    finance_rows, _ = fetch_backoffice_finance_rows(search_query, status_filter, method_filter)

    output_buffer = io.StringIO()
    output_buffer.write('\ufeff')
    csv_writer = csv.writer(output_buffer)
    csv_writer.writerow([
        'Kode Pesanan',
        'Nama Customer',
        'Email',
        'Destinasi',
        'Negara',
        'Paket',
        'Metode',
        'Provider',
        'Channel',
        'Status Pembayaran',
        'Jumlah Dibayar',
        'Harga Awal',
        'Total Diskon',
        'Referensi',
        'Tanggal Bayar',
        'Diverifikasi Oleh',
        'Waktu Verifikasi',
        'Catatan Verifikasi'
    ])

    for row in finance_rows:
        csv_writer.writerow([
            row.get('kode_pemesanan') or build_booking_code(row.get('pemesanan_id')),
            row.get('nama_pemesan') or '',
            row.get('email') or '',
            row.get('wisata_nama') or '',
            row.get('country_label') or '',
            row.get('nama_paket') or '',
            row.get('payment_label') or '',
            row.get('gateway_provider') or '',
            row.get('channel_code') or '',
            row.get('status_pembayaran') or '',
            safe_int(row.get('jumlah_dibayar')),
            safe_int(row.get('harga_awal')),
            safe_int(row.get('total_diskon')),
            row.get('payment_reference') or '',
            row.get('tanggal_pembayaran').strftime('%Y-%m-%d %H:%M:%S') if row.get('tanggal_pembayaran') else '',
            row.get('verified_by_name') or '',
            row.get('verified_at').strftime('%Y-%m-%d %H:%M:%S') if row.get('verified_at') else '',
            row.get('verification_note') or row.get('keterangan') or ''
        ])

    timestamp_label = datetime.now().strftime('%Y%m%d-%H%M%S')
    response = Response(output_buffer.getvalue(), mimetype='text/csv; charset=utf-8')
    response.headers['Content-Disposition'] = f'attachment; filename=eltravel-finance-{timestamp_label}.csv'
    return response


@app.route('/backoffice/staff', methods=['GET', 'POST'])
@backoffice_role_required('owner')
def backoffice_staff():
    """Owner-only workspace to create and maintain staff access."""
    if request.method == 'POST':
        action = (request.form.get('action') or '').strip()
        full_name = request.form.get('nama_lengkap', '').strip()
        email = request.form.get('email', '').strip().lower()
        role = (request.form.get('role') or 'operasional').strip()
        is_active = 1 if request.form.get('is_active', '1') == '1' else 0
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if action in {'create_staff', 'update_staff'}:
            if not full_name:
                flash('Nama lengkap staff wajib diisi.', 'error')
            elif not is_valid_email_address(email):
                flash('Masukkan email staff yang valid.', 'error')
            elif role not in STAFF_ROLE_LABELS:
                flash('Role staff tidak dikenali.', 'error')
            elif action == 'create_staff' and len(password) < PASSWORD_MIN_LENGTH:
                flash('Password staff minimal 8 karakter.', 'error')
            elif password and password != confirm_password:
                flash('Konfirmasi password staff belum cocok.', 'error')
            else:
                db = get_db()
                cur = db.cursor(dictionary=True)
                timestamp_now = datetime.now()

                if action == 'create_staff':
                    cur.execute("SELECT id FROM akun_staff WHERE LOWER(email) = %s LIMIT 1", (email,))
                    if cur.fetchone():
                        flash('Email staff ini sudah terdaftar.', 'error')
                    else:
                        cur.execute("""
                            INSERT INTO akun_staff (
                                nama_lengkap, email, password_hash, role, is_active, created_at, updated_at
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """, (
                            full_name,
                            email,
                            generate_password_hash(password),
                            role,
                            is_active,
                            timestamp_now,
                            timestamp_now
                        ))
                        db.commit()
                        flash('Akun staff baru berhasil dibuat.', 'success')
                        cur.close()
                        db.close()
                        return redirect(url_for('backoffice_staff'))
                else:
                    staff_id = safe_int(request.form.get('staff_id'))
                    cur.execute("SELECT * FROM akun_staff WHERE id = %s LIMIT 1", (staff_id,))
                    existing_staff = cur.fetchone()

                    if not existing_staff:
                        flash('Staff yang ingin diperbarui tidak ditemukan.', 'error')
                    else:
                        cur.execute("SELECT id FROM akun_staff WHERE LOWER(email) = %s AND id <> %s LIMIT 1", (email, staff_id))
                        duplicate_staff = cur.fetchone()
                        cur.execute("SELECT COUNT(*) AS total_owner FROM akun_staff WHERE role = 'owner' AND is_active = 1")
                        owner_count_row = cur.fetchone() or {}
                        active_owner_total = safe_int(owner_count_row.get('total_owner'))
                        removing_last_owner = (
                            existing_staff.get('role') == 'owner'
                            and existing_staff.get('is_active')
                            and (role != 'owner' or not is_active)
                            and active_owner_total <= 1
                        )

                        if duplicate_staff:
                            flash('Email staff ini sudah dipakai akun lain.', 'error')
                        elif removing_last_owner:
                            flash('Setidaknya harus ada satu owner aktif untuk menjaga akses backoffice.', 'error')
                        elif password and len(password) < PASSWORD_MIN_LENGTH:
                            flash('Password baru staff minimal 8 karakter.', 'error')
                        else:
                            update_fields = [
                                "nama_lengkap = %s",
                                "email = %s",
                                "role = %s",
                                "is_active = %s",
                                "updated_at = %s"
                            ]
                            update_params = [full_name, email, role, is_active, timestamp_now]

                            if password:
                                update_fields.append("password_hash = %s")
                                update_params.append(generate_password_hash(password))

                            update_params.append(staff_id)
                            cur.execute(f"""
                                UPDATE akun_staff
                                SET {', '.join(update_fields)}
                                WHERE id = %s
                            """, tuple(update_params))
                            db.commit()

                            if get_current_staff_id() == staff_id:
                                cur.execute("SELECT * FROM akun_staff WHERE id = %s LIMIT 1", (staff_id,))
                                refreshed_staff = cur.fetchone()
                                if refreshed_staff and refreshed_staff.get('is_active'):
                                    remember_logged_in_staff(refreshed_staff)
                                else:
                                    clear_staff_session()

                            flash('Data staff berhasil diperbarui.', 'success')
                            cur.close()
                            db.close()
                            return redirect(url_for('backoffice_staff'))

                cur.close()
                db.close()
        else:
            flash('Aksi staff tidak dikenali.', 'error')

    staff_rows = fetch_backoffice_staff_directory()
    return render_template(
        'backoffice/staff.html',
        staff_rows=staff_rows,
        staff_role_options=STAFF_ROLE_OPTIONS
    )


@app.route('/backoffice/promo', methods=['GET', 'POST'])
@backoffice_role_required('owner', 'operasional')
def backoffice_promotions():
    """CRUD promo destinasi internal."""
    status_filter = (request.args.get('status') or '').strip().lower()

    if request.method == 'POST':
        action = (request.form.get('action') or '').strip()
        promo_name = request.form.get('promo_name', '').strip()
        promo_label = request.form.get('promo_label', '').strip()
        description = request.form.get('description', '').strip()
        wisata_id = safe_int(request.form.get('wisata_id'))
        discount_type = normalize_discount_type(request.form.get('discount_type'))
        discount_value = safe_int(request.form.get('discount_value'))
        starts_at = parse_backoffice_datetime(request.form.get('starts_at'))
        ends_at = parse_backoffice_datetime(request.form.get('ends_at'))
        is_active = 1 if request.form.get('is_active', '1') == '1' else 0

        if action in {'create_promo', 'update_promo'}:
            if not wisata_id or not promo_name:
                flash('Destinasi dan nama promo wajib diisi.', 'error')
            elif discount_value <= 0:
                flash('Nilai diskon harus lebih besar dari nol.', 'error')
            elif not starts_at or not ends_at or ends_at <= starts_at:
                flash('Periode promo harus diisi dengan tanggal mulai dan selesai yang valid.', 'error')
            else:
                db = get_db()
                cur = db.cursor(dictionary=True)
                if action == 'create_promo':
                    cur.execute("""
                        INSERT INTO promo_destinasi (
                            wisata_id, promo_name, promo_label, description, discount_type, discount_value,
                            starts_at, ends_at, is_active, created_by_staff_id, created_at, updated_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        wisata_id,
                        promo_name,
                        promo_label or None,
                        description,
                        discount_type,
                        discount_value,
                        starts_at,
                        ends_at,
                        is_active,
                        get_current_staff_id(),
                        datetime.now(),
                        datetime.now()
                    ))
                    db.commit()
                    flash('Promo baru berhasil ditambahkan.', 'success')
                else:
                    promo_id = safe_int(request.form.get('promo_id'))
                    cur.execute("SELECT id FROM promo_destinasi WHERE id = %s LIMIT 1", (promo_id,))
                    if not cur.fetchone():
                        flash('Promo yang ingin diperbarui tidak ditemukan.', 'error')
                    else:
                        cur.execute("""
                            UPDATE promo_destinasi
                            SET wisata_id = %s,
                                promo_name = %s,
                                promo_label = %s,
                                description = %s,
                                discount_type = %s,
                                discount_value = %s,
                                starts_at = %s,
                                ends_at = %s,
                                is_active = %s,
                                updated_at = %s
                            WHERE id = %s
                        """, (
                            wisata_id,
                            promo_name,
                            promo_label or None,
                            description,
                            discount_type,
                            discount_value,
                            starts_at,
                            ends_at,
                            is_active,
                            datetime.now(),
                            promo_id
                        ))
                        db.commit()
                        flash('Promo berhasil diperbarui.', 'success')
                cur.close()
                db.close()
                return redirect(url_for('backoffice_promotions', status=status_filter or None))

        elif action == 'delete_promo':
            promo_id = safe_int(request.form.get('promo_id'))
            if not promo_id:
                flash('Promo yang akan dihapus tidak valid.', 'error')
            else:
                db = get_db()
                cur = db.cursor()
                cur.execute("DELETE FROM promo_destinasi WHERE id = %s", (promo_id,))
                db.commit()
                cur.close()
                db.close()
                flash('Promo berhasil dihapus dari sistem.', 'success')
                return redirect(url_for('backoffice_promotions', status=status_filter or None))

    destination_options, promo_rows = fetch_backoffice_promo_rows(status_filter)
    return render_template(
        'backoffice/promotions.html',
        destination_options=destination_options,
        promo_rows=promo_rows,
        current_status_filter=status_filter,
        discount_type_options=PROMO_DISCOUNT_TYPE_OPTIONS,
        promo_status_meta=PROMO_STATUS_META
    )


@app.route('/backoffice/pesanan')
@backoffice_login_required
def backoffice_orders():
    """Owner/staff queue with operational filters."""
    status_filter = (request.args.get('status') or '').strip().lower()
    payment_filter = (request.args.get('payment') or '').strip().lower()
    search_query = (request.args.get('q') or '').strip()

    conditions = []
    params = []

    if status_filter in BACKOFFICE_OPERATIONAL_STATUS_OPTIONS:
        conditions.append("COALESCE(op.status_operasional, 'baru') = %s")
        params.append(status_filter)

    if payment_filter in BACKOFFICE_PAYMENT_META:
        conditions.append("COALESCE(pb.status_pembayaran, 'pending') = %s")
        params.append(payment_filter)

    if search_query:
        like_value = f"%{search_query}%"
        conditions.append("""
            (
                COALESCE(p.kode_pemesanan, '') LIKE %s OR
                p.nama_pemesan LIKE %s OR
                COALESCE(p.email, '') LIKE %s OR
                w.nama LIKE %s OR
                COALESCE(w.negara, w.lokasi, '') LIKE %s
            )
        """)
        params.extend([like_value, like_value, like_value, like_value, like_value])

    where_sql = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    db = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute(f"""
        SELECT
            p.id,
            p.kode_pemesanan,
            p.nama_pemesan,
            p.email,
            p.telepon,
            p.tanggal_pesan,
            p.tanggal_pergi,
            p.jumlah_orang,
            p.total_harga,
            p.status,
            tp.nama_paket,
            tp.jenis_paket,
            w.nama AS wisata_nama,
            w.lokasi,
            w.negara,
            w.foto,
            pb.status_pembayaran,
            pb.metode_pembayaran,
            pb.tanggal_pembayaran,
            pb.payment_reference,
            op.status_operasional,
            op.status_tiket,
            op.status_voucher,
            op.status_dokumen,
            op.deadline_follow_up,
            assigned.nama_lengkap AS assigned_staff_name
        FROM pemesanan p
        JOIN tipe_paket tp ON tp.id = p.paket_id
        JOIN wisata w ON w.id = tp.wisata_id
        LEFT JOIN pembayaran pb ON pb.pemesanan_id = p.id
        LEFT JOIN operasional_pesanan op ON op.pemesanan_id = p.id
        LEFT JOIN akun_staff assigned ON assigned.id = op.assigned_staff_id
        {where_sql}
        ORDER BY
            FIELD(COALESCE(op.status_operasional, 'baru'),
                'verifikasi_pembayaran', 'baru', 'menunggu_pembayaran', 'siapkan_tiket', 'siapkan_voucher', 'siap_berangkat', 'selesai', 'dibatalkan'
            ),
            p.tanggal_pesan DESC
    """, tuple(params))
    order_rows = [prepare_backoffice_order_row(row) for row in cur.fetchall()]
    cur.close()
    db.close()

    filter_counts = {
        'all': len(order_rows),
        'payment_review': len([row for row in order_rows if (row.get('status_operasional') or '') == 'verifikasi_pembayaran']),
        'ready_ticket': len([row for row in order_rows if (row.get('status_operasional') or '') == 'siapkan_tiket']),
        'completed': len([row for row in order_rows if (row.get('status_operasional') or '') == 'selesai'])
    }

    return render_template(
        'backoffice/orders.html',
        order_rows=order_rows,
        filter_counts=filter_counts,
        current_status_filter=status_filter,
        current_payment_filter=payment_filter,
        current_search_query=search_query,
        operational_options=BACKOFFICE_OPERATIONAL_STATUS_OPTIONS,
        payment_options=list(BACKOFFICE_PAYMENT_META.keys()),
        operational_meta=BACKOFFICE_OPERATIONAL_META,
        payment_meta=BACKOFFICE_PAYMENT_META
    )


@app.route('/backoffice/destinasi', methods=['GET', 'POST'])
@backoffice_role_required('owner', 'operasional')
def backoffice_destinations():
    """Internal destination catalog with create form for staff."""
    search_query = (request.args.get('q') or '').strip()
    region_filter = (request.args.get('region') or '').strip().lower()
    type_filter = (request.args.get('tipe') or '').strip().lower()

    if request.method == 'POST':
        action = request.form.get('action', 'create_destination').strip()
        if action == 'create_destination':
            destination_name = request.form.get('nama', '').strip()
            location_label = request.form.get('lokasi', '').strip()
            country_label = request.form.get('negara', '').strip()
            region_slug = normalize_backoffice_region_slug(request.form.get('benua'))
            destination_type = normalize_backoffice_destination_type(request.form.get('tipe'))
            category_label = normalize_backoffice_category(request.form.get('kategori'))
            description = request.form.get('deskripsi', '').strip()
            photo_url = request.form.get('foto', '').strip()
            thumbnail_url = request.form.get('thumbnail_foto', '').strip()
            moment_url = request.form.get('moment_foto', '').strip()
            maps_url = request.form.get('maps_url', '').strip()
            best_time = request.form.get('best_time', '').strip()
            photo_source_label = request.form.get('foto_source_label', '').strip()
            photo_source_url = request.form.get('foto_source_url', '').strip()
            try:
                rating_value = max(0, min(5, float(request.form.get('rating') or 4.8)))
            except (TypeError, ValueError):
                rating_value = 4.8
            display_order = safe_int(request.form.get('display_order')) or None
            active_flag = 1 if request.form.get('is_active') == '1' else 0

            if not destination_name or not location_label or not country_label or not description:
                flash('Nama destinasi, lokasi, negara, dan deskripsi wajib diisi.', 'error')
            else:
                db = get_db()
                cur = db.cursor(dictionary=True)
                cur.execute("SELECT id FROM wisata WHERE LOWER(nama) = %s LIMIT 1", (destination_name.lower(),))
                existing_destination = cur.fetchone()

                if existing_destination:
                    cur.close()
                    db.close()
                    flash('Nama destinasi ini sudah ada. Buka detail destinasi yang sudah ada untuk mengeditnya.', 'error')
                else:
                    if display_order is None:
                        cur.execute("SELECT COALESCE(MAX(display_order), 0) AS max_order FROM wisata")
                        max_order_row = cur.fetchone() or {}
                        display_order = safe_int(max_order_row.get('max_order')) + 10

                    cur.execute("""
                        INSERT INTO wisata (
                            nama, lokasi, negara, benua, deskripsi, foto, maps_url, rating, kategori,
                            thumbnail_foto, moment_foto, foto_source_url, foto_source_label, best_time,
                            display_order, is_active
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        destination_name,
                        location_label,
                        country_label,
                        REGION_CONFIG[region_slug]['label'],
                        description,
                        photo_url,
                        maps_url,
                        rating_value,
                        category_label,
                        thumbnail_url,
                        moment_url,
                        photo_source_url,
                        photo_source_label,
                        best_time,
                        display_order,
                        active_flag
                    ))
                    wisata_id = cur.lastrowid

                    cur.execute("""
                        INSERT INTO destinasi (
                            nama, lokasi, negara, benua, deskripsi, foto, maps_url, rating, tipe, kategori,
                            total_review, thumbnail_foto, moment_foto, foto_source_url, foto_source_label,
                            best_time, display_order, is_active
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        destination_name,
                        location_label,
                        country_label,
                        REGION_CONFIG[region_slug]['label'],
                        description,
                        photo_url,
                        maps_url,
                        rating_value,
                        destination_type,
                        category_label,
                        thumbnail_url,
                        moment_url,
                        photo_source_url,
                        photo_source_label,
                        best_time,
                        display_order,
                        active_flag
                    ))

                    db.commit()
                    cur.close()
                    db.close()
                    flash('Destinasi baru berhasil ditambahkan dan langsung masuk ke database.', 'success')
                    return redirect(url_for('backoffice_destination_detail', wisata_id=wisata_id))

    destination_rows = fetch_backoffice_destinations(search_query, region_filter, type_filter)
    return render_template(
        'backoffice/destinations.html',
        destination_rows=destination_rows,
        current_search_query=search_query,
        current_region_filter=region_filter,
        current_type_filter=type_filter,
        region_options=BACKOFFICE_REGION_OPTIONS,
        type_options=BACKOFFICE_DESTINATION_TYPES,
        category_options=BACKOFFICE_CATEGORY_OPTIONS
    )


@app.route('/backoffice/destinasi/<int:wisata_id>', methods=['GET', 'POST'])
@backoffice_role_required('owner', 'operasional')
def backoffice_destination_detail(wisata_id):
    """Internal workspace to edit destination data and package departures."""
    destination_row, package_rows = fetch_backoffice_destination_detail(wisata_id)
    if not destination_row:
        flash('Destinasi tidak ditemukan di katalog internal.', 'error')
        return redirect(url_for('backoffice_destinations'))

    if request.method == 'POST':
        action = request.form.get('action', '').strip()

        try:
            db = get_db()
            cur = db.cursor(dictionary=True)
            cur.execute("""
                SELECT w.id, w.nama, COALESCE(d.id, 0) AS destinasi_id
                FROM wisata w
                LEFT JOIN destinasi d ON d.nama = w.nama
                WHERE w.id = %s
                LIMIT 1
            """, (wisata_id,))
            current_row = cur.fetchone()

            if not current_row:
                cur.close()
                db.close()
                flash('Destinasi tidak ditemukan.', 'error')
                return redirect(url_for('backoffice_destinations'))

            if action == 'save_destination':
                destination_name = request.form.get('nama', '').strip()
                location_label = request.form.get('lokasi', '').strip()
                country_label = request.form.get('negara', '').strip()
                region_slug = normalize_backoffice_region_slug(request.form.get('benua'))
                destination_type = normalize_backoffice_destination_type(request.form.get('tipe'))
                category_label = normalize_backoffice_category(request.form.get('kategori'))
                description = request.form.get('deskripsi', '').strip()
                photo_url = request.form.get('foto', '').strip()
                thumbnail_url = request.form.get('thumbnail_foto', '').strip()
                moment_url = request.form.get('moment_foto', '').strip()
                maps_url = request.form.get('maps_url', '').strip()
                best_time = request.form.get('best_time', '').strip()
                photo_source_label = request.form.get('foto_source_label', '').strip()
                photo_source_url = request.form.get('foto_source_url', '').strip()
                try:
                    rating_value = max(0, min(5, float(request.form.get('rating') or 4.8)))
                except (TypeError, ValueError):
                    rating_value = 4.8
                display_order = safe_int(request.form.get('display_order')) or None
                active_flag = 1 if request.form.get('is_active') == '1' else 0

                if not destination_name or not location_label or not country_label or not description:
                    flash('Nama destinasi, lokasi, negara, dan deskripsi wajib diisi.', 'error')
                else:
                    cur.execute("SELECT id FROM wisata WHERE LOWER(nama) = %s AND id <> %s LIMIT 1", (destination_name.lower(), wisata_id))
                    duplicate_row = cur.fetchone()
                    if duplicate_row:
                        flash('Nama destinasi ini sudah dipakai destinasi lain.', 'error')
                    else:
                        cur.execute("""
                            UPDATE wisata
                            SET nama = %s,
                                lokasi = %s,
                                negara = %s,
                                benua = %s,
                                deskripsi = %s,
                                foto = %s,
                                maps_url = %s,
                                rating = %s,
                                kategori = %s,
                                thumbnail_foto = %s,
                                moment_foto = %s,
                                foto_source_url = %s,
                                foto_source_label = %s,
                                best_time = %s,
                                display_order = %s,
                                is_active = %s
                            WHERE id = %s
                        """, (
                            destination_name,
                            location_label,
                            country_label,
                            REGION_CONFIG[region_slug]['label'],
                            description,
                            photo_url,
                            maps_url,
                            rating_value,
                            category_label,
                            thumbnail_url,
                            moment_url,
                            photo_source_url,
                            photo_source_label,
                            best_time,
                            display_order,
                            active_flag,
                            wisata_id
                        ))

                        if safe_int(current_row.get('destinasi_id')):
                            cur.execute("""
                                UPDATE destinasi
                                SET nama = %s,
                                    lokasi = %s,
                                    negara = %s,
                                    benua = %s,
                                    deskripsi = %s,
                                    foto = %s,
                                    maps_url = %s,
                                    rating = %s,
                                    tipe = %s,
                                    kategori = %s,
                                    thumbnail_foto = %s,
                                    moment_foto = %s,
                                    foto_source_url = %s,
                                    foto_source_label = %s,
                                    best_time = %s,
                                    display_order = %s,
                                    is_active = %s
                                WHERE id = %s
                            """, (
                                destination_name,
                                location_label,
                                country_label,
                                REGION_CONFIG[region_slug]['label'],
                                description,
                                photo_url,
                                maps_url,
                                rating_value,
                                destination_type,
                                category_label,
                                thumbnail_url,
                                moment_url,
                                photo_source_url,
                                photo_source_label,
                                best_time,
                                display_order,
                                active_flag,
                                current_row['destinasi_id']
                            ))
                        else:
                            cur.execute("""
                                INSERT INTO destinasi (
                                    nama, lokasi, negara, benua, deskripsi, foto, maps_url, rating, tipe, kategori,
                                    total_review, thumbnail_foto, moment_foto, foto_source_url, foto_source_label,
                                    best_time, display_order, is_active
                                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, %s, %s)
                            """, (
                                destination_name,
                                location_label,
                                country_label,
                                REGION_CONFIG[region_slug]['label'],
                                description,
                                photo_url,
                                maps_url,
                                rating_value,
                                destination_type,
                                category_label,
                                thumbnail_url,
                                moment_url,
                                photo_source_url,
                                photo_source_label,
                                best_time,
                                display_order,
                                active_flag
                            ))

                        db.commit()
                        flash('Detail destinasi berhasil diperbarui.', 'success')

            elif action == 'create_package':
                package_name = request.form.get('nama_paket', '').strip()
                package_code = (request.form.get('kode_paket', '') or '').strip().upper() or generate_package_code(current_row['nama'], package_name)
                package_kind = normalize_package_kind(request.form.get('jenis_paket'))
                package_status = normalize_package_status(request.form.get('status_paket'))
                package_desc = request.form.get('deskripsi_paket', '').strip()
                package_price = safe_int(request.form.get('harga'))
                package_duration = request.form.get('durasi', '').strip()
                facilities_text = request.form.get('fasilitas', '').strip()
                meeting_point = request.form.get('meeting_point', '').strip()
                departure_info = request.form.get('keberangkatan_info', '').strip()
                min_people = max(1, safe_int(request.form.get('min_orang'), 1))
                max_people = max(min_people, safe_int(request.form.get('max_orang'), min_people))
                quota_total = max(1, safe_int(request.form.get('kuota_total'), max_people))
                quota_available = min(quota_total, max(0, safe_int(request.form.get('kuota_tersedia'), quota_total)))
                is_featured = 1 if request.form.get('is_featured') == '1' else 0

                if not package_name or package_price <= 0 or not package_duration:
                    flash('Nama paket, harga, dan durasi wajib diisi untuk membuat paket baru.', 'error')
                else:
                    cur.execute("""
                        INSERT INTO tipe_paket (
                            wisata_id, kode_paket, nama_paket, jenis_paket, status_paket, deskripsi, harga,
                            durasi, fasilitas, min_orang, max_orang, meeting_point, keberangkatan_info,
                            kuota_total, kuota_tersedia, is_featured
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        wisata_id,
                        package_code[:80],
                        package_name,
                        package_kind,
                        package_status,
                        package_desc,
                        package_price,
                        package_duration,
                        facilities_text,
                        min_people,
                        max_people,
                        meeting_point,
                        departure_info,
                        quota_total,
                        quota_available,
                        is_featured
                    ))
                    db.commit()
                    flash('Paket keberangkatan baru berhasil ditambahkan.', 'success')

            elif action == 'update_package':
                package_id = safe_int(request.form.get('paket_id'))
                package_name = request.form.get('nama_paket', '').strip()
                package_code = (request.form.get('kode_paket', '') or '').strip().upper() or generate_package_code(current_row['nama'], package_name)
                package_kind = normalize_package_kind(request.form.get('jenis_paket'))
                package_status = normalize_package_status(request.form.get('status_paket'))
                package_desc = request.form.get('deskripsi_paket', '').strip()
                package_price = safe_int(request.form.get('harga'))
                package_duration = request.form.get('durasi', '').strip()
                facilities_text = request.form.get('fasilitas', '').strip()
                meeting_point = request.form.get('meeting_point', '').strip()
                departure_info = request.form.get('keberangkatan_info', '').strip()
                min_people = max(1, safe_int(request.form.get('min_orang'), 1))
                max_people = max(min_people, safe_int(request.form.get('max_orang'), min_people))
                quota_total = max(1, safe_int(request.form.get('kuota_total'), max_people))
                quota_available = min(quota_total, max(0, safe_int(request.form.get('kuota_tersedia'), quota_total)))
                is_featured = 1 if request.form.get('is_featured') == '1' else 0

                cur.execute("SELECT id FROM tipe_paket WHERE id = %s AND wisata_id = %s LIMIT 1", (package_id, wisata_id))
                package_row = cur.fetchone()
                if not package_row:
                    flash('Paket yang ingin diperbarui tidak ditemukan.', 'error')
                elif not package_name or package_price <= 0 or not package_duration:
                    flash('Nama paket, harga, dan durasi wajib diisi saat memperbarui paket.', 'error')
                else:
                    cur.execute("""
                        UPDATE tipe_paket
                        SET kode_paket = %s,
                            nama_paket = %s,
                            jenis_paket = %s,
                            status_paket = %s,
                            deskripsi = %s,
                            harga = %s,
                            durasi = %s,
                            fasilitas = %s,
                            min_orang = %s,
                            max_orang = %s,
                            meeting_point = %s,
                            keberangkatan_info = %s,
                            kuota_total = %s,
                            kuota_tersedia = %s,
                            is_featured = %s
                        WHERE id = %s
                    """, (
                        package_code[:80],
                        package_name,
                        package_kind,
                        package_status,
                        package_desc,
                        package_price,
                        package_duration,
                        facilities_text,
                        min_people,
                        max_people,
                        meeting_point,
                        departure_info,
                        quota_total,
                        quota_available,
                        is_featured,
                        package_id
                    ))
                    db.commit()
                    flash('Data keberangkatan paket berhasil diperbarui.', 'success')

            elif action == 'delete_package':
                package_id = safe_int(request.form.get('paket_id'))
                cur.execute("""
                    SELECT
                        tp.id,
                        COUNT(p.id) AS booking_total
                    FROM tipe_paket tp
                    LEFT JOIN pemesanan p ON p.paket_id = tp.id
                    WHERE tp.id = %s AND tp.wisata_id = %s
                    GROUP BY tp.id
                """, (package_id, wisata_id))
                package_row = cur.fetchone()
                if not package_row:
                    flash('Paket yang akan dihapus tidak ditemukan.', 'error')
                elif safe_int(package_row.get('booking_total')) > 0:
                    cur.execute("UPDATE tipe_paket SET status_paket = 'nonaktif' WHERE id = %s", (package_id,))
                    db.commit()
                    flash('Paket sudah pernah dibeli, jadi statusnya diarsipkan menjadi nonaktif agar histori tetap aman.', 'info')
                else:
                    cur.execute("DELETE FROM tipe_paket WHERE id = %s", (package_id,))
                    db.commit()
                    flash('Paket berhasil dihapus dari destinasi ini.', 'success')

            elif action == 'delete_destination':
                cur.execute("""
                    SELECT COUNT(p.id) AS booking_total
                    FROM tipe_paket tp
                    LEFT JOIN pemesanan p ON p.paket_id = tp.id
                    WHERE tp.wisata_id = %s
                """, (wisata_id,))
                booking_row = cur.fetchone() or {}
                booking_total = safe_int(booking_row.get('booking_total'))

                if booking_total > 0:
                    cur.execute("UPDATE wisata SET is_active = 0 WHERE id = %s", (wisata_id,))
                    if safe_int(current_row.get('destinasi_id')):
                        cur.execute("UPDATE destinasi SET is_active = 0 WHERE id = %s", (current_row['destinasi_id'],))
                    cur.execute("UPDATE tipe_paket SET status_paket = 'nonaktif' WHERE wisata_id = %s", (wisata_id,))
                    db.commit()
                    flash('Destinasi sudah punya histori pembelian, jadi diarsipkan menjadi nonaktif agar laporan tetap aman.', 'info')
                    cur.close()
                    db.close()
                    return redirect(url_for('backoffice_destinations'))

                if safe_int(current_row.get('destinasi_id')):
                    cur.execute("DELETE FROM destinasi WHERE id = %s", (current_row['destinasi_id'],))
                cur.execute("DELETE FROM tipe_paket WHERE wisata_id = %s", (wisata_id,))
                cur.execute("DELETE FROM wisata WHERE id = %s", (wisata_id,))
                db.commit()
                flash('Destinasi berhasil dihapus dari katalog internal.', 'success')
                cur.close()
                db.close()
                return redirect(url_for('backoffice_destinations'))

            else:
                flash('Aksi destinasi tidak dikenali.', 'error')

            cur.close()
            db.close()
            return redirect(url_for('backoffice_destination_detail', wisata_id=wisata_id))
        except Exception as error:
            print(f"Backoffice destination action error: {error}")
            flash(f'Terjadi kesalahan saat menyimpan destinasi atau paket: {error}', 'error')

    destination_row, package_rows = fetch_backoffice_destination_detail(wisata_id)
    return render_template(
        'backoffice/destination_detail.html',
        destination_row=destination_row,
        package_rows=package_rows,
        region_options=BACKOFFICE_REGION_OPTIONS,
        type_options=BACKOFFICE_DESTINATION_TYPES,
        category_options=BACKOFFICE_CATEGORY_OPTIONS,
        package_kind_options=BACKOFFICE_PACKAGE_KIND_OPTIONS,
        package_status_options=BACKOFFICE_PACKAGE_STATUS_OPTIONS
    )


@app.route('/backoffice/pesanan/<int:pemesanan_id>', methods=['GET', 'POST'])
@backoffice_login_required
def backoffice_order_detail(pemesanan_id):
    """Detailed operational workspace for a single booking."""
    if request.method == 'POST':
        action = request.form.get('action', '').strip()
        note_text = request.form.get('action_note', '').strip()
        current_staff = get_current_staff() or {}
        current_staff_name = current_staff.get('name', 'Staff')
        current_staff_id = get_current_staff_id()

        try:
            db = get_db()
            cur = db.cursor(dictionary=True)
            ensure_operational_order_record(cur, pemesanan_id)
            cur.execute("""
                SELECT
                    p.id,
                    p.status,
                    pb.id AS pembayaran_id,
                    pb.status_pembayaran,
                    op.assigned_staff_id,
                    op.status_operasional,
                    op.status_tiket,
                    op.status_voucher,
                    op.status_dokumen
                FROM pemesanan p
                LEFT JOIN pembayaran pb ON pb.pemesanan_id = p.id
                LEFT JOIN operasional_pesanan op ON op.pemesanan_id = p.id
                WHERE p.id = %s
                LIMIT 1
            """, (pemesanan_id,))
            state_row = cur.fetchone()

            if not state_row:
                cur.close()
                db.close()
                flash('Pesanan tidak ditemukan di backoffice.', 'error')
                return redirect(url_for('backoffice_orders'))

            if action == 'approve_payment':
                if not state_row.get('pembayaran_id'):
                    flash('Belum ada data pembayaran yang bisa diverifikasi.', 'error')
                elif (state_row.get('status_pembayaran') or '') == 'berhasil':
                    flash('Pembayaran ini sudah berstatus berhasil, jadi tidak perlu diverifikasi ulang.', 'info')
                else:
                    verified_note = note_text or 'Pembayaran diverifikasi oleh tim backoffice.'
                    now_value = datetime.now()
                    cur.execute("""
                        UPDATE pembayaran
                        SET status_pembayaran = 'berhasil',
                            gateway_status = %s,
                            verified_by_staff_id = %s,
                            verified_at = %s,
                            verification_note = %s,
                            tanggal_pembayaran = COALESCE(tanggal_pembayaran, %s)
                        WHERE pemesanan_id = %s
                    """, (
                        'verified_manual' if (state_row.get('status_pembayaran') or '') == 'menunggu_verifikasi' else 'verified_gateway',
                        current_staff_id,
                        now_value,
                        verified_note[:600],
                        now_value,
                        pemesanan_id
                    ))
                    cur.execute("UPDATE pemesanan SET status = 'confirmed' WHERE id = %s", (pemesanan_id,))
                    cur.execute("""
                        UPDATE operasional_pesanan
                        SET assigned_staff_id = COALESCE(assigned_staff_id, %s),
                            payment_checked_by = %s,
                            payment_checked_at = %s,
                            updated_at = %s
                        WHERE pemesanan_id = %s
                    """, (current_staff_id, current_staff_id, now_value, now_value, pemesanan_id))
                    sync_operational_status(cur, pemesanan_id, order_status='confirmed', payment_status='berhasil')
                    append_payment_audit_log(
                        cur,
                        state_row['pembayaran_id'],
                        pemesanan_id,
                        'Pembayaran disetujui',
                        verified_note[:700],
                        actor_type='staff',
                        actor_name=current_staff_name
                    )
                    append_order_status_log(
                        cur,
                        pemesanan_id,
                        'Pembayaran diverifikasi',
                        verified_note[:600],
                        actor_type='staff',
                        actor_name=current_staff_name
                    )
                    db.commit()
                    flash('Pembayaran berhasil diverifikasi dan pesanan masuk ke antrean penerbitan tiket.', 'success')

            elif action == 'reject_payment':
                if not state_row.get('pembayaran_id'):
                    flash('Belum ada pembayaran yang bisa ditolak.', 'error')
                else:
                    rejected_note = note_text or 'Pembayaran ditandai gagal. User perlu mengirim ulang pembayaran.'
                    now_value = datetime.now()
                    cur.execute("""
                        UPDATE pembayaran
                        SET status_pembayaran = 'gagal',
                            gateway_status = 'manual_rejected',
                            verified_by_staff_id = %s,
                            verified_at = %s,
                            verification_note = %s
                        WHERE pemesanan_id = %s
                    """, (current_staff_id, now_value, rejected_note[:600], pemesanan_id))
                    cur.execute("UPDATE pemesanan SET status = 'pending' WHERE id = %s", (pemesanan_id,))
                    cur.execute("""
                        UPDATE operasional_pesanan
                        SET payment_checked_by = %s,
                            payment_checked_at = %s,
                            updated_at = %s
                        WHERE pemesanan_id = %s
                    """, (current_staff_id, now_value, now_value, pemesanan_id))
                    sync_operational_status(cur, pemesanan_id, order_status='pending', payment_status='pending')
                    append_payment_audit_log(
                        cur,
                        state_row['pembayaran_id'],
                        pemesanan_id,
                        'Pembayaran ditolak',
                        rejected_note[:700],
                        actor_type='staff',
                        actor_name=current_staff_name
                    )
                    append_order_status_log(
                        cur,
                        pemesanan_id,
                        'Pembayaran ditolak',
                        rejected_note[:600],
                        actor_type='staff',
                        actor_name=current_staff_name
                    )
                    db.commit()
                    flash('Pembayaran ditandai gagal dan user perlu melakukan pembayaran ulang.', 'success')

            elif action == 'save_operational':
                available_staff = fetch_backoffice_staff_members()
                allowed_staff_ids = {safe_int(item['id']) for item in available_staff}
                assigned_staff_id = safe_int(request.form.get('assigned_staff_id')) or None
                if assigned_staff_id and assigned_staff_id not in allowed_staff_ids:
                    assigned_staff_id = None

                status_operasional = (request.form.get('status_operasional') or '').strip().lower()
                status_tiket = (request.form.get('status_tiket') or '').strip().lower()
                status_voucher = (request.form.get('status_voucher') or '').strip().lower()
                status_dokumen = (request.form.get('status_dokumen') or '').strip().lower()
                deadline_follow_up = request.form.get('deadline_follow_up', '').strip() or None
                catatan_internal = request.form.get('catatan_internal', '').strip()

                if status_operasional not in BACKOFFICE_OPERATIONAL_STATUS_OPTIONS:
                    flash('Status operasional tidak valid.', 'error')
                elif status_tiket not in BACKOFFICE_TICKET_STATUS_OPTIONS:
                    flash('Status tiket tidak valid.', 'error')
                elif status_voucher not in BACKOFFICE_VOUCHER_STATUS_OPTIONS:
                    flash('Status voucher tidak valid.', 'error')
                elif status_dokumen not in BACKOFFICE_DOCUMENT_STATUS_OPTIONS:
                    flash('Status dokumen tidak valid.', 'error')
                else:
                    now_value = datetime.now()
                    cur.execute("""
                        UPDATE operasional_pesanan
                        SET assigned_staff_id = %s,
                            status_operasional = %s,
                            status_tiket = %s,
                            status_voucher = %s,
                            status_dokumen = %s,
                            deadline_follow_up = %s,
                            catatan_internal = %s,
                            updated_at = %s
                        WHERE pemesanan_id = %s
                    """, (
                        assigned_staff_id,
                        status_operasional,
                        status_tiket,
                        status_voucher,
                        status_dokumen,
                        deadline_follow_up,
                        catatan_internal[:3000],
                        now_value,
                        pemesanan_id
                    ))

                    if status_operasional == 'selesai':
                        cur.execute("UPDATE pemesanan SET status = 'completed' WHERE id = %s", (pemesanan_id,))
                    elif status_operasional == 'dibatalkan':
                        cur.execute("UPDATE pemesanan SET status = 'cancelled' WHERE id = %s", (pemesanan_id,))
                    elif (state_row.get('status_pembayaran') or '') == 'berhasil':
                        cur.execute("UPDATE pemesanan SET status = 'confirmed' WHERE id = %s", (pemesanan_id,))
                    else:
                        cur.execute("UPDATE pemesanan SET status = 'pending' WHERE id = %s", (pemesanan_id,))

                    append_order_status_log(
                        cur,
                        pemesanan_id,
                        'Catatan operasional diperbarui',
                        note_text[:600] or 'Status operasional, tiket, voucher, atau dokumen diperbarui dari dashboard.',
                        actor_type='staff',
                        actor_name=current_staff_name
                    )
                    db.commit()
                    flash('Data operasional pesanan berhasil diperbarui.', 'success')

            elif action == 'complete_order':
                now_value = datetime.now()
                cur.execute("UPDATE pemesanan SET status = 'completed' WHERE id = %s", (pemesanan_id,))
                cur.execute("""
                    UPDATE operasional_pesanan
                    SET assigned_staff_id = COALESCE(assigned_staff_id, %s),
                        status_operasional = 'selesai',
                        status_tiket = 'terbit',
                        status_voucher = 'terkirim',
                        updated_at = %s
                    WHERE pemesanan_id = %s
                """, (current_staff_id, now_value, pemesanan_id))
                append_order_status_log(
                    cur,
                    pemesanan_id,
                    'Pesanan diselesaikan',
                    note_text[:600] or 'Tim backoffice menandai pesanan ini selesai.',
                    actor_type='staff',
                    actor_name=current_staff_name
                )
                db.commit()
                flash('Pesanan ditandai selesai.', 'success')

            else:
                flash('Aksi backoffice belum dikenali.', 'error')

            cur.close()
            db.close()
            return redirect(url_for('backoffice_order_detail', pemesanan_id=pemesanan_id))
        except Exception as error:
            print(f"Backoffice order action error: {error}")
            flash(f'Terjadi kesalahan saat memproses aksi: {error}', 'error')

    order_row, payment_details, payment_audit_rows, status_logs, participant_rows = fetch_backoffice_order_detail(pemesanan_id)
    if not order_row:
        flash('Pesanan tidak ditemukan di backoffice.', 'error')
        return redirect(url_for('backoffice_orders'))

    return render_template(
        'backoffice/order_detail.html',
        order_row=order_row,
        payment_details=payment_details,
        payment_audit_rows=payment_audit_rows,
        status_logs=status_logs,
        participant_rows=participant_rows,
        available_staff=fetch_backoffice_staff_members(),
        operational_options=BACKOFFICE_OPERATIONAL_STATUS_OPTIONS,
        ticket_options=BACKOFFICE_TICKET_STATUS_OPTIONS,
        voucher_options=BACKOFFICE_VOUCHER_STATUS_OPTIONS,
        document_options=BACKOFFICE_DOCUMENT_STATUS_OPTIONS,
        operational_meta=BACKOFFICE_OPERATIONAL_META,
        payment_meta=BACKOFFICE_PAYMENT_META,
        ticket_meta=BACKOFFICE_TICKET_META,
        voucher_meta=BACKOFFICE_VOUCHER_META,
        document_meta=BACKOFFICE_DOCUMENT_META,
        payment_detail_map=payment_details_rows_to_map(payment_details)
    )

# ════════════════════════════════════════
# HOMEPAGE & DESTINASI ROUTES
# ════════════════════════════════════════

@app.route('/')
def index():
    """Homepage with curated region and trip sections."""
    wisata = []
    featured_trips = []
    region_cards = []
    globe_country_targets = []

    try:
        if midtrans_is_configured():
            db = get_db()
            cur = db.cursor(dictionary=True)
            cur.execute("""
                SELECT pb.pemesanan_id
                FROM pembayaran pb
                JOIN pemesanan p ON p.id = pb.pemesanan_id
                WHERE LOWER(p.email) = %s
                  AND pb.gateway_provider = 'midtrans'
                  AND pb.status_pembayaran = 'pending'
            """, (get_current_user_email(),))
            pending_gateway_rows = cur.fetchall()
            cur.close()
            db.close()

            for gateway_row in pending_gateway_rows:
                try:
                    sync_midtrans_payment_for_booking(gateway_row['pemesanan_id'])
                except Exception as gateway_error:
                    print(f"Status sync warning: {gateway_error}")

        db = get_db()
        cur = db.cursor(dictionary=True)

        cur.execute("""
            SELECT
                w.id,
                w.nama,
                w.lokasi,
                w.negara,
                w.benua,
                w.kategori,
                w.deskripsi,
                w.foto,
                w.thumbnail_foto,
                w.moment_foto,
                w.foto_source_url,
                w.foto_source_label,
                w.best_time,
                w.rating,
                w.display_order,
                d.tipe,
                MIN(tp.harga) AS min_harga,
                SUBSTRING_INDEX(
                    GROUP_CONCAT(tp.durasi ORDER BY tp.harga ASC SEPARATOR '||'),
                    '||',
                    1
                ) AS paket_durasi,
                COUNT(tp.id) AS paket_count
            FROM wisata w
            LEFT JOIN destinasi d ON d.nama = w.nama
            LEFT JOIN tipe_paket tp ON tp.wisata_id = w.id
            GROUP BY
                w.id,
                w.nama,
                w.lokasi,
                w.negara,
                w.benua,
                w.kategori,
                w.deskripsi,
                w.foto,
                w.thumbnail_foto,
                w.moment_foto,
                w.foto_source_url,
                w.foto_source_label,
                w.best_time,
                w.rating,
                w.display_order,
                d.tipe
            ORDER BY COALESCE(w.display_order, 9999) ASC, w.rating DESC, w.id ASC
        """)
        wisata = apply_destination_media_list(cur.fetchall())
        featured_trips = build_featured_trips(wisata)
        region_cards = build_region_cards(wisata)
        globe_country_targets = build_globe_country_targets(wisata)
        cur.close()
        db.close()
    except Exception as e:
        print(f"Index error: {e}")
        wisata = []
        featured_trips = []
        region_cards = []
        globe_country_targets = []

    return render_template(
        'index.html',
        wisata=wisata,
        featured_trips=featured_trips,
        region_cards=region_cards,
        globe_country_targets=globe_country_targets,
        globe_supported_country_names=[item['db_name'] for item in globe_country_targets]
    )
@app.route('/promo')
def promo():
    """Public promo page showing destinations with active discounts."""
    promo_rows = []
    db_error = False

    try:
        db = get_db()
        cur = db.cursor(dictionary=True)
        cur.execute("""
            SELECT
                w.*,
                d.tipe,
                MIN(tp.harga) AS min_harga,
                COUNT(DISTINCT tp.id) AS paket_count
            FROM wisata w
            LEFT JOIN destinasi d ON d.nama = w.nama
            LEFT JOIN tipe_paket tp ON tp.wisata_id = w.id
            WHERE EXISTS (
                SELECT 1
                FROM promo_destinasi pr
                WHERE pr.wisata_id = w.id
                  AND pr.is_active = 1
                  AND pr.starts_at <= NOW()
                  AND pr.ends_at >= NOW()
            )
              AND COALESCE(w.is_active, 1) = 1
            GROUP BY w.id, d.tipe
            ORDER BY COALESCE(w.display_order, 9999) ASC, w.rating DESC, w.id ASC
        """)
        promo_rows = apply_destination_media_list(cur.fetchall())
        promo_rows = attach_promo_metadata_to_destinations(cur, promo_rows)
        promo_rows = [row for row in promo_rows if row.get('has_active_promo')]
        cur.close()
        db.close()
    except Exception as error:
        print(f"Promo page error: {error}")
        db_error = True

    return render_template(
        'promo.html',
        promo_rows=promo_rows,
        db_error=db_error
    )


@app.route('/destinasi')
def destinasi():
    """Destinasi page with continent and country filters."""
    wisata = []
    available_country_filters = []
    db_error = False
    tipe = request.args.get('tipe', '').strip().lower()
    kategori = request.args.get('kategori', '').strip()
    negara = request.args.get('negara', '').strip()
    benua = request.args.get('benua', '').strip().lower()

    if kategori.lower() == 'internasional' and not tipe and not negara:
        tipe = 'internasional'
        kategori = ''

    try:
        db = get_db()
        cur = db.cursor(dictionary=True)

        base_query = """
            SELECT w.*, d.tipe
            FROM wisata w
            LEFT JOIN destinasi d ON d.nama = w.nama
        """
        base_conditions = []
        base_params = []

        if tipe in ['lokal', 'internasional']:
            base_conditions.append("d.tipe = %s")
            base_params.append(tipe)

        if kategori:
            base_conditions.append("w.kategori = %s")
            base_params.append(kategori)

        append_region_condition(base_conditions, base_params, benua)

        if benua in REGION_CONFIG:
            country_query = base_query
            if base_conditions:
                country_query += " WHERE " + " AND ".join(base_conditions)
            country_query += " ORDER BY COALESCE(w.display_order, 9999) ASC, w.rating DESC, w.id ASC"
            cur.execute(country_query, list(base_params))
            available_country_filters = build_country_filters(benua, cur.fetchall())

        conditions = list(base_conditions)
        params = list(base_params)
        append_country_condition(conditions, params, negara)

        final_query = base_query
        if conditions:
            final_query += " WHERE " + " AND ".join(conditions)
        final_query += " ORDER BY COALESCE(w.display_order, 9999) ASC, w.rating DESC, w.id ASC"

        cur.execute(final_query, params)
        wisata = apply_destination_media_list(cur.fetchall())
        wisata = attach_promo_metadata_to_destinations(cur, wisata)
        cur.close()
        db.close()
    except Exception as e:
        print(f"Destinasi error: {e}")
        wisata = []
        db_error = True

    return render_template(
        'destinasi.html',
        wisata=wisata,
        db_error=db_error,
        current_tipe=tipe,
        current_kategori=kategori,
        current_negara=negara,
        current_benua=benua,
        current_region_label=REGION_CONFIG.get(benua, {}).get('label', ''),
        available_country_filters=available_country_filters
    )


@app.route('/paket-wisata')
def paket_wisata():
    """Package catalog page grouped by package type and continent."""
    package_type_slug = request.args.get('jenis', 'solo').strip().lower()
    benua = request.args.get('benua', '').strip().lower()
    negara = request.args.get('negara', '').strip()
    db_error = False
    available_country_filters = []
    package_cards = []

    if package_type_slug not in PACKAGE_TYPE_CONFIG:
        package_type_slug = 'solo'

    try:
        db = get_db()
        cur = db.cursor(dictionary=True)

        base_query = """
            SELECT
                w.id,
                w.nama,
                w.lokasi,
                w.negara,
                w.benua,
                w.kategori,
                w.deskripsi,
                w.foto,
                w.thumbnail_foto,
                w.moment_foto,
                w.foto_source_url,
                w.foto_source_label,
                w.best_time,
                w.rating,
                w.display_order,
                d.tipe,
                MIN(tp.harga) AS min_harga,
                SUBSTRING_INDEX(
                    GROUP_CONCAT(tp.durasi ORDER BY tp.harga ASC SEPARATOR '||'),
                    '||',
                    1
                ) AS paket_durasi,
                COUNT(tp.id) AS paket_count
            FROM wisata w
            LEFT JOIN destinasi d ON d.nama = w.nama
            LEFT JOIN tipe_paket tp ON tp.wisata_id = w.id
        """

        group_by = """
            GROUP BY
                w.id,
                w.nama,
                w.lokasi,
                w.negara,
                w.benua,
                w.kategori,
                w.deskripsi,
                w.foto,
                w.thumbnail_foto,
                w.moment_foto,
                w.foto_source_url,
                w.foto_source_label,
                w.best_time,
                w.rating,
                w.display_order,
                d.tipe
        """

        base_conditions = []
        base_params = []
        append_region_condition(base_conditions, base_params, benua)

        if benua in REGION_CONFIG:
            country_query = base_query
            if base_conditions:
                country_query += " WHERE " + " AND ".join(base_conditions)
            country_query += " " + group_by + " ORDER BY COALESCE(w.display_order, 9999) ASC, w.rating DESC, w.id ASC"
            cur.execute(country_query, list(base_params))
            available_country_filters = build_country_filters(benua, cur.fetchall())

        conditions = list(base_conditions)
        params = list(base_params)
        append_country_condition(conditions, params, negara)

        final_query = base_query
        if conditions:
            final_query += " WHERE " + " AND ".join(conditions)
        final_query += " " + group_by + " ORDER BY COALESCE(w.display_order, 9999) ASC, w.rating DESC, w.id ASC"

        cur.execute(final_query, params)
        package_rows = apply_destination_media_list(cur.fetchall())
        package_rows = attach_promo_metadata_to_destinations(cur, package_rows)
        package_cards = build_package_catalog(package_rows, package_type_slug)

        cur.close()
        db.close()
    except Exception as e:
        print(f"Paket wisata error: {e}")
        db_error = True

    return render_template(
        'paket_wisata.html',
        package_cards=package_cards,
        package_type=PACKAGE_TYPE_CONFIG[package_type_slug],
        current_package_type=package_type_slug,
        current_benua=benua,
        current_negara=negara,
        current_region_label=REGION_CONFIG.get(benua, {}).get('label', ''),
        available_country_filters=available_country_filters,
        db_error=db_error
    )

@app.route('/wisata/<int:id>')
def detail_wisata(id):
    """Detail wisata page"""
    wisata = None
    paket = []
    reviews = []
    story = None
    
    try:
        db = get_db()
        cur = db.cursor(dictionary=True)
        
        # Get wisata data
        cur.execute("""
            SELECT w.*, d.tipe
            FROM wisata w
            LEFT JOIN destinasi d ON d.nama = w.nama
            WHERE w.id = %s
        """, (id,))
        wisata = apply_destination_media(cur.fetchone())
        if wisata:
            attach_promo_metadata_to_destinations(cur, [wisata])
        
        # Get paket
        if wisata:
            cur.execute("SELECT * FROM tipe_paket WHERE wisata_id = %s", (id,))
            paket = cur.fetchall()
            active_promo = wisata.get('active_promo')
            for package_row in paket:
                apply_promo_to_package_row(package_row, active_promo)
            story = get_destination_story_meta(wisata)
            
            # Get reviews
            cur.execute("""
                SELECT rr.* FROM rating_review rr
                JOIN wisata w ON rr.destinasi_id = w.id
                WHERE w.id = %s AND rr.status_review = 'published'
                ORDER BY rr.tanggal_publish DESC
                LIMIT 5
            """, (id,))
            reviews = cur.fetchall()
        
        cur.close()
        db.close()
    except Exception as e:
        print(f"Detail wisata error: {e}")
    
    return render_template('detail.html', wisata=wisata, paket=paket, reviews=reviews, story=story)

# ════════════════════════════════════════
# BOOKING ROUTES
# ════════════════════════════════════════

@app.route('/pesan/<int:paket_id>', methods=['GET', 'POST'])
def pesan(paket_id):
    """Booking form"""
    if not get_current_user():
        return redirect_to_login(
            message='Silakan login terlebih dahulu sebelum melakukan pemesanan paket.',
            next_url=url_for('pesan', paket_id=paket_id)
        )

    paket = None
    wisata_id = None
    current_user = get_current_user() or {}
    
    try:
        db = get_db()
        cur = db.cursor(dictionary=True)
        cur.execute("""
            SELECT tp.*, w.nama as wisata_nama, w.lokasi, w.foto, w.id as wisata_id
            FROM tipe_paket tp
            JOIN wisata w ON tp.wisata_id = w.id
            WHERE tp.id = %s
        """, (paket_id,))
        paket = cur.fetchone()

        if paket:
            wisata_id = paket['wisata_id']
            promo_map = fetch_promos_for_wisata_ids(cur, [wisata_id])
            active_promo = pick_current_active_promo(promo_map.get(wisata_id, []))
            apply_promo_to_package_row(paket, active_promo)
            media = get_destination_media(paket.get('wisata_nama'))
            if not (paket.get('foto') or '').strip() and media.get('image'):
                paket['foto'] = media['image']

        cur.close()
        db.close()
    except Exception as e:
        print(f"Pesan GET error: {e}")

    if request.method == 'POST' and paket:
        try:
            db = get_db()
            cur = db.cursor()
            
            nama_pemesan = request.form.get('nama_pemesan', '').strip() or current_user.get('name', '')
            email = current_user.get('email', '').strip()
            telepon = request.form.get('telepon', '').strip()
            tanggal_pergi = request.form.get('tanggal_pergi', '')
            jumlah_orang = int(request.form.get('jumlah_orang', 1))
            catatan = request.form.get('catatan', '').strip()
            
            # Validate
            if not all([nama_pemesan, email, telepon, tanggal_pergi]):
                flash('Semua field harus diisi!', 'error')
                cur.close()
                db.close()
                return render_template('pesan.html', paket=paket)
            
            harga_satuan_awal = safe_int(paket.get('display_original_price') or paket['harga'])
            harga_satuan_final = safe_int(paket.get('display_discounted_price') or paket['harga'])
            total_diskon = max(0, (harga_satuan_awal - harga_satuan_final) * jumlah_orang)
            total_harga = harga_satuan_final * jumlah_orang
            promo_row = paket.get('active_promo') or {}
            promo_snapshot_title = promo_row.get('promo_name') if paket.get('has_active_promo') else None
            promo_snapshot_value = promo_row.get('badge_text') if paket.get('has_active_promo') else None
            promo_id = safe_int(promo_row.get('id')) or None
            
            # Insert booking
            cur.execute("""
                INSERT INTO pemesanan
                  (paket_id, nama_pemesan, email, telepon, tanggal_pergi,
                   jumlah_orang, total_harga, harga_awal, total_diskon, promo_id,
                   promo_snapshot_title, promo_snapshot_value, tanggal_pesan, status, catatan, sumber_pesanan)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'pending',%s,'website')
            """, (
                paket_id,
                nama_pemesan,
                email,
                telepon,
                tanggal_pergi,
                jumlah_orang,
                total_harga,
                harga_satuan_awal * jumlah_orang,
                total_diskon,
                promo_id,
                promo_snapshot_title,
                promo_snapshot_value,
                datetime.now(),
                catatan
            ))
            
            pemesanan_id = cur.lastrowid
            booking_code = build_booking_code(pemesanan_id)
            if column_exists(cur, 'pemesanan', 'kode_pemesanan'):
                cur.execute("UPDATE pemesanan SET kode_pemesanan = %s WHERE id = %s", (booking_code, pemesanan_id))
            ensure_operational_order_record(cur, pemesanan_id)
            sync_operational_status(cur, pemesanan_id, order_status='pending', payment_status='pending')
            append_order_status_log(
                cur,
                pemesanan_id,
                'Pesanan baru masuk',
                'Pesanan dibuat dari aplikasi utama dan menunggu pembayaran.',
                actor_type='customer',
                actor_name=nama_pemesan
            )

            db.commit()
            
            cur.close()
            db.close()
            
            flash('Pemesanan berhasil! Lanjut ke pembayaran.', 'success')
            return redirect(url_for('pembayaran', pemesanan_id=pemesanan_id))
        
        except Exception as e:
            print(f"Pesan POST error: {e}")
            flash(f'Terjadi kesalahan: {str(e)}', 'error')

    return render_template('pesan.html', paket=paket, logged_user=current_user)

# ════════════════════════════════════════
# PAYMENT ROUTES (NEW!)
# ════════════════════════════════════════

@app.route('/pembayaran/<int:pemesanan_id>', methods=['GET', 'POST'])
def pembayaran(pemesanan_id):
    """Payment page with Midtrans or manual fallback."""
    if not get_current_user():
        return redirect_to_login(
            message='Login diperlukan untuk membuka pembayaran pesanan Anda.',
            next_url=url_for('pembayaran', pemesanan_id=pemesanan_id)
        )

    pemesanan = None
    pembayaran = None
    payment_detail_rows = []
    payment_detail_map = {}
    launch_snap = request.args.get('launch') == '1'

    try:
        if midtrans_is_configured():
            sync_midtrans_payment_for_booking(pemesanan_id)

        db = get_db()
        cur = db.cursor(dictionary=True)

        cur.execute("""
            SELECT p.*, tp.nama_paket, tp.harga, w.nama as wisata_nama, w.foto
            FROM pemesanan p
            JOIN tipe_paket tp ON p.paket_id = tp.id
            JOIN wisata w ON tp.wisata_id = w.id
            WHERE p.id = %s
        """, (pemesanan_id,))
        pemesanan = apply_destination_media(cur.fetchone())

        if pemesanan:
            cur.execute("SELECT * FROM pembayaran WHERE pemesanan_id = %s", (pemesanan_id,))
            pembayaran = cur.fetchone()
            if pembayaran:
                cur.execute("SELECT * FROM payment_detail WHERE pembayaran_id = %s ORDER BY id ASC", (pembayaran['id'],))
                payment_detail_rows = cur.fetchall()
                payment_detail_map = payment_details_rows_to_map(payment_detail_rows)

        cur.close()
        db.close()
    except Exception as e:
        print(f"Pembayaran GET error: {e}")

    if not pemesanan:
        flash('Data pemesanan tidak ditemukan.', 'error')
        return redirect(url_for('status_pesanan'))

    if not user_owns_booking(pemesanan.get('email')):
        flash('Pesanan ini tidak terhubung dengan akun yang sedang login.', 'error')
        return redirect(url_for('status_pesanan'))

    if pembayaran and pembayaran.get('status_pembayaran') == 'berhasil':
        flash('Pembayaran untuk pesanan ini sudah berhasil.', 'info')
        return redirect(url_for('konfirmasi_pembayaran', pemesanan_id=pemesanan_id))

    demo_qris_enabled = payment_demo_enabled() and not midtrans_is_configured()

    if request.method == 'POST' and pemesanan:
        try:
            metode_pembayaran = request.form.get('metode_pembayaran', 'bank_transfer')
            payment_reference = request.form.get('payment_reference', '').strip()
            keterangan = request.form.get('keterangan', '').strip()

            if metode_pembayaran not in PAYMENT_METHOD_CONFIG:
                flash('Metode pembayaran tidak valid.', 'error')
                return redirect(url_for('pembayaran', pemesanan_id=pemesanan_id))

            selected_method = PAYMENT_METHOD_CONFIG[metode_pembayaran]
            use_gateway = midtrans_is_configured() and selected_method.get('supports_gateway')
            use_demo_qris = demo_qris_enabled and metode_pembayaran == 'qris'

            if use_gateway:
                response_payload = create_midtrans_transaction_for_booking(pemesanan, metode_pembayaran)
                detail_map = extract_midtrans_detail_map(response_payload)
                detail_map['redirect_url'] = response_payload.get('redirect_url', '')
                detail_map['snap_token'] = response_payload.get('token', '')
                detail_map['payment_label'] = selected_method['label']

                db = get_db()
                cur = db.cursor(dictionary=True)
                cur.execute("SELECT id FROM pembayaran WHERE pemesanan_id = %s LIMIT 1", (pemesanan_id,))
                existing_payment = cur.fetchone()
                timestamp_now = datetime.now()

                if existing_payment:
                    pembayaran_id = existing_payment['id']
                    cur.execute("""
                        UPDATE pembayaran
                        SET metode_pembayaran = %s,
                            status_pembayaran = 'pending',
                            jumlah_dibayar = %s,
                            keterangan = %s,
                            gateway_provider = 'midtrans',
                            gateway_order_id = %s,
                            gateway_status = 'pending',
                            snap_token = %s,
                            redirect_url = %s,
                            channel_code = %s,
                            payment_reference = NULL,
                            paid_at = NULL,
                            raw_response_json = %s,
                            tanggal_pembayaran = NULL
                        WHERE id = %s
                    """, (
                        metode_pembayaran,
                        pemesanan['total_harga'],
                        keterangan,
                        response_payload['gateway_order_id'],
                        response_payload.get('token', ''),
                        response_payload.get('redirect_url', ''),
                        metode_pembayaran,
                        json.dumps(response_payload),
                        pembayaran_id
                    ))
                else:
                    cur.execute("""
                        INSERT INTO pembayaran (
                            pemesanan_id, metode_pembayaran, status_pembayaran, tanggal_pembayaran,
                            jumlah_dibayar, keterangan, created_at, gateway_provider, gateway_order_id,
                            gateway_status, snap_token, redirect_url, channel_code, raw_response_json
                        ) VALUES (%s, %s, 'pending', NULL, %s, %s, %s, 'midtrans', %s, 'pending', %s, %s, %s, %s)
                    """, (
                        pemesanan_id,
                        metode_pembayaran,
                        pemesanan['total_harga'],
                        keterangan,
                        timestamp_now,
                        response_payload['gateway_order_id'],
                        response_payload.get('token', ''),
                        response_payload.get('redirect_url', ''),
                        metode_pembayaran,
                        json.dumps(response_payload)
                    ))
                    pembayaran_id = cur.lastrowid

                replace_payment_details(cur, pembayaran_id, detail_map)
                append_payment_audit_log(
                    cur,
                    pembayaran_id,
                    pemesanan_id,
                    'Transaksi gateway dibuat',
                    f"User memilih {selected_method['label']} dan sistem membuat transaksi Midtrans dengan order ID {response_payload['gateway_order_id']}.",
                    actor_type='customer',
                    actor_name=pemesanan.get('nama_pemesan') or 'Customer'
                )
                ensure_operational_order_record(cur, pemesanan_id)
                sync_operational_status(cur, pemesanan_id, order_status='pending', payment_status='pending')
                append_order_status_log(
                    cur,
                    pemesanan_id,
                    'Transaksi gateway dibuat',
                    f"Transaksi pembayaran dibuat dengan metode {selected_method['label']} dan siap dibayar user.",
                    actor_type='system',
                    actor_name='Payment Gateway'
                )
                db.commit()
                cur.close()
                db.close()

                flash('Transaksi pembayaran berhasil dibuat. Lanjutkan ke jendela pembayaran aman.', 'success')
                return redirect(url_for('pembayaran', pemesanan_id=pemesanan_id, launch='1'))

            if use_demo_qris:
                response_payload = create_demo_qris_transaction_for_booking(pemesanan, metode_pembayaran)
                detail_map = response_payload['detail_map']

                db = get_db()
                cur = db.cursor(dictionary=True)
                cur.execute("SELECT id FROM pembayaran WHERE pemesanan_id = %s LIMIT 1", (pemesanan_id,))
                existing_payment = cur.fetchone()
                timestamp_now = datetime.now()

                if existing_payment:
                    pembayaran_id = existing_payment['id']
                    cur.execute("""
                        UPDATE pembayaran
                        SET metode_pembayaran = %s,
                            status_pembayaran = 'pending',
                            tanggal_pembayaran = NULL,
                            jumlah_dibayar = %s,
                            keterangan = %s,
                            gateway_provider = 'demo_qris',
                            gateway_order_id = %s,
                            gateway_transaction_id = NULL,
                            gateway_status = 'pending_demo',
                            snap_token = NULL,
                            redirect_url = NULL,
                            channel_code = 'qris_demo',
                            payment_reference = %s,
                            paid_at = NULL,
                            raw_response_json = %s
                        WHERE id = %s
                    """, (
                        metode_pembayaran,
                        pemesanan['total_harga'],
                        keterangan,
                        response_payload['gateway_order_id'],
                        response_payload['payment_reference'],
                        json.dumps(response_payload['raw_payload']),
                        pembayaran_id
                    ))
                else:
                    cur.execute("""
                        INSERT INTO pembayaran (
                            pemesanan_id, metode_pembayaran, status_pembayaran, tanggal_pembayaran,
                            jumlah_dibayar, keterangan, created_at, gateway_provider, gateway_order_id,
                            gateway_status, snap_token, redirect_url, channel_code, payment_reference, raw_response_json
                        ) VALUES (%s, %s, 'pending', NULL, %s, %s, %s, 'demo_qris', %s, 'pending_demo', NULL, NULL, 'qris_demo', %s, %s)
                    """, (
                        pemesanan_id,
                        metode_pembayaran,
                        pemesanan['total_harga'],
                        keterangan,
                        timestamp_now,
                        response_payload['gateway_order_id'],
                        response_payload['payment_reference'],
                        json.dumps(response_payload['raw_payload'])
                    ))
                    pembayaran_id = cur.lastrowid

                replace_payment_details(cur, pembayaran_id, detail_map)
                append_payment_audit_log(
                    cur,
                    pembayaran_id,
                    pemesanan_id,
                    'QRIS demo dibuat',
                    f"User memilih QRIS dan sistem membuat QRIS simulasi untuk kebutuhan presentasi dengan referensi {response_payload['payment_reference']}.",
                    actor_type='customer',
                    actor_name=pemesanan.get('nama_pemesan') or 'Customer'
                )
                ensure_operational_order_record(cur, pemesanan_id)
                sync_operational_status(cur, pemesanan_id, order_status='pending', payment_status='pending')
                append_order_status_log(
                    cur,
                    pemesanan_id,
                    'QRIS demo dibuat',
                    'Transaksi QRIS simulasi sudah siap ditampilkan untuk presentasi dan pengujian akademik.',
                    actor_type='system',
                    actor_name='Demo Payment'
                )
                db.commit()
                cur.close()
                db.close()

                flash('QRIS demo akademik berhasil dibuat. Lanjutkan ke halaman konfirmasi untuk menampilkan kode dan mensimulasikan pembayaran.', 'success')
                return redirect(url_for('konfirmasi_pembayaran', pemesanan_id=pemesanan_id))

            manual_qris_image = get_manual_qris_image()
            if metode_pembayaran == 'qris' and not manual_qris_image:
                flash('QRIS manual belum diisi. Tambahkan gambar QRIS perusahaan di company_payment_config.py atau .env.', 'error')
                return redirect(url_for('pembayaran', pemesanan_id=pemesanan_id))

            db = get_db()
            cur = db.cursor(dictionary=True)
            cur.execute("SELECT id FROM pembayaran WHERE pemesanan_id = %s LIMIT 1", (pemesanan_id,))
            existing_payment = cur.fetchone()
            timestamp_now = datetime.now()
            destination_meta = get_payment_destination(metode_pembayaran)
            detail_map = {
                'manual_method': metode_pembayaran,
                'manual_reference': payment_reference,
                'manual_note': keterangan,
                'manual_qris_image': manual_qris_image if metode_pembayaran == 'qris' else '',
                'payment_label': selected_method['label'],
                'destination_type': destination_meta.get('type', ''),
                'destination_json': json.dumps(destination_meta)
            }

            if destination_meta.get('type') == 'ewallet' and destination_meta.get('item'):
                detail_map['wallet_label'] = destination_meta['item']['label']
                detail_map['wallet_account_name'] = destination_meta['item']['account_name']
                detail_map['wallet_account_number'] = destination_meta['item']['account_number']
            elif destination_meta.get('type') == 'qris' and destination_meta.get('item'):
                detail_map['qris_merchant_name'] = destination_meta['item']['merchant_name']
            elif destination_meta.get('type') == 'bank':
                detail_map['bank_total_accounts'] = str(len(destination_meta.get('items', [])))

            if existing_payment:
                pembayaran_id = existing_payment['id']
                cur.execute("""
                    UPDATE pembayaran
                    SET metode_pembayaran = %s,
                        status_pembayaran = 'menunggu_verifikasi',
                        tanggal_pembayaran = %s,
                        jumlah_dibayar = %s,
                        keterangan = %s,
                        gateway_provider = 'manual',
                        gateway_order_id = NULL,
                        gateway_status = 'manual_submitted',
                        snap_token = NULL,
                        redirect_url = NULL,
                        channel_code = %s,
                        payment_reference = %s,
                        paid_at = NULL,
                        raw_response_json = %s
                    WHERE id = %s
                """, (
                    metode_pembayaran,
                    timestamp_now,
                    pemesanan['total_harga'],
                    keterangan,
                    metode_pembayaran,
                    payment_reference,
                    json.dumps(detail_map),
                    pembayaran_id
                ))
            else:
                cur.execute("""
                    INSERT INTO pembayaran (
                        pemesanan_id, metode_pembayaran, status_pembayaran, tanggal_pembayaran,
                        jumlah_dibayar, keterangan, created_at, gateway_provider, gateway_status,
                        channel_code, payment_reference, raw_response_json
                    ) VALUES (%s, %s, 'menunggu_verifikasi', %s, %s, %s, %s, 'manual', 'manual_submitted', %s, %s, %s)
                """, (
                    pemesanan_id,
                    metode_pembayaran,
                    timestamp_now,
                    pemesanan['total_harga'],
                    keterangan,
                    timestamp_now,
                    metode_pembayaran,
                    payment_reference,
                    json.dumps(detail_map)
                ))
                pembayaran_id = cur.lastrowid

            replace_payment_details(cur, pembayaran_id, detail_map)
            append_payment_audit_log(
                cur,
                pembayaran_id,
                pemesanan_id,
                'Konfirmasi pembayaran manual',
                f"User mengirim pembayaran melalui {selected_method['label']} dengan referensi {payment_reference or 'tanpa referensi'}.",
                actor_type='customer',
                actor_name=pemesanan.get('nama_pemesan') or 'Customer'
            )
            cur.execute("UPDATE pemesanan SET status = 'pending' WHERE id = %s", (pemesanan_id,))
            ensure_operational_order_record(cur, pemesanan_id)
            sync_operational_status(cur, pemesanan_id, order_status='pending', payment_status='menunggu_verifikasi')
            append_order_status_log(
                cur,
                pemesanan_id,
                'Menunggu verifikasi pembayaran',
                f"User mengirim konfirmasi pembayaran manual melalui metode {selected_method['label']}.",
                actor_type='customer',
                actor_name=pemesanan.get('nama_pemesan') or 'Customer'
            )
            db.commit()
            cur.close()
            db.close()

            flash('Konfirmasi pembayaran manual sudah dicatat. Tim kami akan memverifikasi transaksi Anda.', 'success')
            return redirect(url_for('konfirmasi_pembayaran', pemesanan_id=pemesanan_id))

        except Exception as e:
            print(f"Pembayaran POST error: {e}")
            flash(f'Terjadi kesalahan: {str(e)}', 'error')

    return render_template(
        'pembayaran.html',
        pemesanan=pemesanan,
        pembayaran=pembayaran,
        payment_detail_map=payment_detail_map,
        payment_methods=PAYMENT_METHOD_CONFIG,
        payment_config=PAYMENT_DISPLAY_CONFIG,
        payment_demo=PAYMENT_DEMO_CONFIG,
        payment_account=FINANCE_ACCOUNT_CONFIG,
        manual_qris_image=get_manual_qris_image(),
        demo_qris_enabled=demo_qris_enabled,
        midtrans_enabled=midtrans_is_configured(),
        midtrans_client_key=get_midtrans_client_key(),
        midtrans_snap_js_url=midtrans_snap_js_url(),
        launch_snap=launch_snap
    )

@app.route('/konfirmasi_pembayaran/<int:pemesanan_id>', methods=['GET', 'POST'])
def konfirmasi_pembayaran(pemesanan_id):
    """Payment confirmation page."""
    if not get_current_user():
        return redirect_to_login(
            message='Login diperlukan untuk melihat konfirmasi pembayaran.',
            next_url=url_for('konfirmasi_pembayaran', pemesanan_id=pemesanan_id)
        )

    pemesanan = None
    pembayaran = None
    payment_detail_rows = []
    payment_detail_map = {}

    demo_qris_enabled = payment_demo_enabled() and not midtrans_is_configured()

    try:
        if midtrans_is_configured():
            sync_midtrans_payment_for_booking(pemesanan_id)

        db = get_db()
        cur = db.cursor(dictionary=True)

        cur.execute("""
            SELECT p.*, tp.nama_paket, w.nama as wisata_nama, w.foto
            FROM pemesanan p
            JOIN tipe_paket tp ON p.paket_id = tp.id
            JOIN wisata w ON tp.wisata_id = w.id
            WHERE p.id = %s
        """, (pemesanan_id,))
        pemesanan = apply_destination_media(cur.fetchone())

        if pemesanan:
            cur.execute("SELECT * FROM pembayaran WHERE pemesanan_id = %s", (pemesanan_id,))
            pembayaran = cur.fetchone()

            if pembayaran:
                cur.execute("SELECT * FROM payment_detail WHERE pembayaran_id = %s ORDER BY id ASC", (pembayaran['id'],))
                payment_detail_rows = cur.fetchall()
                payment_detail_map = payment_details_rows_to_map(payment_detail_rows)

        if request.method == 'POST':
            action = request.form.get('action')
            if action == 'simulate_demo_success' and pembayaran and pembayaran.get('gateway_provider') == 'demo_qris':
                if pembayaran.get('status_pembayaran') == 'berhasil':
                    flash('Simulasi pembayaran ini sudah ditandai berhasil sebelumnya.', 'info')
                    return redirect(url_for('konfirmasi_pembayaran', pemesanan_id=pemesanan_id))

                payment_detail_map = complete_demo_qris_payment(cur, pembayaran, pemesanan, payment_detail_map)
                pembayaran['status_pembayaran'] = 'berhasil'
                pembayaran['gateway_status'] = 'settlement_demo'
                pembayaran['gateway_transaction_id'] = payment_detail_map.get('demo_transaction_id')
                pembayaran['payment_reference'] = payment_detail_map.get('demo_reference')
                pembayaran['paid_at'] = payment_detail_map.get('demo_paid_at')
                pembayaran['tanggal_pembayaran'] = payment_detail_map.get('demo_paid_at')
                db.commit()
                flash('Simulasi pembayaran QRIS berhasil dicatat. Dashboard admin sekarang bisa menunjukkan status lunas dan siap diproses.', 'success')
                return redirect(url_for('konfirmasi_pembayaran', pemesanan_id=pemesanan_id))

            if action == 'upload_evidence' and pembayaran:
                file = request.files.get('bukti_pembayaran')
                if file and file.filename:
                    import os
                    from werkzeug.utils import secure_filename
                    upload_dir = os.path.join(app.root_path, 'static', 'uploads', 'evidence')
                    os.makedirs(upload_dir, exist_ok=True)
                    
                    filename = secure_filename(f"evidence_{pembayaran['id']}_{file.filename}")
                    file_path = os.path.join(upload_dir, filename)
                    file.save(file_path)
                    
                    # Update payment details to include the evidence
                    payment_detail_map['bukti_pembayaran'] = filename
                    replace_payment_details(cur, pembayaran['id'], payment_detail_map)
                    
                    flash('Bukti pembayaran berhasil diupload.', 'success')
                    db.commit()
                    return redirect(url_for('konfirmasi_pembayaran', pemesanan_id=pemesanan_id))

        cur.close()
        db.close()
    except Exception as e:
        print(f"Konfirmasi error: {e}")

    if not pemesanan:
        flash('Data pemesanan tidak ditemukan.', 'error')
        return redirect(url_for('status_pesanan'))

    if not user_owns_booking(pemesanan.get('email')):
        flash('Pesanan ini tidak terhubung dengan akun yang sedang login.', 'error')
        return redirect(url_for('status_pesanan'))

    payment_detail_map = enrich_demo_payment_detail_map(pemesanan, pembayaran, payment_detail_map)

    return render_template(
        'konfirmasi_pembayaran.html',
        pemesanan=pemesanan,
        pembayaran=pembayaran,
        payment_details=payment_detail_rows,
        payment_detail_map=payment_detail_map,
        payment_config=PAYMENT_DISPLAY_CONFIG,
        payment_demo=PAYMENT_DEMO_CONFIG,
        payment_account=FINANCE_ACCOUNT_CONFIG,
        manual_qris_image=get_manual_qris_image(),
        demo_qris_enabled=demo_qris_enabled
    )


@app.route('/api/pembayaran/<int:pemesanan_id>/midtrans-sync', methods=['POST'])
def api_midtrans_sync(pemesanan_id):
    """Persist Midtrans Snap callback payload from the browser."""
    if not get_current_user():
        return jsonify({'error': 'Login diperlukan.'}), 401

    try:
        db = get_db()
        cur = db.cursor(dictionary=True)
        cur.execute("SELECT email FROM pemesanan WHERE id = %s", (pemesanan_id,))
        pemesanan = cur.fetchone()
        cur.close()
        db.close()
    except Exception as error:
        return jsonify({'error': str(error)}), 500

    if not pemesanan or not user_owns_booking(pemesanan.get('email')):
        return jsonify({'error': 'Pesanan tidak ditemukan atau bukan milik akun ini.'}), 404

    payload = request.get_json(silent=True) or {}
    if not payload.get('order_id'):
        return jsonify({'error': 'Payload transaksi tidak lengkap.'}), 400

    try:
        sync_midtrans_payment_payload(payload)
        return jsonify({'success': True})
    except Exception as error:
        print(f"Midtrans sync payload error: {error}")
        return jsonify({'error': str(error)}), 500


@app.route('/payment-notifications/midtrans', methods=['POST'])
def midtrans_notification():
    """Handle Midtrans server-to-server notifications."""
    payload = request.get_json(silent=True) or {}
    if not verify_midtrans_signature(payload):
        return jsonify({'error': 'Signature Midtrans tidak valid.'}), 403

    try:
        sync_midtrans_payment_payload(payload)
        return jsonify({'success': True})
    except Exception as error:
        print(f"Midtrans notification error: {error}")
        return jsonify({'error': str(error)}), 500

# ════════════════════════════════════════
# RATING/REVIEW ROUTES (NEW!)
# ════════════════════════════════════════

@app.route('/review/<int:pemesanan_id>', methods=['GET', 'POST'])
def review(pemesanan_id):
    """Rating and review page"""
    if not get_current_user():
        return redirect_to_login(
            message='Login diperlukan untuk menulis review perjalanan Anda.',
            next_url=url_for('review', pemesanan_id=pemesanan_id)
        )

    pemesanan = None
    existing_review = None
    
    try:
        db = get_db()
        cur = db.cursor(dictionary=True)
        
        # Get booking info
        cur.execute("""
            SELECT p.*, tp.wisata_id, w.nama as wisata_nama, w.foto
            FROM pemesanan p
            JOIN tipe_paket tp ON p.paket_id = tp.id
            JOIN wisata w ON tp.wisata_id = w.id
            WHERE p.id = %s
        """, (pemesanan_id,))
        pemesanan = cur.fetchone()
        if pemesanan:
            review_media = get_destination_media(pemesanan.get('wisata_nama'))
            if not (pemesanan.get('foto') or '').strip() and review_media.get('image'):
                pemesanan['foto'] = review_media['image']
        
        # Check if already reviewed
        if pemesanan:
            cur.execute("""
                SELECT * FROM rating_review WHERE pemesanan_id = %s
            """, (pemesanan_id,))
            existing_review = cur.fetchone()
        
        cur.close()
        db.close()
    except Exception as e:
        print(f"Review GET error: {e}")

    if not pemesanan:
        flash('Data pemesanan tidak ditemukan.', 'error')
        return redirect(url_for('status_pesanan'))

    if not user_owns_booking(pemesanan.get('email')):
        flash('Pesanan ini tidak terhubung dengan akun yang sedang login.', 'error')
        return redirect(url_for('status_pesanan'))

    if request.method == 'POST' and pemesanan:
        try:
            db = get_db()
            cur = db.cursor()

            nama_pengguna = request.form.get('nama_pengguna', '').strip() or pemesanan['nama_pemesan']
            email_pengguna = request.form.get('email_pengguna', '').strip() or pemesanan['email']
            destinasi_id = pemesanan['wisata_id']
            
            rating_destinasi = float(request.form.get('rating_destinasi', 5.0))
            rating_pelayanan = float(request.form.get('rating_pelayanan', 5.0))
            rating_keseluruhan = float(request.form.get('rating_keseluruhan', 5.0))
            
            judul_review = request.form.get('judul_review', '').strip()
            isi_review = request.form.get('isi_review', '').strip()
            
            # Validate ratings (1-5)
            for rating in [rating_destinasi, rating_pelayanan, rating_keseluruhan]:
                if not (1.0 <= rating <= 5.0):
                    flash('Rating harus antara 1 dan 5!', 'error')
                    cur.close()
                    db.close()
                    return render_template('review.html', pemesanan=pemesanan)
            
            # Check if update or insert
            if existing_review:
                # Update
                cur.execute("""
                    UPDATE rating_review SET
                        nama_pengguna = %s,
                        email_pengguna = %s,
                        rating_destinasi = %s,
                        rating_pelayanan = %s,
                        rating_keseluruhan = %s,
                        judul_review = %s,
                        isi_review = %s,
                        tanggal_review = %s
                    WHERE pemesanan_id = %s
                """, (nama_pengguna, email_pengguna, rating_destinasi, rating_pelayanan, rating_keseluruhan,
                      judul_review, isi_review, datetime.now(), pemesanan_id))
                flash('Rating diperbarui!', 'success')
            else:
                # Insert
                cur.execute("""
                    INSERT INTO rating_review
                      (pemesanan_id, destinasi_id, nama_pengguna, email_pengguna,
                       rating_destinasi, rating_pelayanan, rating_keseluruhan,
                       judul_review, isi_review, status_review, tanggal_review)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending', %s)
                """, (pemesanan_id, destinasi_id, nama_pengguna, email_pengguna,
                      rating_destinasi, rating_pelayanan, rating_keseluruhan,
                      judul_review, isi_review, datetime.now()))
                flash('Terima kasih atas rating Anda! Review akan ditampilkan setelah verifikasi.', 'success')
            
            db.commit()
            cur.close()
            db.close()
            
            return redirect(url_for('status_pesanan'))
        
        except Exception as e:
            print(f"Review POST error: {e}")
            flash(f'Terjadi kesalahan: {str(e)}', 'error')

    return render_template('review.html', pemesanan=pemesanan, existing_review=existing_review)

# ════════════════════════════════════════
# OTHER ROUTES
# ════════════════════════════════════════

@app.route('/riwayat')
@app.route('/status-pesanan')
def status_pesanan():
    """User-facing order status page."""
    if not get_current_user():
        return redirect_to_login(
            message='Silakan login untuk melihat status pesanan tiket Anda.',
            next_url=url_for('status_pesanan')
        )

    status_data = []
    summary = {
        'total': 0,
        'payment_pending': 0,
        'verifying': 0,
        'active': 0,
        'completed': 0
    }

    try:
        db = get_db()
        cur = db.cursor(dictionary=True)

        cur.execute("""
            SELECT
                p.*,
                tp.nama_paket,
                tp.harga,
                w.nama as wisata_nama,
                w.foto,
                pb.id as pembayaran_id,
                pb.status_pembayaran,
                pb.metode_pembayaran,
                pb.tanggal_pembayaran,
                rr.id as review_id
            FROM pemesanan p
            JOIN tipe_paket tp ON p.paket_id = tp.id
            JOIN wisata w ON tp.wisata_id = w.id
            LEFT JOIN pembayaran pb ON pb.pemesanan_id = p.id
            LEFT JOIN rating_review rr ON rr.pemesanan_id = p.id
            WHERE LOWER(p.email) = %s
            ORDER BY p.tanggal_pesan DESC
        """, (get_current_user_email(),))
        status_data = cur.fetchall()
        for row in status_data:
            media = get_destination_media(row.get('wisata_nama'))
            if not (row.get('foto') or '').strip() and media.get('image'):
                row['foto'] = media['image']

        cur.close()
        db.close()
    except Exception as e:
        print(f"Status pesanan error: {e}")

    for item in status_data:
        item['status_info'] = get_booking_status_info(item)
        item['is_reviewed'] = bool(item.get('review_id'))
        item['can_pay_now'] = item['status_info']['key'] == 'payment_pending'
        item['can_review'] = item['status_info']['key'] in ['confirmed', 'completed']

    summary['total'] = len(status_data)
    summary['payment_pending'] = len([row for row in status_data if row['status_info']['key'] == 'payment_pending'])
    summary['verifying'] = len([row for row in status_data if row['status_info']['key'] == 'verifying'])
    summary['completed'] = len([row for row in status_data if row['status_info']['key'] == 'completed'])
    summary['active'] = len([
        row for row in status_data
        if row['status_info']['key'] in ['verifying', 'confirmed']
    ])

    return render_template('riwayat.html', status_data=status_data, summary=summary)

@app.route('/kontak', methods=['GET', 'POST'])
def kontak():
    """Contact page"""
    if request.method == 'POST':
        flash('Pesan Anda telah berhasil dikirim! Tim kami akan segera menghubungi Anda.', 'success')
        return redirect(url_for('kontak'))
    return render_template('kontak.html')

@app.route('/tentang')
def tentang():
    """About page"""
    return render_template('tentang.html')

# ════════════════════════════════════════
# API ENDPOINTS (for AJAX)
# ════════════════════════════════════════

@app.route('/api/destinasi/<int:id>')
def api_destinasi(id):
    """Get destinasi details via API"""
    try:
        db = get_db()
        cur = db.cursor(dictionary=True)
        cur.execute("SELECT * FROM wisata WHERE id = %s", (id,))
        destinasi = apply_destination_media(cur.fetchone())
        cur.close()
        db.close()
        
        if destinasi:
            return jsonify(destinasi)
        else:
            return jsonify({'error': 'Not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/paket/<int:wisata_id>')
def api_paket(wisata_id):
    """Get paket by wisata_id via API"""
    try:
        db = get_db()
        cur = db.cursor(dictionary=True)
        cur.execute("SELECT * FROM tipe_paket WHERE wisata_id = %s", (wisata_id,))
        paket = cur.fetchall()
        cur.close()
        db.close()
        
        return jsonify(paket)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/healthz')
def healthz():
    """Simple health check endpoint for hosted smoke tests."""
    db_ok = False
    try:
        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT 1")
        cur.fetchone()
        cur.close()
        db.close()
        db_ok = True
    except Exception as error:
        print(f"Health check DB warning: {error}")

    return jsonify({
        'status': 'ok' if db_ok else 'degraded',
        'database': 'ok' if db_ok else 'unreachable'
    }), (200 if db_ok else 503)

# ════════════════════════════════════════
# ERROR HANDLERS
# ════════════════════════════════════════

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('500.html'), 500

# ════════════════════════════════════════
# RUN APP
# ════════════════════════════════════════

try:
    ensure_database_schema()
except Exception as schema_error:
    print(f"Schema bootstrap error: {schema_error}")

if __name__ == '__main__':
    app.run(debug=True, port=5000)
