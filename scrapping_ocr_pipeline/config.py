import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

DATA_DIR = os.path.join(BASE_DIR, "data")
RAW_DIR = os.path.join(DATA_DIR, "raw")
IMAGES_DIR = os.path.join(RAW_DIR, "images")
INTERIM_DIR = os.path.join(DATA_DIR, "interm")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")
HEADERS = {
    "User-Agent": "GameScraper/1.0"
}



def ensure_dirs() -> None:
    os.makedirs(IMAGES_DIR, exist_ok=True)
    os.makedirs(INTERIM_DIR, exist_ok=True)
    os.makedirs(PROCESSED_DIR, exist_ok=True)
