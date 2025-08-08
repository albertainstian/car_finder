#!/usr/bin/env python3
"""
car_finder.py — target-only Craigslist scraper (Mazda CX-30 by default)

- Robust HTML selectors + RSS fallback (works even when HTML is blocked)
- Strict make/model filtering in TITLE (and optional deep content check)
- Appends to CSV and dedupes in SQLite
- Multi-region; owner-only toggle; include/exclude keywords
"""

from __future__ import annotations
import argparse, os, sys, time, random, sqlite3, csv, re
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timezone
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup
from xml.etree import ElementTree as ET

UA = [
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
]
HEADERS = {"Accept-Language": "en-US,en;q=0.9"}
RESULTS_PER_PAGE = 120

def log(*a): print(f"[{datetime.now().strftime('%H:%M:%S')}]", *a)

# ---------- Storage ----------
def db_init(path: str) -> None:
    conn = sqlite3.connect(path)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS listings(
      id TEXT PRIMARY KEY,
      title TEXT,
      url TEXT,
      price INTEGER,
      location TEXT,
      posted_at TEXT,
      region TEXT,
      inserted_at TEXT
    );
    """)
    conn.commit(); conn.close()

def db_insert_if_new(path: str, row: Dict) -> bool:
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute("""
      INSERT OR IGNORE INTO listings(id,title,url,price,location,posted_at,region,inserted_at)
      VALUES (?,?,?,?,?,?,?,?)
    """, (row["id"], row["title"], row["url"], row["price"], row["location"], row["posted_at"], row["region"],
          datetime.now(timezone.utc).isoformat()))
    conn.commit()
    inserted = cur.rowcount == 1
    conn.close()
    return inserted

def csv_append(path: str, row: Dict) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    new_file = not os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(["id","title","price","location","posted_at","region","url","inserted_at"])
        w.writerow([
            row["id"], row["title"], row["price"], row["location"], row["posted_at"],
            row["region"], row["url"], datetime.now(timezone.utc).isoformat()
        ])

# ---------- Helpers ----------
def parse_price(s: str) -> Optional[int]:
    if not s: return None
    digits = "".join(c for c in s if c.isdigit())
    return int(digits) if digits else None

def model_synonyms(model: str) -> List[str]:
    m = model.lower().strip()
    out = {m}
    out.add(m.replace("-", ""))
    out.add(m.replace(" ", ""))
    out.add(m.replace("-", " ").replace("  ", " ").strip())
    return list(out)

def title_matches(title: str, make: str, model: str, include: List[str], exclude: List[str]) -> bool:
    tl = title.lower()
    if any(x.lower() in tl for x in exclude): return False
    if make.lower() not in tl: return False
    if not any(x in tl for x in model_synonyms(model)): return False
    if include and not all(k.lower() in tl for k in include): return False
    return True

def fetch_html(region: str, category: str, query: str, offset: int, proxy: str = "") -> BeautifulSoup:
    url = f"https://{region}.craigslist.org/search/{category}"
    headers = dict(HEADERS); headers["User-Agent"] = random.choice(UA)
    params = {"query": query, "sort":"date", "hasPic":"1", "s": str(offset)}
    proxies = {"http": proxy, "https": proxy} if proxy else None
    r = requests.get(url, params=params, headers=headers, timeout=20, proxies=proxies)
    r.raise_for_status()
    return BeautifulSoup(r.text, "lxml")

def parse_results(soup: BeautifulSoup) -> Tuple[List[Dict], Optional[str]]:
    items: List[Dict] = []
    containers = soup.select("li.cl-search-result, li.cl-static-search-result")
    if not containers:
        containers = soup.select("li.result-row")
    if not containers:
        containers = [li for li in soup.select("li")
                      if li.select_one("a.cl-app-anchor, a.hdrlnk, a.result-title, a[href*='/cto/'], a[href*='/ctd/']")]
    for li in containers:
        a = (li.select_one("a.cl-app-anchor")
             or li.select_one("a.result-title.hdrlnk")
             or li.select_one("a.result-title")
             or li.select_one("a.hdrlnk")
             or li.select_one("a[href*='/cto/'], a[href*='/ctd/']")
             or li.find("a", href=True))
        if not a or not a.has_attr("href"): continue
        url = a["href"].strip()
        title = (a.get("aria-label") or a.get_text(" ", strip=True)) or li.get_text(" ", strip=True)[:140]
        price_el = (li.select_one("span.price")
                    or li.select_one("span.result-price")
                    or li.select_one("span.pricenew, span.pricetag"))
        price = parse_price(price_el.get_text(" ", strip=True)) if price_el else None
        if price is None:
            m = re.search(r"\$([\d,]+)", li.get_text(" ", strip=True))
            if m: price = int(m.group(1).replace(",", ""))
        hood_el = (li.select_one("span.neighborhood")
                   or li.select_one("span.result-hood")
                   or li.select_one("span.hood"))
        hood = hood_el.get_text(" ", strip=True).strip("() ") if hood_el else None
        t = li.find("time")
        posted_at = t["datetime"] if (t and t.has_attr("datetime")) else (t.get_text(" ", strip=True) if t else None)
        pid = li.get("data-pid") or li.get("id") or url
        items.append({"id": pid, "title": title, "url": url, "price": price, "location": hood, "posted_at": posted_at})
    next_url = None
    nxt = (soup.select_one("a.button.next")
           or soup.select_one("a.cl-next-page")
           or soup.find("a", attrs={"rel": "next"}))
    if nxt and nxt.has_attr("href"):
        next_url = nxt["href"]
    return items, next_url

# ---------- RSS fallback ----------
def fetch_rss(region: str, category: str, query: str, proxy: str = "") -> Optional[str]:
    url = f"https://{region}.craigslist.org/search/{category}?query={quote(query)}&format=rss"
    headers = dict(HEADERS); headers["User-Agent"] = random.choice(UA)
    proxies = {"http": proxy, "https": proxy} if proxy else None
    r = requests.get(url, headers=headers, timeout=20, proxies=proxies)
    if r.status_code != 200 or not r.text.strip():
        return None
    return r.text

def parse_results_rss(xml: str) -> List[Dict]:
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return []
    out: List[Dict] = []
    for item in root.iterfind(".//item"):
        title = (item.findtext("title") or "").strip()
        url   = (item.findtext("link") or "").strip()
        desc  = (item.findtext("description") or "").strip()
        m_price = re.search(r"\$([\d,]+)", title) or re.search(r"\$([\d,]+)", desc)
        price = int(m_price.group(1).replace(",", "")) if m_price else None
        hood = None
        m_hood = re.search(r"\(([^)]+)\)", title)
        if m_hood: hood = m_hood.group(1).strip()
        if url and title:
            out.append({"id": url, "title": title, "url": url, "price": price, "location": hood, "posted_at": None})
    return out

# ---------- Runner ----------
def run(args) -> None:
    make    = args.make.strip()
    model   = args.model.strip()
    include = [s.lower() for s in (args.must or [])]
    exclude = [s.lower() for s in (args.exclude or [])]
    regions = args.regions
    category = "cto" if args.owner else "cta"
    query = args.query or f"{make} {model}"
    proxy = args.proxy or os.getenv("CR_PROXY", "")

    os.makedirs(os.path.dirname(args.csv) or ".", exist_ok=True)
    db_init(args.db)

    total_new = 0
    for region in regions:
        log(f"Region: {region} | query='{query}' | category={category}")
        offset = 0
        page   = 0

        while page < 20 and total_new < args.limit:
            soup = fetch_html(region, category, query, offset, proxy=proxy)
            text = soup.get_text(" ", strip=True)
            if re.search(r"(unusual activity|verify you are a human|blocked|are you a human)", text, re.I):
                log("Block/verification page detected — using RSS fallback for this region.")
                rss = fetch_rss(region, category, query, proxy=proxy)
                items = parse_results_rss(rss) if rss else []
                next_url = None
            else:
                items, next_url = parse_results(soup)
                if not items and offset == 0:
                    log("HTML empty — trying RSS fallback…")
                    rss = fetch_rss(region, category, query, proxy=proxy)
                    items = parse_results_rss(rss) if rss else []
                    next_url = None
                    if items:
                        log(f"RSS returned {len(items)} items.")

            if not items:
                log("No items on this page.")
                break

            for it in items:
                if total_new >= args.limit: break

                # YEAR filter
                if args.min_year or args.max_year:
                    yrs = re.findall(r"\b(19\d{2}|20\d{2})\b", it["title"])
                    year_ok = True
                    if yrs:
                        try:
                            y = max(int(x) for x in yrs)
                            if args.min_year and y < args.min_year: year_ok = False
                            if args.max_year and y > args.max_year: year_ok = False
                        except: pass
                    if not year_ok: continue

                if not title_matches(it["title"], make, model, include, exclude):
                    continue

                row = {
                    "id": it["id"] or it["url"],
                    "title": it["title"],
                    "url": it["url"],
                    "price": it["price"],
                    "location": it["location"],
                    "posted_at": it["posted_at"],
                    "region": region,
                }

                if db_insert_if_new(args.db, row):
                    total_new += 1
                    csv_append(args.csv, row)
                    log(f"[NEW] {row['title']}  ${row['price']}  -> {row['url']}")
                else:
                    log(f"[SKIP] dup: {row['url']}")

            if not next_url or total_new >= args.limit:
                break

            offset += RESULTS_PER_PAGE
            page   += 1
            time.sleep(args.sleep + random.uniform(0.3, 0.9))

    log(f"Done. New listings added: {total_new}. CSV: {args.csv}  DB: {args.db}")

def positive_int(x: str) -> int:
    v = int(x)
    if v <= 0: raise argparse.ArgumentTypeError("must be > 0")
    return v

def main():
    p = argparse.ArgumentParser(description="Target-only Craigslist scraper (defaults to Mazda CX-30).")
    p.add_argument("--make", default="Mazda", help="car make (default: Mazda)")
    p.add_argument("--model", default="CX-30", help="car model (default: CX-30)")
    p.add_argument("--query", default=None, help="override search query; otherwise uses '<make> <model>'")
    p.add_argument("--regions", nargs="+", default=["losangeles","sandiego","sfbay"], help="CL regions")
    p.add_argument("--owner", action="store_true", help="owner-only (cto) instead of all (cta)")
    p.add_argument("--min-year", type=int, default=None)
    p.add_argument("--max-year", type=int, default=None)
    p.add_argument("--must", nargs="*", default=[], help="extra required keywords in title (case-insensitive)")
    p.add_argument("--exclude", nargs="*", default=[], help="forbidden keywords in title")
    p.add_argument("--limit", type=positive_int, default=25, help="max new to save across all regions")
    p.add_argument("--sleep", type=float, default=2.5, help="seconds between pages (jittered)")
    p.add_argument("--db", default="carfinder.db", help="sqlite db path")
    p.add_argument("--csv", default="carfinder.csv", help="csv output path")
    p.add_argument("--proxy", default="", help="proxy url or set CR_PROXY env (optional)")
    args = p.parse_args()
    run(args)

if __name__ == "__main__":
    main()
