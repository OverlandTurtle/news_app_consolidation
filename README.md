# News App Capstone (Consolidation)

A simple Django news platform with three roles:

- **Readers** subscribe to publishers/journalists and read approved articles.
- **Journalists** create and manage their own article drafts.
- **Editors** approve pending articles for publishing.

On approval, the app emails subscribers and attempts to post to X (Twitter) if configured.

---

## What’s in this repo (capstone requirements)

- **Branch workflow**: work was done on `docs` (Sphinx) and `container` (Docker), then merged into `main`.
- **Sphinx documentation** lives in `docs/` and builds to `docs/build/html/`.
- **Docker** support via `Dockerfile` + `docker-compose.yml` (Django + MariaDB).

---

## Quick start (run locally)

### 1) Create + activate venv, install deps

```bash
# from the project root (where manage.py is)
python -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
```

### 2) Create a local `.env` (NOT committed)

Create a file called `.env` in the project root.

Minimum example:

```env
DJANGO_SECRET_KEY=change-me
DJANGO_DEBUG=1
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost

DB_NAME=news_capstone_db
DB_USER=news_capstone_user
DB_PASSWORD=your_password_here
DB_HOST=127.0.0.1
DB_PORT=3306
```

A safe placeholder file is provided as `.env.example`.

### 3) MariaDB setup (fresh DB)

Start MariaDB:

```bash
brew services start mariadb
```

Create DB/user (one-time):

```bash
mysql -u root -p
```

```sql
CREATE DATABASE news_capstone_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'news_capstone_user'@'localhost' IDENTIFIED BY 'YOUR_PASSWORD_HERE';
GRANT ALL PRIVILEGES ON news_capstone_db.* TO 'news_capstone_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### 4) Migrate + create roles + run server

```bash
python manage.py migrate
python manage.py setup_roles
python manage.py createsuperuser
python manage.py runserver
```

Open:

- App: `http://127.0.0.1:8000/`
- Admin: `http://127.0.0.1:8000/admin/`

---

## Sphinx documentation

Build the docs (from project root):

```bash
cd docs && make html
```

Output:

- `docs/build/html/index.html`

---

## Docker (Django + MariaDB using Docker Compose)

### 1) Create `.env.docker` (local-only, NOT committed)

Create a file named `.env.docker` in the project root:

```env
# Django
DJANGO_SECRET_KEY=dev-only-secret-key-change-me
DJANGO_DEBUG=1
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# Database (points Django to the *db* service inside compose)
DB_NAME=news_capstone_db
DB_USER=news_capstone_user
DB_PASSWORD=password123
DB_HOST=db
DB_PORT=3306
```

### 2) Build + run

```bash
docker compose up --build
```

In another terminal (first time / after schema changes), run migrations:

```bash
docker compose run --rm web python manage.py migrate
```

Optional: create a superuser inside the container:

```bash
docker compose run --rm web python manage.py createsuperuser
```

Then visit:

- `http://127.0.0.1:8000/`

Stop containers:

```bash
docker compose down
```

Reset DB volume (fresh start):

```bash
docker compose down -v
```

---

## Roles + permissions

Run once after migrations:

```bash
python manage.py setup_roles
```

- **Reader**: view approved articles/newsletters (with subscription rules)
- **Editor**: approve/manage content
- **Journalist**: create/manage drafts

---

## Email + X posting on approval

When an editor approves an article/newsletter:

- Email is sent to subscribed Readers (publisher + journalist subscriptions)
- X posting is attempted only if env vars exist:
  - `X_BEARER_TOKEN`
  - `X_POST_URL`

If missing, posting is skipped (approval still succeeds).

---

## REST API (Basic Auth)

Feed (Reader-only): approved articles matching the Reader’s subscriptions:

```bash
curl -i -u USERNAME:PASSWORD http://127.0.0.1:8000/api/me/feed/
```

Article detail (Reader-only, subscription-guarded):

```bash
curl -i -u USERNAME:PASSWORD http://127.0.0.1:8000/api/articles/ID/
```

---

## Tests

```bash
python manage.py test
```

---

## Style (Black + flake8)

Format:

```bash
black .
```

Lint:

```bash
flake8 .
```
