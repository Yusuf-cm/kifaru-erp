# Kifaru ERP

A small Django-based business management system for a retail/POS business:
point-of-sale checkout, multi-warehouse inventory, purchasing (suppliers &
purchase orders), and a real double-entry accounting ledger (chart of
accounts, journals, trial balance, P&L, balance sheet). Amounts are modeled
in KES but nothing is hardcoded to a single currency's formatting.

Apps:

- `core` — dashboard, document numbering (`DocumentSequence`), shared models.
- `inventory` — products, warehouses, and the stock-movement ledger (the
  source of truth for stock levels; movements are append-only).
- `purchasing` — suppliers and purchase orders; receiving a PO adds stock and
  posts the funding journal entry (cash/M-Pesa/bank/accounts payable).
- `sales` — the POS screen and checkout API; completing a sale deducts stock
  at moving-average cost and posts both the revenue and COGS journal entries.
- `accounting` — chart of accounts, journal entries/lines, accounting
  periods, and the reporting helpers (`accounting/services.py`) used by the
  trial balance, P&L, and balance sheet views.

## Requirements

- Python 3.11+ (developed/tested against 3.14)
- pip
- SQLite (bundled with Python) for local development, or PostgreSQL in
  production (see Database section below)

## Setup

```bash
# from the project root (this folder, containing manage.py)
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

## Environment variables

None are required for local development — sensible defaults are used when
they're unset. All are read via `os.environ` in `config/settings.py`.

| Variable | Purpose | Local default |
|---|---|---|
| `SECRET_KEY` | Django secret key | insecure fallback key (fine for local dev only) |
| `DEBUG` | Enable Django debug mode | `False` (set to `True` locally if you want tracebacks) |
| `DATABASE_URL` | Postgres connection string (e.g. `postgres://user:pass@host:5432/db`) | unset → falls back to local `db.sqlite3` |
| `RENDER_EXTERNAL_HOSTNAME` | Render deployment hostname, added to `ALLOWED_HOSTS` | unset |
| `RAILWAY_PUBLIC_DOMAIN` | Railway deployment hostname, added to `ALLOWED_HOSTS`/CSRF trusted origins | unset |
| `DJANGO_SUPERUSER_USERNAME` / `DJANGO_SUPERUSER_EMAIL` / `DJANGO_SUPERUSER_PASSWORD` | Used by `manage.py create_superuser_env` to bootstrap an admin account non-interactively | unset (command no-ops without a password) |

For local development you can skip all of these and the app runs against
SQLite with `DEBUG=False`.

## Database

- **Local dev**: no `DATABASE_URL` set → uses SQLite (`db.sqlite3` in the
  project root). Nothing else to configure.
- **Production**: set `DATABASE_URL` to a PostgreSQL connection string (this
  is what Render/Railway inject automatically) and `psycopg2-binary` (already
  in `requirements.txt`) handles the driver.

## Running it

```bash
python manage.py migrate
python manage.py createsuperuser        # or set DJANGO_SUPERUSER_* env vars and run:
# python manage.py create_superuser_env

# Seed the chart of accounts, an open accounting period, and a retail
# storefront warehouse (required before you can post a sale or PO):
python manage.py seed_erp
# add --demo to also create sample products and a supplier:
python manage.py seed_erp --demo

python manage.py runserver
```

Then visit:

- `/` — executive dashboard (login required)
- `/pos/` — point of sale
- `/inventory/` — stock & products
- `/purchasing/orders/` — purchase orders
- `/accounting/accounts/` — chart of accounts, trial balance, P&L, balance sheet
- `/admin/` — Django admin

## Tests

```bash
python manage.py test
```

## Static checks

```bash
python manage.py check              # Django system checks
python manage.py makemigrations --check --dry-run   # fails if models drifted from migrations
```

## Deployment

`build.sh` and `render.yaml` are set up for Render/Railway-style platforms:
install dependencies, run `collectstatic`, run `migrate`, then serve with
`gunicorn config.wsgi:application`. Static files are served via WhiteNoise.
