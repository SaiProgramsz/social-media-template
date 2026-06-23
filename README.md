# study.net

Student-friendly social app for learning + studying.

## MVP modules

- Feed: study updates (posts)
- Study rooms: create/join timed sessions
- Notes: share note sets
- Q&A: questions + answers
- Safety: report/block

## Local setup (Windows PowerShell)

1) Install dependencies (system Python; no venv):

```powershell
pip install -r requirements.txt
```

2) Set environment variables:

```powershell
$env:DJANGO_SECRET_KEY = "change-me"
$env:DJANGO_DEBUG = "1"
```

3) Run migrations + server:

```powershell
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```
This project uses SQLite by default (no PostgreSQL required).
