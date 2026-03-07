from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import csv
import json
import io
import time
from typing import Optional
from fastapi.responses import StreamingResponse

app = FastAPI(title="SCRPR API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",

    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
}


#Models

class ScrapeRequest(BaseModel):
    url: str
    scrape_links: bool = True
    scrape_images: bool = True
    scrape_tables: bool = True
    timeout: int = 15


class LinkResult(BaseModel):
    text: str
    href: str
    type: str  


class ImageResult(BaseModel):
    src: str
    alt: str
    width: Optional[str] = None
    height: Optional[str] = None


class TableResult(BaseModel):
    index: int
    headers: list[str]
    rows: list[list[str]]


class ScrapeResponse(BaseModel):
    url: str
    title: str
    status_code: int
    content_size_kb: float
    elapsed_ms: int
    links: list[LinkResult]
    images: list[ImageResult]
    tables: list[TableResult]


#Helpers 
def classify_link(href: str, base_origin: str) -> str:
    try:
        parsed = urlparse(href)
        if not parsed.scheme:
            return "other"
        return "internal" if parsed.netloc == base_origin else "external"
    except Exception:
        return "other"


def parse_links(soup: BeautifulSoup, base_url: str) -> list[LinkResult]:
    base_origin = urlparse(base_url).netloc
    results = []
    seen = set()
    for tag in soup.find_all("a", href=True):
        href = tag["href"].strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        resolved = urljoin(base_url, href)
        if resolved in seen:
            continue
        seen.add(resolved)
        text = tag.get_text(strip=True)[:200] or "(no text)"
        results.append(LinkResult(
            text=text,
            href=resolved,
            type=classify_link(resolved, base_origin)
        ))
    return results


def parse_images(soup: BeautifulSoup, base_url: str) -> list[ImageResult]:
    results = []
    seen = set()
    for tag in soup.find_all("img"):
        src = tag.get("src") or tag.get("data-src") or ""
        src = src.strip()
        if not src:
            continue
        resolved = urljoin(base_url, src)
        if resolved in seen:
            continue
        seen.add(resolved)
        results.append(ImageResult(
            src=resolved,
            alt=tag.get("alt", ""),
            width=tag.get("width"),
            height=tag.get("height")
        ))
    return results


def parse_tables(soup: BeautifulSoup) -> list[TableResult]:
    results = []
    for idx, table in enumerate(soup.find_all("table"), start=1):
        headers = [th.get_text(strip=True) for th in table.find_all("th")]
        rows = []
        for tr in table.find_all("tr"):
            cells = [td.get_text(strip=True) for td in tr.find_all("td")]
            if cells:
                rows.append(cells)
        results.append(TableResult(index=idx, headers=headers, rows=rows))
    return results


#Routes

@app.get("/", response_class=HTMLResponse)
async def index():
    with open("static/index.html", "r") as f:
        return f.read()


@app.post("/scrape", response_model=ScrapeResponse)
async def scrape(req: ScrapeRequest):
    url = req.url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        start = time.time()
        resp = requests.get(url, headers=HEADERS, timeout=req.timeout, allow_redirects=True)
        elapsed = int((time.time() - start) * 1000)
        resp.raise_for_status()
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Request timed out — the site took too long to respond.")
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=502, detail="Could not connect to the target URL. Check the address and try again.")
    except requests.exceptions.HTTPError:
        error_msgs = {403: "Access denied (403) — site is blocking scrapers.", 404: "Not found (404) — check the URL.", 405: "Method not allowed (405) — site may block bots or require JavaScript.", 429: "Rate limited (429) — wait and try again."}
        raise HTTPException(status_code=resp.status_code, detail=error_msgs.get(resp.status_code, f"Target site returned HTTP {resp.status_code}."))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

    if not resp.content:
        raise HTTPException(status_code=422, detail="The site returned an empty response. It may require JavaScript to render.")

    soup = BeautifulSoup(resp.content, "html.parser")
    title = soup.title.string.strip() if soup.title and soup.title.string else url

    # Warn if page looks JS-rendered (very little actual text content)
    body_text = soup.get_text(strip=True)
    if len(body_text) < 200:
        raise HTTPException(
            status_code=422,
            detail="Page appears to be JavaScript-rendered. requests+BS4 only fetches static HTML. Try a simpler site, or add Playwright support."
        )

    return ScrapeResponse(
        url=resp.url,
        title=title,
        status_code=resp.status_code,
        content_size_kb=round(len(resp.content) / 1024, 2),
        elapsed_ms=elapsed,
        links=parse_links(soup, resp.url) if req.scrape_links else [],
        images=parse_images(soup, resp.url) if req.scrape_images else [],
        tables=parse_tables(soup) if req.scrape_tables else [],
    )


@app.post("/export/json")
async def export_json(req: ScrapeRequest):
    data = await scrape(req)
    content = json.dumps(data.dict(), indent=2)
    return StreamingResponse(
        io.StringIO(content),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=scrape-export.json"}
    )


@app.post("/export/csv")
async def export_csv(req: ScrapeRequest):
    data = await scrape(req)
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["TYPE", "TEXT_OR_ALT", "URL_OR_SRC", "SUBTYPE"])
    for l in data.links:
        writer.writerow(["link", l.text, l.href, l.type])
    for i in data.images:
        writer.writerow(["image", i.alt, i.src, ""])
    for t in data.tables:
        for row in t.rows:
            writer.writerow([f"table_{t.index}", "", " | ".join(row), ""])

    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=scrape-export.csv"}
    )