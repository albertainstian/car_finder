[![CI](https://github.com/albertainstian/car_webscaper_data_ai_ml/actions/workflows/python-tests.yml/badge.svg?branch=main)](https://github.com/albertainstian/car_webscaper_data_ai_ml/actions/workflows/python-tests.yml) [![codecov](https://codecov.io/gh/albertainstian/car_webscaper_data_ai_ml/branch/main/graph/badge.svg)](https://codecov.io/gh/albertainstian/car_webscaper_data_ai_ml) ![License](https://img.shields.io/badge/license-MIT-blue.svg)
[![Python tests](https://github.com/albertainstian/car_webscaper_data_ai_ml/actions/workflows/python-tests.yml/badge.svg?branch=main)](https://github.com/albertainstian/car_webscaper_data_ai_ml/actions/workflows/python-tests.yml)
[![Python tests](https://github.com/albertainstian/car_webscaper_data_ai_ml/actions/workflows/python-tests.yml/badge.svg?branch=main)](https://github.com/albertainstian/car_webscaper_data_ai_ml/actions/workflows/python-tests.yml)
[![Python tests](https://github.com/albertainstian/car_webscaper_data_ai_ml/actions/workflows/python-tests.yml/badge.svg?branch=main)](https://github.com/albertainstian/car_webscaper_data_ai_ml/actions/workflows/python-tests.yml)
# Car Finder — Craigslist Scraper (CSV/SQLite)

Scrape car listings from Craigslist by **query** and **region(s)**, save to **CSV/SQLite**, formatted in machine learning and artificial intelligence training datasets

<!-- (Optional badges — update owner/repo if you want) -->
<!-- [![CI](https://github.com/<owner>/<repo>/actions/workflows/ci.yml/badge.svg)](https://github.com/<owner>/<repo>/actions/workflows/ci.yml) -->
<!-- ![Python](https://img.shields.io/badge/python-3.10%2B-blue) -->

## Features
- 🧭 Search multiple regions in one run
- ⏱️ Rate-limit friendly with `--sleep`
- 💾 Outputs: CSV and/or SQLite
- 🧪 Tests + (optional) CI wiring

- ## Install

### Option 1 (recommended): Install from GitHub tag
```bash
pip install "git+https://github.com/albertainstian/car_webscaper_data_ai_ml.git@v0.1.0"


## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate         
python -m pip install -U pip    
pip install -r requirements.txtulsoup4 lxml pandas matplotlib

python carfind.py \
  --query "Mazda CX-30" \
  --regions losangeles sandiego sfbay \
  --limit 30 --sleep 1.5 --since 14 \
  --out data/cx30.csv
