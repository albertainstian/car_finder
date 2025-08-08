# Car Finder — Craigslist Scraper (CSV/SQLite + Quick EDA)

Scrape car listings make/model and price from Craigslist by **query** and **region(s)**, save to **CSV/SQLite**, and run a tiny **EDA** to visualize prices. formatted in machine learning and artificial intelligence friendly csv

Built as a lightweight, production-ish Python project you can extend.

<!-- (Optional badges — update owner/repo if you want) -->
<!-- [![CI](https://github.com/<owner>/<repo>/actions/workflows/ci.yml/badge.svg)](https://github.com/<owner>/<repo>/actions/workflows/ci.yml) -->
<!-- ![Python](https://img.shields.io/badge/python-3.10%2B-blue) -->

## Features
- 🧭 Search multiple regions in one run
- ⏱️ Rate-limit friendly with `--sleep`
- 🧹 Dedupe and optional `--since` filter (last N days)
- 💾 Outputs: CSV and/or SQLite
- 📊 Quick EDA script to plot a price histogram
- 🧪 Tests + (optional) CI wiring

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
python carfinder.py --query "mazda cx 30" --regions sandiego --limit 15 --sleep 2 --out data/sd.csv


python -m venv .venv && source .venv/bin/activate &&
pip install requests beautifulsoup4 lxml


# Quick EDA (writes data/price_hist.png)
python scripts/eda_quick.py --csv data/cx30.csv --model "Mazda CX-30"

[![CI](https://github.com/albertainstian/car_webscaper_data_ai_ml/actions/workflows/ci.yml/badge.svg)](https://github.com/albertainstian/car_webscaper_data_ai_ml/actions)
