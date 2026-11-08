# TourVibe: Pack, Go & Explore Bangladesh

TourVibe is the new version of our 2024 **Pack-Go** project, rebuilt from the start as an
individual final project. It is a web application to discover tourist places in Bangladesh,
plan the cost of a trip and book tour packages.

## What is new compared with Pack-Go (2024)

| Pack-Go (2024) | TourVibe |
|---|---|
| One list of tours with a price per day | 23 places in all 8 divisions with season, cost, tips, map link, photo gallery |
| Anyone could add, edit or delete tours | Only admins can manage content; travelers cannot |
| Cart started at 2 and crashed on wrong numbers | Cart checks every number; seats are checked so tours are never overbooked |
| Order with no status | Orders are Pending / Confirmed / Cancelled, with PDF invoice and CSV export |
| Profile page crashed for some users | Every user gets a profile automatically (photo, phone, address) |
| No tests | 71 automated tests |
| No API | REST API with token login |
| — | Reviews and ratings, wishlist |
| — | Trip planner: short route (nearest-neighbour) and full cost estimate |
| — | "Where to go?" suggestions scored by season, budget, interest and rating |
| — | Admin dashboard with charts |

## Built with

- Python 3, Django 5 (MVT pattern), SQLite
- Django REST Framework (session and token login)
- Bootstrap 5, Bootstrap Icons, Chart.js, JavaScript
- ReportLab (PDF invoices)

## Apps

```
packandgo/    settings, main urls, home page and dashboards
userprofile/  sign up, login, profile with photo
tour/         divisions, categories, places, photo gallery, reviews, wishlist
booking/      tour packages, cart, checkout, orders, invoice
planner/      trip cost planner and "where to go" suggestions
api/          REST API
```

## How to run (Windows)

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_data
python manage.py runserver
```

Open http://127.0.0.1:8000

| Role | Username | Password |
|---|---|---|
| Admin | admin | Admin@12345 |
| Traveler | ekram (also nabila, faiza, jannatul, mahmud, sadia) | Traveler@2026 |

## Tests

```
python manage.py test
```

## REST API

Open http://127.0.0.1:8000/api/ to browse it.

| Method | URL | Who |
|---|---|---|
| GET | /api/destinations/?q=&division=&category=&month=&max_price=&sort= | Everyone |
| GET | /api/packages/, /api/reviews/, /api/categories/, /api/divisions/ | Everyone |
| POST/PUT/DELETE | /api/destinations/, /api/packages/ | Admin |
| POST | /api/reviews/ | Logged-in users |
| GET/POST | /api/orders/ | Logged-in users (own orders; admin sees all) |
| POST | /api/orders/<reference>/cancel/ | Owner or admin |
| POST | /api/orders/<reference>/set-status/ | Admin |
| GET | /api/plans/ | Logged-in users |
| POST | /api/planner/estimate/ | Everyone |
| POST | /api/planner/recommend/ | Everyone |
| POST | /api/token/ | Get a login token |

Example order:

```json
POST /api/orders/
{"items": [{"package": "sajek-valley-cloud-trip", "travelers": 2}],
 "contact_name": "Ekram", "contact_phone": "01712345678"}
```

## Note

Costs are planning estimates. Rules for places like the Sundarbans and Saint Martin's Island change,
so check the latest official information before travelling.
