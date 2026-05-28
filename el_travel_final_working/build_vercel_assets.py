"""Prepare public assets for Vercel deployments.

Vercel merekomendasikan file statis berada di folder `public/`. Project lokal ini
tetap memakai folder `static/` untuk Flask, jadi saat build script ini dijalankan
kami menyalin aset ke `public/static` tanpa mengganggu workflow lokal.
"""

from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "static"
PUBLIC_DIR = ROOT / "public"
PUBLIC_STATIC_DIR = PUBLIC_DIR / "static"


def rebuild_public_static():
    if PUBLIC_STATIC_DIR.exists():
        shutil.rmtree(PUBLIC_STATIC_DIR)
    PUBLIC_STATIC_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copytree(STATIC_DIR, PUBLIC_STATIC_DIR, dirs_exist_ok=True)


if __name__ == "__main__":
    PUBLIC_DIR.mkdir(exist_ok=True)
    rebuild_public_static()
    print("Prepared public/static for Vercel.")
