# Address Book API

A minimal REST API built with **FastAPI** for managing an address book. Every
address carries its geographic coordinates, is validated on input and is stored
in an **SQLite** database. Besides create / read / update / delete, the API can
return all addresses within a given distance of a point.

There is no GUI: use the interactive Swagger UI that FastAPI generates at
`http://127.0.0.1:8000/docs`.

---

## Requirements

- Python **3.11 or newer** (`python --version`)
- `pip` (ships with Python)

No database server is needed — SQLite is built into Python and the database
file (`address_book.db`) is created automatically on first start.

---

## How to run

All commands are run from the project folder (the one containing this README).

### macOS / Linux

```bash
cd address-book
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Windows (PowerShell)

```powershell
cd address-book
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

> If PowerShell blocks the activation script, run
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, or use
> `.venv\Scripts\activate.bat` from `cmd.exe` instead.

When the server is running you will see log lines such as:

```
2026-10-28 10:00:00 | INFO     | app.db.session | Database initialised at sqlite:///./address_book.db
2026-10-28 10:00:00 | INFO     | app.main | Application started (version 1.0.0)
```

Then open:

| URL | What |
| --- | --- |
| http://127.0.0.1:8000/docs | Swagger UI (try every endpoint here) |
| http://127.0.0.1:8000/redoc | ReDoc documentation |
| http://127.0.0.1:8000/health | Liveness check |

Stop the server with `Ctrl+C`. `--reload` restarts it on code changes; leave it
out outside development.

### Run the tests

```bash
pip install -r requirements-dev.txt
pytest
```

The tests use a temporary database, so your `address_book.db` is never touched.
Optional lint check: `ruff check .`

---

## Configuration

Settings are read from environment variables (or a `.env` file — see
`.env.example`). All are optional.

| Variable | Default | Description |
| --- | --- | --- |
| `ADDRESS_BOOK_DATABASE_URL` | `sqlite:///./address_book.db` | SQLAlchemy database URL |
| `ADDRESS_BOOK_LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `ADDRESS_BOOK_SQL_ECHO` | `false` | Log every SQL statement |

Example: `ADDRESS_BOOK_LOG_LEVEL=DEBUG uvicorn app.main:app --reload`

---

## API

| Method | Path | Description | Success |
| --- | --- | --- | --- |
| `POST` | `/addresses` | Create an address | `201` |
| `GET` | `/addresses?offset=0&limit=100` | List addresses (paginated) | `200` |
| `GET` | `/addresses/{id}` | Get one address | `200` |
| `PUT` | `/addresses/{id}` | Replace all fields | `200` |
| `PATCH` | `/addresses/{id}` | Update only the fields sent | `200` |
| `DELETE` | `/addresses/{id}` | Delete an address | `204` |
| `GET` | `/addresses/nearby?latitude=&longitude=&distance_km=&limit=` | Addresses within a distance, nearest first | `200` |

Errors: `404` for an unknown id, `422` for invalid input (with details on which
field failed and why).

### Validation rules

| Field | Rule |
| --- | --- |
| `label` | optional, 1–100 characters |
| `street` | required, 1–200 characters (street and house number) |
| `postal_code` | required, 2–20 letters/digits/spaces/hyphens |
| `city` | required, 1–100 characters |
| `country` | required, ISO 3166-1 alpha-2 code (`de` is stored as `DE`) |
| `latitude` | required, −90 … 90 (decimal degrees, WGS 84) |
| `longitude` | required, −180 … 180 |

Leading/trailing whitespace is trimmed, unknown fields are rejected, and
`PATCH` refuses an empty body or `null` for any field except `label`. The
database additionally enforces the coordinate ranges with `CHECK` constraints.

### Example requests (curl)

```bash
# Create
curl -X POST http://127.0.0.1:8000/addresses \
  -H "Content-Type: application/json" \
  -d '{"label": "Brandenburg Gate", "street": "Pariser Platz", "postal_code": "10117",
       "city": "Berlin", "country": "DE", "latitude": 52.516275, "longitude": 13.377704}'

# Update one field
curl -X PATCH http://127.0.0.1:8000/addresses/1 \
  -H "Content-Type: application/json" -d '{"label": "Gate"}'

# Find everything within 5 km of Alexanderplatz
curl "http://127.0.0.1:8000/addresses/nearby?latitude=52.5219&longitude=13.4132&distance_km=5"

# Delete
curl -X DELETE http://127.0.0.1:8000/addresses/1
```

A `nearby` result is a normal address plus `distance_km`:

```json
[
  {
    "id": 1,
    "label": "Brandenburg Gate",
    "street": "Pariser Platz",
    "postal_code": "10117",
    "city": "Berlin",
    "country": "DE",
    "latitude": 52.516275,
    "longitude": 13.377704,
    "created_at": "2026-10-28T10:00:00.555155Z",
    "updated_at": "2026-10-28T10:00:00.555161Z",
    "distance_km": 2.482
  }
]
```

### How the distance search works

SQLite has no geospatial functions, so the search runs in two steps:

1. **Bounding-box pre-filter (SQL).** A latitude/longitude box that is
   guaranteed to contain the search circle is computed and queried using an
   index on `(latitude, longitude)`. Boxes that cross the ±180° meridian or
   contain a pole are handled.
2. **Exact filter (Python).** The great-circle distance to each candidate is
   computed with the haversine formula; candidates outside the radius are
   dropped and the rest sorted by distance.

This keeps the database doing the heavy lifting while the result stays exact
(on a spherical earth model, accurate to ~0.5 %).

---

## Project structure

```
address-book/
├── app/
│   ├── main.py              # App factory, lifespan, request logging, error handlers
│   ├── api/routes/
│   │   └── addresses.py     # HTTP endpoints (thin layer)
│   ├── core/
│   │   ├── config.py        # Settings (pydantic-settings, env vars / .env)
│   │   ├── exceptions.py    # Domain exceptions
│   │   └── logging.py       # Logging configuration
│   ├── db/
│   │   ├── base.py          # SQLAlchemy declarative base
│   │   └── session.py       # Engine, session dependency, table creation
│   ├── models/address.py    # ORM model (table + constraints + index)
│   ├── schemas/address.py   # Pydantic request/response models & validation
│   ├── services/addresses.py# Business logic: CRUD + distance search
│   └── utils/geo.py         # Haversine distance and bounding box
├── tests/                   # pytest suite (API + geo unit tests)
├── requirements.txt         # Runtime dependencies
├── requirements-dev.txt     # + test / lint tools
├── pyproject.toml           # pytest and ruff configuration
└── .env.example             # Example configuration
```

**Layers:** routes handle HTTP only, services hold the logic and raise domain
exceptions, and `app.main` maps those exceptions to HTTP status codes. This keeps
the business logic testable without HTTP and easy to reuse.

## Libraries used

| Library | Why |
| --- | --- |
| FastAPI | Web framework, dependency injection, OpenAPI / Swagger docs |
| Uvicorn | ASGI server |
| SQLAlchemy 2 | ORM with typed models and SQLite support |
| Pydantic v2 | Request validation and response serialisation |
| pydantic-settings | Typed configuration from environment variables |
| pytest + httpx | Tests via FastAPI's `TestClient` |

## Possible next steps

- Database migrations with Alembic instead of `create_all` on startup.
- Geocoding (e.g. Nominatim) to fill coordinates from the address text.
- SpatiaLite or PostGIS for large datasets.
- Authentication if the API is exposed publicly.
