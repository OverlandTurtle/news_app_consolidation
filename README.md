# News App Capstone

A simple Django news platform with three roles:

- **Readers** subscribe to publishers/journalists and read approved articles.
- **Journalists** create and manage their own article drafts.
- **Editors** approve pending articles for publishing.

On approval, the app emails subscribers and attempts to post to X (Twitter) if configured.

---

## Quick start

## Run locally

```bash
# from the project root (where manage.py is)
python -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt

python manage.py migrate
python manage.py setup_roles
python manage.py createsuperuser
python manage.py runserver
```

Open:
- App: `http://127.0.0.1:8000/`
- Admin: `http://127.0.0.1:8000/admin/`

---

## MariaDB setup (fresh DB)

Start MariaDB:

```bash
brew services start mariadb
```

Create DB/user:

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

Update `news_capstone/settings.py`:

```python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": "news_capstone_db",
        "USER": "news_capstone_user",
        "PASSWORD": "YOUR_PASSWORD_HERE",
        "HOST": "127.0.0.1",
        "PORT": "3306",
        "OPTIONS": {"charset": "utf8mb4"},
    }
}
```

---

## Roles + permissions

Run once after migrations:

```bash
python manage.py setup_roles
```

- **Reader**: view articles
- **Editor**: view/change/delete articles
- **Journalist**: add/view/change/delete articles

---

## Email + X posting on approval

When an editor approves an article:
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
python manage.py test news_app
```

---

## Newsletters

Newsletters follow the same basic workflow as articles:

- **Readers** can browse approved newsletters.
- **Journalists** can create and manage their own newsletter drafts.
- **Editors** can approve pending newsletters.

Useful pages:

- Reader list: `http://127.0.0.1:8000/newsletters/`
- Reader detail: `http://127.0.0.1:8000/newsletters/<id>/`
- Journalist drafts: `http://127.0.0.1:8000/my-newsletters/`
- Editor pending: `http://127.0.0.1:8000/editor/newsletters/pending/`

Notes:
- Newsletters can be **independent** (no publisher) or linked to a publisher.
- Approval rules match articles:
  - Independent items: any editor can approve
  - Publisher-linked items: only editors assigned to that publisher can approve

---

## Editors can create publishers (UI)

Editors can add new publishers from the normal UI (not only the admin):

- Create publisher: `http://127.0.0.1:8000/publishers/create/`

When an editor creates a publisher, the editor is assigned to that publisher by default (to reduce admin friction).

---

## Editor manage pages (update/delete)

Editors can also view/update/delete content via the editor manage pages:

- Manage articles: `http://127.0.0.1:8000/editor/articles/`
- Manage newsletters: `http://127.0.0.1:8000/editor/newsletters/`

---

## Style (flake8)

This project includes a `.flake8` config and passes linting:

```bash
flake8 .
```

