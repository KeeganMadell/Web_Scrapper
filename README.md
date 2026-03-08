# SCRPR — Web Scraper

A full-stack web scraping tool built with FastAPI and BeautifulSoup4, featuring a clean dark-themed browser UI. Point it at any URL to extract links, images, and structured table data from static HTML pages. Results are displayed in a tabbed interface and can be exported as JSON or CSV for further use.
Built with: Python, FastAPI, BeautifulSoup4, HTML/CSS/JS
Features: Link classification (internal/external), image preview grid, table extraction, JSON & CSV export, response time and size metrics.

FastAPI + BeautifulSoup4 scraper with a clean browser UI.

## Setup

```bash
# 1. Clone / unzip the project
cd scraper

# 2. Create a virtual environment
python3 -m venv venv
source venv/bin/activate        # Linux/Mac
# venv\Scripts\activate         # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the server
uvicorn main:app --reload --port 8000
```

Open **http://localhost:8000** in your browser.

## Features
- Scrapes **links** (internal/external tagged), **images** (lazy-loaded grid), **HTML tables**
- Toggle each data type on/off before scraping
- Export results as **JSON** or **CSV**
- Shows status code, page size, and response time
- Proper User-Agent headers to reduce bot blocking

## API Endpoints
| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Frontend UI |
| POST | `/scrape` | Scrape a URL, returns JSON |
| POST | `/export/json` | Download JSON export |
| POST | `/export/csv` | Download CSV export |

## Project Structure
```
scraper/
├── main.py           # FastAPI backend
├── requirements.txt
├── static/
│   └── index.html    # Frontend UI
└── README.md
```
