import argparse, csv, re, time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
import requests
from bs4 import BeautifulSoup

# ---- HOT PATCH START ----
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

def build_search_url(region: str, query: str, offset: int = 0) -> str:
    # Wider search (title+body). Keep simple paging via ?s=
    base = _region_base(region) if "_region_base" in globals() else REGIONS[region]  # works for both styles
    from urllib.parse import urlencode
    return f"{base}/search/cta?{urlencode({'query': query, 's': offset})}"

def parse_listings(html: str, region: str):
    # Robust selectors for newer CL markup
    from bs4 import BeautifulSoup
    from datetime import datetime, timezone
    import re
    soup = BeautifulSoup(html, "lxml")
    now = datetime.now(timezone.utc).isoformat()
    out = []

    # try multiple row patterns
    rows = []
    for sel in ("li.result-row", "li.cl-search-result", ".cl-static-search-result"):
        rows = soup.select(sel)
        if rows: break

    if not rows:
        # dump a debug page once to inspect structure
        import os
        os.makedirs("data", exist_ok=True)
        with open("data/_debug.html", "w", encoding="utf-8") as f: f.write(html)
        print("[debug] saved data/_debug.html (no rows matched)")
        return out

    for row in rows:
        pid = row.get("data-pid") or row.get("data-id") or ""
        # title/url
        a = (row.select_one("a.result-title") or
             row.select_one("a.posting-title") or
             row.select_one(".titlestring a") or
             row.select_one("a.cl-app-anchor") or
             row.select_one("a[href*='/cto/'], a[href*='/ctd/']"))
        if not a: 
            continue
        title = a.get_text(strip=True)
        url = a.get("href") or ""
        if url and not url.startswith("http"):
            base = _region_base(region) if "_region_base" in globals() else REGIONS[region]
            url = base + url

        # price
        p = row.select_one(".result-price") or row.select_one(".price") or row.select_one("span[class*='price']")
        digits = re.sub(r"[^\d]", "", p.get_text(strip=True) if p else "")
        price = int(digits) if digits else None

        # location
        hood = row.select_one(".result-hood") or row.select_one(".location")
        loc = hood.get_text(strip=True).strip("()") if hood else None

        # posted time
        t = row.select_one("time")
        posted = t.get("datetime") if (t and t.has_attr("datetime")) else ""
        if not posted:
            t2 = row.select_one("time[title]")
            posted = t2.get("title") if t2 else ""

        if not pid and url:
            d = re.sub(r"[^\d]", "", url)
            pid = d[-10:] if d else url

        if pid and title and url:
            out.append({"id": str(pid), "title": title, "price": price, "location": loc,
                        "url": url, "posted_at": posted, "region": region, "created_ts": now})
    return out
# ---- HOT PATCH END ----


UA = {"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"}
REGIONS = {
    "losangeles":"https://losangeles.craigslist.org",
    "sandiego":"https://sandiego.craigslist.org",
    "sfbay":"https://sfbay.craigslist.org",
}

def build_url(region, q, offset=0):
    base = REGIONS[region]
    params = {"query": q, "srchType": "T", "s": offset}
    return f"{base}/search/cta?{urlencode(params)}"

def fetch(session, url, retries=2, timeout=15):
    last = None
    for _ in range(retries+1):
        try:
            r = session.get(url, headers=UA, timeout=timeout)
            r.raise_for_status()
            return r.text
        except Exception as e:
            last = e
            time.sleep(1)
    raise last

def parse_list(html, region):
    soup = BeautifulSoup(html, "lxml")
    now = datetime.now(timezone.utc).isoformat()
    out = []
    for row in soup.select(".result-row, .cl-static-search-result"):
        pid = row.get("data-pid") or row.get("data-id")
        a = row.select_one("a.result-title, a.posting-title, .titlestring a")
        title = (a.get_text(strip=True) if a else "") or ""
        url = (a.get("href") if a else "") or ""
        if url and not url.startswith("http"):
            url = REGIONS[region] + url
        price_tag = row.select_one(".result-price, .price")
        price_text = price_tag.get_text(strip=True) if price_tag else ""
        price_digits = re.sub(r"[^\d]", "", price_text or "")
        price = int(price_digits) if price_digits else ""
        hood = row.select_one(".result-hood") or row.select_one(".location")
        loc = (hood.get_text(strip=True).strip("()") if hood else "") or ""
        t = row.select_one("time")
        posted = t.get("datetime") if t and t.has_attr("datetime") else ""
        if not pid:
            # fallback from URL digits
            digits = re.sub(r"[^\d]", "", url)
            pid = digits[-10:] if digits else url
        if pid and title and url:
            out.append({
                "id": str(pid), "title": title, "price": price, "location": loc,
                "url": url, "posted_at": posted, "region": region, "created_ts": now
            })
    return out

def search(query, regions, limit=50, sleep_s=1.5, since_days=None):
    cutoff = None
    if since_days and since_days > 0:
        cutoff_dt = datetime.now(timezone.utc) - timedelta(days=since_days)
        cutoff = cutoff_dt.isoformat()
    results = []
    seen = set()
    with requests.Session() as s:
        for reg in regions:
            fetched = 0
            offset = 0
            while fetched < limit:
                html = fetch(s, build_url(reg, query, offset))
                batch = parse_list(html, reg)
                if cutoff:
                    batch = [b for b in batch if b["posted_at"] >= cutoff or not b["posted_at"]]
                if not batch: break
                for b in batch:
                    if b["id"] in seen: continue
                    seen.add(b["id"]); results.append(b); fetched += 1
                    if fetched >= limit: break
                if len(batch) < 100: break
                offset += len(batch); time.sleep(sleep_s)
    return results[:limit]

def write_csv(rows, path):
    if not rows: return 0
    import os
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    return len(rows)

def main():
    ap = argparse.ArgumentParser(description="Craigslist car finder (ultra-lean)")
    ap.add_argument("--query", required=True)
    ap.add_argument("--regions", nargs="+", required=True)
    ap.add_argument("--limit", type=int, default=50)
    ap.add_argument("--sleep", type=float, default=1.5)
    ap.add_argument("--since", type=int, default=None)
    ap.add_argument("--out", default="data/results.csv")
    args = ap.parse_args()

    rows = search(args.query, args.regions, args.limit, args.sleep, args.since)
    n = write_csv(rows, args.out)
    print(f"[carfinder] scraped={len(rows)} wrote={n} → {args.out}")
    if rows[:3]:
        print("[sample]", *[r["title"] for r in rows[:3]], sep="\n- ")

if __name__ == "__main__":
    main()
