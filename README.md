# PulseNotify — Flight Price Monitoring API

A Django REST Framework backend starter for the PulseNotify assignment. It includes PostgreSQL/Redis Docker services, split settings, JWT authentication, models, API routes, Celery tasks and a test scaffold.

## 1. Requirements

- Python 3.11 or 3.12
- Docker Desktop
- Git
- Postman

## 2. Setup

```bash
# Windows PowerShell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1

# macOS/Linux
python3.11 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
```

Copy `.env.example` to `.env`, then update the secret and database password.

```bash
# Windows PowerShell
Copy-Item .env.example .env

# macOS/Linux
cp .env.example .env
```

Start PostgreSQL and Redis:

```bash
docker compose up -d
docker compose ps
```

Create database tables:

```bash
python manage.py makemigrations pulse
python manage.py migrate
python manage.py createsuperuser
```

Start Django:

```bash
python manage.py runserver
```

## 3. Start Celery

Open two additional terminals, activate the same virtual environment in each, and run:

```bash
celery -A pulsenotify worker --loglevel=info
```

```bash
celery -A pulsenotify beat --loglevel=info
```

On Windows, Celery's default prefork pool can be problematic. For local development use:

```bash
celery -A pulsenotify worker --pool=solo --loglevel=info
```

## 4. API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/auth/register/` | Public user registration |
| POST | `/api/auth/login/` | Public JWT login |
| POST | `/api/alerts/` | Create an alert (JWT) |
| GET | `/api/alerts/` | List current user's alerts (JWT) |
| DELETE | `/api/alerts/<id>/` | Deactivate own alert (JWT) |
| GET | `/api/flights/price/?route=DEL-BOM` | Public mock price feed |
| GET | `/api/admin/summary/` | Admin-only statistics (JWT) |

For protected routes, send:

`Authorization: Bearer <access_token>`

## 5. Important implementation notes

- Registration deliberately ignores any `role` field supplied by the client.
- UserProfile is created by a `post_save` signal.
- Alert listing is scoped to `request.user`.
- Deleting an alert changes its status to `inactive`; it does not delete the row.
- The mock feed supports `DEL-BOM`, `BLR-HYD`, `DEL-BLR`, and `BOM-GOA`.
- Celery Beat is configured to call `pulse.tasks.check_prices` every 60 seconds.
- `check_prices` calls the local price endpoint using `requests.get()` and dispatches `send_notification.delay(...)`.
- Change the default admin user's profile role to `admin` in Django shell before testing the admin endpoint:

```bash
python manage.py shell
```

```python
from django.contrib.auth.models import User
u = User.objects.get(username="your-admin-username")
u.profile.role = "admin"
u.profile.save()
```

## 6. Run tests

Run the Django automated test suite:

```bash
python manage.py test
```

The included tests cover threshold comparison, notification creation, and user alert scoping. Expand them with API-level tests as part of your submission.

## 7. Postman API Testing

A Postman collection is included in the project:

`postman/PulseNotify.postman_collection.json`

The collection contains 13 API requests covering:

- User registration and login
- Duplicate registration and invalid login
- Creating, listing, and deactivating alerts
- Mock flight price lookup
- Admin summary access
- Authentication and authorization checks
- Unauthorized access and ownership validation


## 8. Before pushing to GitHub

- Ensure `.env` is not committed.
- Keep `.env.example` with placeholder values.
- Run migrations and tests.
- Export your Postman collection as JSON.
- Add screenshots or a short demo if your course asks for them.

## 9. Useful commands

```bash
docker compose down
docker compose down -v  # WARNING: deletes the local PostgreSQL volume/data
python manage.py check
python manage.py showmigrations
```
