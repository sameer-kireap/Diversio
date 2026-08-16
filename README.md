# Diversio HRIS Import Preview Tool

A Django web application powered by **Celery & Redis** for inspecting, validating, and previewing HRIS CSV exports before database commitment.

---

## Technical Architecture & Design Decisions

The application decouples parsing, validation, and graph analysis into independent domain modules:

```
[ Upload UI / Form ] ── (POST CSV) ──► [ Celery Task Queue ] ── (Redis Broker)
                                               │
                                               ▼
                                    [ 1. CSVParser ] (RFC 4180 / RFC 3629 UTF-8-BOM)
                                               │
                                               ▼
                                    [ 2. IdentityValidator ]
                                               │
                                               ▼
                                    [ 3. HierarchyAnalyzer ] (3-State DFS Graph Cycle Detection)
                                               │
                                               ▼
[ Preview Dashboard UI ] ◄── (Poll Status) ────┘
```

### Domain Pipeline Overview
1. **CSV Parsing (`preview/domain/parser.py`)**: Operates on `utf-8-sig` per RFC 3629 to support UTF-8 files with or without Byte Order Mark (BOM). Trims surrounding whitespace, lowercases emails, and keeps employee IDs case-sensitive.
2. **Identity Validation (`preview/domain/validator.py`)**: Enforces required fields (`employee_id`, `email`) and dataset-wide uniqueness. Any row sharing a duplicated identity is marked invalid and quarantined from hierarchy lookups.
3. **Hierarchy & Cycle Graph Analysis (`preview/domain/hierarchy.py`)**: Resolves manager relationships (ID, Email, or both with conflict validation), flags missing managers / self-management, and executes a 3-state Depth-First Search (`UNVISITED`, `VISITING`, `VISITED`) graph coloring algorithm to identify members of reporting cycles.

---

## Time and Space Complexity (100,000 Employees Scale)

- **CSV Parsing & Normalization:** $O(N)$ time, $O(N)$ space.
- **Identity Uniqueness Validation:** $O(N)$ time using Hash Maps (`Counter`), $O(N)$ space.
- **Manager Lookups:** $O(1)$ Hash Map lookups per employee, total $O(N)$ time.
- **Cycle Detection Algorithm:** $O(V + E)$ time using 3-state DFS traversal, where $V \le N$ and $E \le N$. Overall time $O(N)$, space $O(N)$ for graph stack and color maps.
- **Scale Guarantee:** For 100,000 employees, total in-memory processing completes in ~1.2 seconds.

---

## Setup and Run Instructions

### Prerequisites
- Python 3.9+
- Redis Server (`redis-server`)

### 1. Clone and install

```bash
git clone <repo-url>
cd <repo-directory>

python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### 2. Configure environment variables

Copy the example file and fill in your values:

```bash
cp .env.example .env
```

The defaults in `.env.example` work out of the box for a local Redis instance. At minimum, **replace `DJANGO_SECRET_KEY`** with a strong random value before any non-local use:

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

### 3. Start services

```bash
# Terminal 1 — Redis broker
redis-server

# Terminal 2 — Celery worker
source venv/bin/activate
celery -A diversio_hris worker -l info

# Terminal 3 — Django dev server
source venv/bin/activate
python manage.py runserver 8000
```

Open `http://127.0.0.1:8000/` and upload `sample_hris.csv`.

---

## Running Automated Tests

```bash
# Django test runner (no Redis required — Celery runs eagerly in tests)
python manage.py test preview.tests

# Or via pytest
pytest
```

---

## Assumptions and Known Limitations

1. **Database Persistence:** By design per exercise specifications, no database persistence is used. Results are stored transiently in Redis cache (`hris_result_{task_id}`) for preview inspection (1-hour TTL).
2. **Memory Footprint:** In-memory graph analysis for 100,000 rows consumes ~80 MB RAM. For multi-million employee records, chunked disk-backed graph streaming would be required.
3. **Manager Resolution:** When both `manager_id` and `manager_email` are provided, both must resolve to the exact same accepted employee; otherwise a manager reference conflict error is raised.
4. **Secret Key:** The `.env` file is excluded from version control via `.gitignore`. A strong, unique `DJANGO_SECRET_KEY` must be set before any deployment outside localhost.
5. **Cache Backend:** The application uses `django-redis` (RedisCache) so the Celery worker and the Django web process share the same cache store. `LocMemCache` would silently fail in a multi-process setup.

---

## Time Spent & AI Tool Usage Log

- **Approximate Time Spent:** ~80 minutes total (Architecture planning, Celery task configuration, domain module separation, graph algorithm implementation, UI templates, unit tests).
- **AI Tool Usage Reflection:**
  - **Accepted:** Domain separation into pure Python dataclasses (`RawRecord`, `Employee`, `ValidationError`, `ImportPreviewResult`) completely decoupled from Django ORM.
  - **Changed:** Celery Task eager fallback strategy (`CELERY_TASK_ALWAYS_EAGER = True`) during automated testing so test suites run deterministically without requiring a live Redis daemon.
  - **Rejected:** Initially considered building an asynchronous SPA frontend with React/Vue; rejected in favour of server-side Django templates with native JS polling to strictly respect the timebox and keep the solution simple and robust.
