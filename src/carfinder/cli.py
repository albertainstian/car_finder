import argparse
from .core import main as run_search  # or adapt to your function name

def build():
    p=argparse.ArgumentParser(prog="carfind", description="Car listings scraper")
    p.add_argument("--query", required=True)
    p.add_argument("--regions", nargs="+", required=True)
    p.add_argument("--limit", type=int, default=25)
    p.add_argument("--sleep", type=float, default=1.0)
    p.add_argument("--since", type=int, default=14)
    p.add_argument("--out", default="data/results.csv")
    return p

def main(argv=None):
    args=build().parse_args(argv)
    run_search(args)  # or pass explicit params if your core expects them
