# fastapi-practice

Small FastAPI practice project with:

- User registration + login
- JWT auth (Bearer token)
- Simple todo CRUD backed by Turso (libSQL / SQLite via SQLAlchemy)

## Requirements

- Python 3.10+
- MySQL (or compatible) database

Python deps are listed in `requirements.txt`.

## Setup

1) Create and activate a virtualenv

```bash
python -m venv .venv
source .venv/bin/activate
```

2) Install dependencies

```bash
pip install -r requirements.txt
```

3) Configure the app

The app reads configuration from environment variables in `app/main.py`:

- Turso (recommended): `TURSO_DATABASE_URL` + `TURSO_AUTH_TOKEN`
- Local fallback: `DATABASE_URL` (default: `sqlite:///./local.db`)
- `SECRET_KEY` (default): `dev-secret-key-change-me`

Update these before running (especially `SECRET_KEY`).

4) Create the database schema

The code expects `users` and `todos` tables with at least these columns:

```sql
CREATE TABLE users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT NOT NULL UNIQUE,
  email TEXT NOT NULL,
  password TEXT NOT NULL
);

CREATE TABLE todos (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  todo TEXT NOT NULL,
  body TEXT DEFAULT '',
  completed INTEGER NOT NULL DEFAULT 0,
  created_by INTEGER NOT NULL,
  FOREIGN KEY (created_by) REFERENCES users(id)
);
```

## Run

```bash
uvicorn app.main:app --reload
```

Then open:

- `http://127.0.0.1:8000/` (health check)
- `http://127.0.0.1:8000/docs` (Swagger UI)

## API

### Auth

Most todo endpoints require an `Authorization` header:

```
Authorization: Bearer <access_token>
```

### Endpoints

- `GET /` → `{"Hello":"World"}`
- `POST /register` → register a user (params: `username`, `email`, `password`)
- `POST /login` → login (params: `username`, `password`) and receive `access_token`
- `GET /todos` → list todos for the authenticated user
- `POST /todos` → create a todo (params: `todo`, optional `body`)
- `PUT /todos/{todo_id}` → update a todo you own (optional params: `todo`, `body`, `completed`)
- `DELETE /todos/{todo_id}` → delete a todo you own

### Example curl flow

Register:

```bash
curl -X POST "http://127.0.0.1:8000/register?username=alice&email=alice@example.com&password=secret"
```

Login:

```bash
curl -X POST "http://127.0.0.1:8000/login?username=alice&password=secret"
```

Create a todo (replace `<TOKEN>`):

```bash
curl -X POST "http://127.0.0.1:8000/todos?todo=Buy%20milk&body=2%20liters" \
  -H "Authorization: Bearer <TOKEN>"
```

List todos:

```bash
curl "http://127.0.0.1:8000/todos" -H "Authorization: Bearer <TOKEN>"
```

## Deploy (Vercel)

This repo includes an `index.py` that re-exports the FastAPI `app` from `app/main.py`, which matches Vercel’s Python/FastAPI entrypoint detection.

### 1) Set environment variables

In your Vercel project settings, add:

- `TURSO_DATABASE_URL`
- `TURSO_AUTH_TOKEN`
- `SECRET_KEY` (strong random value)
- Optional: `ACCESS_TOKEN_EXPIRE_HOURS` (default `24`)

### 2) Deploy

Using the Vercel CLI:

```bash
vercel deploy
```

Or connect the Git repo in the Vercel dashboard and deploy from there.
