"""Kompatibilitas lama.

Pengaturan kanal pembayaran utama sekarang dipusatkan di
company_payment_config.py agar tim cukup mengelola satu file inti.
"""

from company_payment_config import (
    FINANCE_ACCOUNT_CONFIG,
    FINANCE_PAYMENT_METHODS,
    get_ewallet_account,
    get_payment_destination,
)
