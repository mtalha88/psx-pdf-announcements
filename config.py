"""Configuration for PSX PDF Announcements Space."""
import os
from pathlib import Path

# API Sources
SARMAAYA_API_URL = "https://beta-restapi.sarmaaya.pk/api/announcements/result-announcements"

# HuggingFace
HF_TOKEN = os.environ.get("HF_TOKEN")
HF_DATASET_ID = "rafaytalha23/psx-announcements-data"  # Dataset for storage

# Paths
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
ANNOUNCEMENTS_FILE = DATA_DIR / "announcements.csv"

# OCR Model (free on HF)
OCR_MODEL = "microsoft/trocr-base-printed"

# Test ticker for development
TEST_TICKER = "LUCK"
