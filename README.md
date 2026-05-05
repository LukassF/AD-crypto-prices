# Crypto Prices Collector

Project for the Advanced Databases course. This repository collects cryptocurrency price data, stores it in a database, and (planned) provides a GUI to visualise and filter that data.

## What it is

- Fetches crypto prices from external APIs on a schedule or on-demand.
- Persists fetched data into a local database for analysis and querying.
- Future work: a GUI to visualise, filter and explore the stored data.

## Key files and folders

- `api_data_collector.py` — main data collection entrypoint.
- `requirements.txt` — Python dependencies.
- `models/price.py` — price model definition.
- `utils/db/` — database utilities and seeding scripts.

## Prerequisites

- Python 3.10+ (recommended)
- pip
- Docker & Docker Compose (optional, for containerised run)

## Run locally (virtualenv)

1. Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate

python3 ./init_env.py
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Initialize / seed the database (if needed):

```bash
python utils/db/seed.py
```

4. Run the data collector:

```bash
python api_data_collector.py
```

## Run with Docker Compose

Build and run all services with Docker Compose:

```bash
docker compose up --build
```

This is the quickest way to get the app running in a consistent environment.

## Notes & Next steps

- The GUI for visualisation and filtering is planned and will query the stored data from the database.
- Consider adding configuration (API keys, DB URL) via environment variables or a config file.
- Tests and example queries will be added as development continues.

## Contact / Contributing

Feel free to open an issue or PR with improvements. For course submissions, include a short usage/demo video or instructions.
