#  Finance Management System API

A RESTful backend API built with **Django REST Framework** for managing personal finances, including authentication, budgets, cards, currencies, and transactions.

This project is **API-first** and is designed to be consumed by frontend or mobile applications.

---

##  Features

###  Authentication & User Management
- User signup with email verification
- Login & JWT-based authentication
- Token refresh
- Profile management (view, update, delete)
- Password change
- Account statistics

###  Budgets
- Create, update, delete budgets
- Activate / deactivate budgets
- Track budget progress
- Spending history per budget
- Alerts & overview
- Group budgets by category or period

###  Cards & Currencies
- Manage user cards
- Set default card
- Update card balance
- Card statistics & summaries
- Currency list & conversion
- Exchange rates (latest & historical)

###  Transactions
- Income & expense tracking
- Categories & tags
- Bulk delete transactions
- Filter by date, card, category
- Monthly trends & statistics
- Recent transactions

###  API Documentation
- Interactive Swagger (OpenAPI) documentation

---

##  Tech Stack

- **Python**
- **Django**
- **Django REST Framework**
- **SQLite** (default database)
- **JWT Authentication (SimpleJWT)**
- **drf-spectacular** (Swagger / OpenAPI)
- **django-filter**

---

##  API Modules Overview

###  Auth (`/api/auth/`)
| Method | Endpoint |
|------|---------|
| GET | `/check-email/` |
| GET | `/check-username/` |
| POST | `/signup/` |
| POST | `/verify-code/` |
| POST | `/resend-code/` |
| POST | `/complete-registration/` |
| POST | `/login/` |
| POST | `/logout/` |
| POST | `/token/refresh/` |
| GET | `/profile/` |
| PUT / PATCH | `/profile/` |
| POST | `/profile/change-password/` |
| DELETE | `/profile/delete/` |
| GET | `/profile/statistics/` |

---

###  Budgets (`/api/budgets/budgets/`)
| Method | Endpoint |
|------|---------|
| GET / POST | `/` |
| GET / PUT / PATCH / DELETE | `/{id}/` |
| GET | `/{id}/progress/` |
| GET | `/{id}/spending_history/` |
| POST | `/{id}/toggle_active/` |
| GET | `/active/` |
| GET | `/alerts/` |
| GET | `/by_category/` |
| GET | `/by_period/` |
| GET | `/overview/` |

---

###  Cards & Currencies (`/api/cards/`)
#### Card Types
- `GET /card-types/`
- `GET /card-types/{id}/`

#### Cards
- `GET /cards/`
- `POST /cards/`
- `GET /cards/{id}/`
- `PUT / PATCH / DELETE /cards/{id}/`
- `POST /cards/{id}/change_status/`
- `POST /cards/{id}/set_default/`
- `POST /cards/{id}/update_balance/`
- `GET /cards/{id}/transaction_summary/`
- `GET /cards/statistics/`
- `GET /cards/total_balance/`

#### Currencies & Exchange Rates
- `GET /currencies/`
- `GET /currencies/{id}/`
- `POST /currencies/convert/`
- `GET /exchange-rates/`
- `GET /exchange-rates/{id}/`
- `GET /exchange-rates/latest/`

---

###  Transactions (`/api/transactions/`)
#### Categories
- `GET /categories/`
- `POST /categories/`
- `GET /categories/{id}/`
- `PUT / PATCH / DELETE /categories/{id}/`
- `GET /categories/expense/`
- `GET /categories/income/`

#### Tags
- `GET /tags/`
- `POST /tags/`
- `GET /tags/{id}/`
- `PUT / PATCH / DELETE /tags/{id}/`
- `GET /tags/{id}/transactions/`

#### Transactions
- `GET /transactions/`
- `POST /transactions/`
- `GET /transactions/{id}/`
- `PUT / PATCH / DELETE /transactions/{id}/`
- `POST /transactions/bulk_delete/`
- `GET /transactions/by_card/`
- `GET /transactions/by_category/`
- `GET /transactions/by_date/`
- `GET /transactions/monthly_trend/`
- `GET /transactions/recent/`
- `GET /transactions/statistics/`

---

##  Authentication

This API uses **JWT (Bearer Token)** authentication.

Add the token to request headers:

```http
Authorization: Bearer <access_token>
```


##  API Documentation (Swagger)
Once the server is running, access Swagger UI at:
[text](http://127.0.0.1:8000/api/swagger/)




##  Local Setup
```bash
git clone https://github.com/yourusername/finance-api.git
cd finance-api
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```




##  Environment variables
Create .env file:

```bash
DEBUG=True
SECRET_KEY=your-secret-key
ALLOWED_HOSTS=127.0.0.1,localhost

DB_ENGINE=django.db.backends.sqlite3
DB_NAME=db.sqlite3
```


##  Run migrations & server

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```



##  Database
	•	Default database: SQLite
	•	Designed to allow easy switch to PostgreSQL via environment variables



##  Notes
	•	This is a backend-only project (no frontend UI)
	•	Root URL / intentionally returns 404
	•	All functionality is exposed via REST APIs


