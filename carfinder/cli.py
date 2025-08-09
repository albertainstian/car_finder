from __future__ import annotations
import argparse, csv, os, re, time, requests
from bs4 import BeautifulSoup
from urllib.parse import urlencode
from datetime import datetime, timezone, timedelta

REG = {
  "losangeles":"https://losangeles.craigslist.org",
  "sandiego":"https://sandiego.craigslist.org",
  "sfbay":"https://sfbay.craigslist.org",
  "orangecounty":"https://orangecounty.craigslist.org",
  "inlandempire":"https://inlandempire.craigslist.org",
  "ventura":"https://ventura.craigslist.org",
}
UA = {"User-Agent":"Mozilla/5.0"}

def _url(r,q,s=0): return f"{REG[r]}/search/cta?{urlencode({'query':q,'s':s})}"

def _fetch(sess,url,tries=3,timeout=15):
    for _ in range(tries):
        try:
            r=sess.get(url,headers=UA,timeout=timeout); r.raise_for_status(); return r.text
        except Exception: time.sleep(1)
    return ""

def _parse(html,region):
    soup=BeautifulSoup(html,"lxml"); now=datetime.now(timezone.utc).isoformat(); out=[]
    rows=[]
    for sel in ("li.result-row","li.cl-search-result",".cl-static-search-result"):
        rows=soup.select(sel)
        if rows: break
    for row in rows:
        a=row.select_one("a.result-title, a.posting-title, .titlestring a, a.cl-app-anchor")
        if not a: continue
        title=a.get_text(strip=True); url=a.get("href","")
        if url and not url.startswith("http"): url=REG[region]+url
        p=row.select_one(".result-price, .price"); digits=re.sub(r"\D","",p.get_text() if p else "")
        price=int(digits) if digits else None
        loc=row.select_one(".result-hood,.location"); loc=loc.get_text(strip=True).strip("()") if loc else None
        t=row.select_one("time"); posted=t["datetime"] if t and t.has_attr("datetime") else ""
        pid=row.get("data-pid") or row.get("data-id") or re.sub(r".*?(\d{8,})","\\1",url)
        if pid and title and url:
            out.append({"id":str(pid),"title":title,"price":price,"location":loc,
                        "url":url,"posted_at":posted,"region":region,"created_ts":now})
    return out

def _run(q,regions,limit,sleep,since,outcsv):
    cutoff=(datetime.now(timezone.utc)-timedelta(days=since)).isoformat() if since else None
    seen,setrows=set(),[]
    with requests.Session() as s:
        for r in regions:
            got,off=0,0
            while got<limit:
                html=_fetch(s,_url(r,q,off)); batch=_parse(html,r)
                if cutoff: batch=[b for b in batch if (b["posted_at"]>=cutoff) or not b["posted_at"]]
                if not batch: break
                for b in batch:
                    if b["id"] in seen: continue
                    seen.add(b["id"]); setrows.append(b); got+=1
                    if got>=limit: break
                if len(batch)<100: break
                off+=len(batch); time.sleep(sleep)
    if setrows:
        os.makedirs(os.path.dirname(outcsv) or ".",exist_ok=True)
        with open(outcsv,"w",newline="",encoding="utf-8") as f:
            w=csv.DictWriter(f,fieldnames=list(setrows[0].keys()))
            w.writeheader(); w.writerows(setrows)
    print(f"[carfinder] scraped={len(setrows)} → {outcsv if setrows else '(no file)'}")
    if setrows[:3]: print("[sample]",*["- "+x["title"] for x in setrows[:3]],sep="\n")
    return 0

def main(argv=None):
    ap=argparse.ArgumentParser(description="Craigslist car finder (tiny)")
    ap.add_argument("--query",required=True)
    ap.add_argument("--regions",nargs="+",required=True)
    ap.add_argument("--limit",type=int,default=50)
    ap.add_argument("--sleep",type=float,default=1.5)
    ap.add_argument("--since",type=int,default=None)
    ap.add_argument("--out",default="data/results.csv")
    a=ap.parse_args(argv)
    return _run(a.query,a.regions,a.limit,a.sleep,a.since,a.out)
