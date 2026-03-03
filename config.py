import os
from dotenv import load_dotenv

load_dotenv()

# --- Business Configuration ---
# Advertiser IDs to filter (comma-separated in env)
ADVERTISER_IDS = os.getenv('ADVERTISER_IDS', '').split(',')

# Special spot name (e.g. institutional spot)
SPECIAL_SPOT = os.getenv('SPECIAL_SPOT', '')

# File prefixes for each channel (comma-separated in env)
FILE_PREFIXES = os.getenv('FILE_PREFIXES', '').split(',')

# Google Sheet name
GOOGLE_SHEET_NAME = os.getenv('GOOGLE_SHEET_NAME', '')

# Gmail label to search
GMAIL_LABEL = os.getenv('GMAIL_LABEL', 'Logs')

# Data directory
DATA_DIR = os.getenv('DATA_DIR', 'data')
