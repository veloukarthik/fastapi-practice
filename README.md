# fastapi-practice

Small FastAPI practice project with:

- User registration + login
- JWT auth (Bearer token)
- Simple todo CRUD backed by MySQL (via SQLAlchemy + PyMySQL)

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

The app currently uses hard-coded values in `app/main.py`:

- `DATABASE_URL` (default): `mysql+pymysql://root:root@localhost:8080/pythondb`
- `SECRET_KEY` (default): `your-secret-key-change-this-in-production`

Update these before running (especially `SECRET_KEY`).

4) Create the database schema

The code expects `users` and `todos` tables with at least these columns:

```sql
CREATE TABLE users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(255) NOT NULL UNIQUE,
  email VARCHAR(255) NOT NULL,
  password VARCHAR(255) NOT NULL
);

CREATE TABLE todos (
  id INT AUTO_INCREMENT PRIMARY KEY,
  todo VARCHAR(255) NOT NULL,
  body TEXT,
  completed TINYINT(1) NOT NULL DEFAULT 0,
  created_by INT NOT NULL,
  INDEX (created_by),
  CONSTRAINT fk_todos_users FOREIGN KEY (created_by) REFERENCES users(id)
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

