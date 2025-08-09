from __future__ import annotations
import argparse, pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt

def main():
    ap = argparse.ArgumentParser(description="Quick EDA for carfind output")
    ap.add_argument("--csv", required=True)
    ap.add_argument("--model", default=None, help='Filter title contains (e.g. "CX-30")')
    args = ap.parse_args()

    df = pd.read_csv(args.csv)
    if args.model:
        df = df[df["title"].str.contains(args.model, case=False, na=False)]

    out_dir = Path("data"); out_dir.mkdir(parents=True, exist_ok=True)
    png = out_dir / "price_hist.png"

    plt.figure()
    df["price"].dropna().astype(int).plot.hist(bins=30)
    plt.title("Price distribution" + (f" — {args.model}" if args.model else ""))
    plt.xlabel("Price (USD)"); plt.ylabel("Count"); plt.tight_layout()
    plt.savefig(png)
    print(f"[eda] saved {png}")

if __name__ == "__main__":
    main()
