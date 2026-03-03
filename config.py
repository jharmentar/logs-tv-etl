import os
from dotenv import load_dotenv

load_dotenv()

# --- Business Configuration ---
# Advertiser IDs to filter (comma-separated in env)
ADVERTISER_IDS = [x.strip() for x in os.getenv('ADVERTISER_IDS', '').split(',') if x.strip()]

# Special spot name (e.g. institutional spot)
SPECIAL_SPOT = os.getenv('SPECIAL_SPOT', '').strip()

# File prefixes for each channel (comma-separated in env)
FILE_PREFIXES = [x.strip() for x in os.getenv('FILE_PREFIXES', '').split(',') if x.strip()]

# Google Sheet name
GOOGLE_SHEET_NAME = os.getenv('GOOGLE_SHEET_NAME', '').strip()

# Gmail label to search
GMAIL_LABEL = os.getenv('GMAIL_LABEL', 'Logs').strip()

# Data directory
DATA_DIR = os.getenv('DATA_DIR', 'data').strip()
