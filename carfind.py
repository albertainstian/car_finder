from __future__ import annotations
import argparse, csv, os, re, time, requests
from bs4 import BeautifulSoup
from urllib.parse import urlencode
from datetime import datetime, timezone, timedelta

REGIONS = {
  "losangeles":"https://losangeles.craigslist.org",
  "sandiego":"https://sandiego.craigslist.org",
  "orangecounty":"https://orangecounty.craigslist.org",
  "inlandempire":"https://inlandempire.craigslist.org",
  "ventura":"https://ventura.craigslist.org",
  "sfbay":"https://sfbay.craigslist.org",
}
UA = {
  "User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
  "Accept-Language":"en-US,en;q=0.9",
}
def _title_ok(title: str, q: str) -> bool:
    t = (title or "").lower()
    ql = (q or "").lower()
    variants = {ql, ql.replace("-", " "), ql.replace("-", ""), ql.replace(" ", "")}
    if "mazda" in ql or "cx" in ql:
        variants |= {"mazda cx-30", "mazda cx 30", "mazda cx30", "cx-30", "cx 30", "cx30"}
    return any(v in t for v in variants)

def _url(region: str, q: str, offset: int = 0) -> str:
    base = REGIONS.get(region)
    if not base:
        raise SystemError(f"Unknown region '{region}'. Try: {', '.join(sorted(REGIONS))}")
    from urllib.parse import urlencode
    params = {
        "query": q,
        "auto_make_model": q,  # hint to model filter
        "srchType": "T",       # TITLE ONLY to cut body noise
        "bundleDuplicates": 1, # collapse dupes
        # "purveyor": "owner", # uncomment to prefer private sellers
        "s": offset,
    }
    return f"{base}/search/cta?{urlencode(params)}"


def _fetch(sess: requests.Session, url: str, tries=3, timeout=15) -> str:
    last = None
    for _ in range(tries):
        try:
            r = sess.get(url, headers=UA, timeout=timeout); r.raise_for_status(); return r.text
        except Exception as e:
            last = e; time.sleep(1)
    raise last  # type: ignore[misc]

def _parse_dt(s: str | None):
    if not s: return None
    try:
        return datetime.fromisoformat(s.replace("Z","+00:00"))
    except Exception:
        return None

def _parse(html: str, region: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    now = datetime.now(timezone.utc).isoformat()
    out: list[dict] = []

    # Try multiple list layouts
    rows = []
    for sel in ("li.result-row","li.cl-search-result",".cl-static-search-result"):
        rows = soup.select(sel)
        if rows: break

    if not rows:
        os.makedirs("data", exist_ok=True)
        with open("data/_debug.html","w",encoding="utf-8") as f: f.write(html)
        return out

    for row in rows:
        # title + url
        a = row.select_one("a.result-title, a.posting-title, .titlestring a, a.cl-app-anchor") \
            or row.select_one("a[href*='/cto/'], a[href*='/ctd/']")
        if not a: continue
        title = a.get_text(strip=True) or ""
        url = a.get("href") or ""
        if url and not url.startswith("http"): url = REGIONS[region] + url

        # id
        pid = row.get("data-pid") or row.get("data-id") or ""
        if not pid and url:
            digits = re.sub(r"[^\d]","",url); pid = digits[-10:] if digits else url

        # price
        ptag = row.select_one(".result-price, .price, span[class*='price']")
        digits = re.sub(r"\D","", ptag.get_text(strip=True) if ptag else "")
        price = int(digits) if digits else None

        # location
        hood = row.select_one(".result-hood, .location")
        loc = hood.get_text(strip=True).strip("()") if hood else None

        # time
        t = row.select_one("time")
        posted = t["datetime"] if (t and t.has_attr("datetime")) else ""
        if pid and title and url:
            out.append({"id":str(pid),"title":title,"price":price,"location":loc,
                        "url":url,"posted_at":posted,"region":region,"created_ts":now})
    return out

def run(query: str, regions: list[str], limit=50, sleep=1.5, since_days: int|None=None, out_csv="data/results.csv") -> int:
    cutoff_dt = (datetime.now(timezone.utc) - timedelta(days=since_days)) if since_days else None
    seen: set[str] = set()
    rows: list[dict] = []

    with requests.Session() as s:
        for reg in regions:
            got, offset = 0, 0
            while got < limit:
                # 1) fetch, fail-safe
                try:
                    html = _fetch(s, _url(reg, query, offset))
                except Exception as e:
                    print(f"[warn] fetch failed for {reg} offset={offset}: {e}")
                    break

                # 2) parse → always define batch
                batch = _parse(html, reg) or []

                # 3) since filter
                if cutoff_dt:
                    def _keep_since(b):
                        dt = _parse_dt(b.get("posted_at"))
                        return (dt is None) or (dt >= cutoff_dt)
                    batch = [b for b in batch if _keep_since(b)]

                # 4) title backstop to avoid Ford/Tesla noise
                batch = [b for b in batch if _title_ok(b.get("title",""), query)]

                if not batch:
                    break

                # 5) dedupe + collect
                for b in batch:
                    if b["id"] in seen:
                        continue
                    seen.add(b["id"])
                    rows.append(b)
                    got += 1
                    if got >= limit:
                        break

                # 6) paging heuristic
                if len(batch) < 100:
                    break
                offset += len(batch)
                time.sleep(sleep)

    # write CSV
    if rows:
        os.makedirs(os.path.dirname(out_csv) or ".", exist_ok=True)
        with open(out_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader(); w.writerows(rows)
    print(f"[carfind] scraped={len(rows)} → {out_csv if rows else '(no file)'}")
    if rows[:3]:
        print("[sample]", *[f"- {r['title']}" for r in rows[:3]], sep="\n")
    return 0

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Craigslist car finder (single-file)")
    ap.add_argument("--query", required=True)
    ap.add_argument("--regions", nargs="+", required=True)
    ap.add_argument("--limit", type=int, default=50)
    ap.add_argument("--sleep", type=float, default=1.5)
    ap.add_argument("--since", type=int, default=None)
    ap.add_argument("--out", default="data/results.csv")
    a = ap.parse_args(argv)
    return run(a.query, a.regions, a.limit, a.sleep, a.since, a.out)

if __name__ == "__main__":
    raise SystemExit(main())
