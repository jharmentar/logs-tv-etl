<div align="center">

# 📡 Spots INE — ETL Monitor

> Automated pipeline that downloads daily broadcast spot logs from Gmail, processes them, syncs results to Google Sheets, and visualizes them in Looker Studio.

![Python](https://img.shields.io/badge/Python-3.x-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Google Sheets](https://img.shields.io/badge/Google%20Sheets-API-34A853?style=for-the-badge&logo=google-sheets&logoColor=white)
![Gmail](https://img.shields.io/badge/Gmail-API-EA4335?style=for-the-badge&logo=gmail&logoColor=white)
![Looker Studio](https://img.shields.io/badge/Looker-Studio-4285F4?style=for-the-badge&logo=looker&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)

</div>

---

## 📌 Overview

**Spots INE** is a fully automated ETL (Extract · Transform · Load) pipeline built for monitoring broadcast spots across 4 television channels. Every day, the script:

1. **Connects to Gmail** and downloads new `.xls` log files attached to unread emails in a specific label.
2. **Cleans and transforms** the data — filtering by advertiser, adjusting timestamps, and assigning time slots.
3. **Uploads the results** to a Google Sheets file with one sheet per channel.
4. **Feeds a Looker Studio dashboard** for real-time visualization and reporting.

This eliminates a manual daily process and ensures data is always up-to-date with zero human intervention.

---

## ✨ Features

| Feature | Description |
|---|---|
| 📥 **Auto-Download** | Fetches `.xls` files from Gmail based on filename patterns  |
| 🧹 **Data Cleaning** | Filters spots by advertiser  and special events |
| 🕐 **Time Adjustment** | Fixes edge cases like trailing ` spots|
| 🌅 **Shift Classification** | Labels each spot as `Mañana`, `Tarde`, or `Noche` based on broadcast time |
| ☁️ **Google Sheets Sync** | Pushes clean DataFrames into a dedicated Google Sheet, one tab per channel |
| 📊 **Looker Studio** | Interactive dashboard connected to Google Sheets for monitoring |
| 📋 **Structured Logging** | Timestamped logs for every step of the ETL process |

---

## 🗂️ Project Structure

```
Spots_INE/
├── main.py                       # ETL orchestrator (extract → transform → load)
├── spot_downloader.py            # Gmail API authentication and attachment downloader
├── config.py                     # Loads business config from environment variables
├── requirements.txt              # Python dependencies
├── Dockerfile                    # Container configuration for deployment
├── .github/workflows/
│   └── etl_schedule.yml          # GitHub Actions — daily scheduled pipeline
├── credentials.json              # 🔒 Google Service Account key (git-ignored)
├── client_secret.json            # 🔒 Gmail OAuth client secret (git-ignored)
├── token.json                    # 🔒 Auto-generated OAuth token (git-ignored)
├── .env                          # 🔒 Business configuration values (git-ignored)
└── data/                         # Working directory for downloaded XLS files
```

---

## ⚙️ ETL Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              EXTRACT                                        │
│  Gmail API ──► Unread emails (label: Logs) ──► Download .xls files          │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                             TRANSFORM                                       │
│  Filter rows (Only advertiser spots)                                        │
│  ──► Adjust timestamps ──► Classify shifts ──► Rename columns               │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                                LOAD                                         │
│  Google Sheets API ──► "Spots Your City" ──► Spot2 | Spot4 | Spot5 | Spot9  │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                             VISUALIZE                                       │
│  Looker Studio ──► Dashboard connected to Google Sheets                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- A [Google Cloud Project](https://console.cloud.google.com/) with the following APIs enabled:
  - Gmail API
  - Google Sheets API
  - Google Drive API

### 1. Clone the repository

```bash
git clone https://github.com/your-username/Spots_INE.git
cd Spots_INE
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure credentials

#### Google Sheets (Service Account)
1. Create a **Service Account** in Google Cloud Console and download the JSON key.
2. Rename it to `credentials.json` and place it in the project root.
3. Share your **"Spots"** Google Sheet with the service account's email address.

#### Gmail API (OAuth 2.0)
1. Create an **OAuth 2.0 Client ID** (Desktop App) in Google Cloud Console and download the JSON.
2. Rename it to `client_secret.json` and place it in the project root.
3. On the **first run**, a browser window will open for authorization. A `token.json` file will be auto-generated for subsequent runs.

### 4. Run the pipeline

```bash
python main.py
```

---

## 🐳 Running with Docker

### 1. Build the image
```bash
docker build -t spots-ine .
```

### 2. Run the container (Mounting secrets)
Since secrets are ignored by `.dockerignore`, you must mount them as volumes:

```bash
docker run --rm `
  -v "${PWD}/credentials.json:/app/credentials.json" `
  -v "${PWD}/client_secret.json:/app/client_secret.json" `
  -v "${PWD}/token.json:/app/token.json" `
  --env-file .env `
  spots-ine
```

### 3. Running with Docker Compose (Recommended for Servers)
This is the easiest way to run the project on a Linux server without manually mounting every file.

```bash
docker-compose up --build
```

To schedule it daily at 02:00 AM on a Linux server, add this to your `crontab -e`:
```bash
0 2 * * * cd /path/to/your_repo && docker-compose up --build
```

---

## 🔧 Environment Configuration

Business-specific values are loaded from environment variables (via `.env` file). 

---

## 🤖 GitHub Actions — Automated Daily Run

The pipeline is configured to run automatically every day at **2:00 AM (La Paz time)** via GitHub Actions.

### Required Secrets

Go to **Repository → Settings → Secrets and variables → Actions** and add:

| Secret | How to generate |
|---|---|
| `GOOGLE_CREDENTIALS` | `[Convert]::ToBase64String([IO.File]::ReadAllBytes("credentials.json"))` |
| `GMAIL_CLIENT_SECRET` | `[Convert]::ToBase64String([IO.File]::ReadAllBytes("client_secret.json"))` |
| `GMAIL_TOKEN` | `[Convert]::ToBase64String([IO.File]::ReadAllBytes("token.json"))` |
| `ADVERTISER_IDS` | Comma-separated advertiser IDs |
| `SPECIAL_SPOT` | Special spot name |
| `FILE_PREFIXES` | Your file prefixes |
| `GOOGLE_SHEET_NAME` | Your Google Sheet name |
| `GMAIL_LABEL` | Gmail label to search (e.g. `Logs`) |

### Manual Trigger

You can also trigger the pipeline manually from the **Actions** tab → **Daily ETL Pipeline** → **Run workflow**.

---

**Built with ❤️ by Josue Armenta**

**March 1, 2026**
