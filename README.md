# oshkelosh
### E-comm framework using Python/Flask & SQLite

The goal is to create a modular e-commerce framework using Flask and SQLite.
To start with, it will be built for the Printfull api and PayPal api as the payment proccessor. But more POD and payment proccessors will be added later.

This is not a fully featured package like wordpress, but rather a starting point for creating your own ecomm sites. Programming skills is required, especially for html/js/css and python/jinja.

Setup to be done via the .env file. Reference the .env_sample, or simply remove the _sample part of the filename

## Installation

1. Clone the repo:
   ```
   git clone https://github.com/yourusername/oshkelosh.git
   cd oshkelosh
   ```

2. Install Redis-Server:
   Download and install Redis from the official site (redis.io/download) or use a package manager
   ```ubuntu
   sudo apt install redis-server
   sudo systemctl start redis-server
   sodu systemctl enamble redis-server
   ```
   or
   Install Valkey if redis-server is unavailable
   ```arch
   sudo pacman -S valkey
   sudo systemctl start valkey
   sodu systemctl enamble valkey
   ```

3. Create a virtual environment and activate it:
   ```
   python -m venv .venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

4. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

5. Copy and configure `.env`:
   ```
   cp .env_sample .env
   ```
   Edit `.env` with your super secret 'APP_SECRET' and 'FLASK_ENV'. Flask environments: 'development', 'production', 'testing', 'default'

## Usage

1. Run the development server:
   ```
   python3 run.py
   ```
   Visit `http://localhost:5000` to access the site.

### Key Features
- **Product Management**: Add/edit products via admin panel, integrated with various suppliers.
- **Cart & Checkout**: Session-based cart with PayPal Express Checkout.
- **Order Tracking**: SQLite-stored orders with webhook support for status updates.
- **Modular Design**: Easy to extend processors in `app/processor.py` (e.g., add Stripe or Guten).

Customize templates in `app/templates/` and static assets in `app/static/`.

## Project Structure
```
oshkelosh/
├── run.py                 # Oshkelosh entry point
├── app/
│   ├── __init__.py
│   ├── processor.py       # Integration manager(Suppliers, Payments and Services)
│   │
│   ├── main/              # Main blueprint (Index, Products/Categories and login)
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   └── forms.py
│   ├── admin/             # Admin blueprint (Dashboard, Product/Payment & User management)
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   └── forms.py
│   ├── user/              # User blueprint (User profile, Cart & Checkout)
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   └── forms.py
│   │
│   ├── addons/             # Externally loaded modules
│   │   ├── __init__.py
│   │   ├── styles/         # Templates and static files for 'main' and 'user' blueprints
│   │   ├── payments/       # Scripts for interacting with payment proccessors
│   │   ├── suppliers/      # Scripts for interacting with suppliers
│   │   └── messaging/      # Scripts for sending communication with clients and admin
│   │
│   ├── database/
│   │   ├── __init__.py
│   │   ├── migrations.py   # Database creation
│   │   ├── models.py       # Database interaction
│   │   └── schema.py       # Databse setup/layout
│   │
│   └── helpers/
│       └── __init__.py     # Various functions for static/template routes and site/style data
│
├── tests/
│
├── data/                  # SQLite DB (gitignored)
│   ├── database.db
│   └── images/            # Product images
│
├── .env                   # SECRET_KEY and FLASK_ENV (gitignored)
│
├── flask_config.py              # Flask environment configs
├── requirements.txt
└── README.md
```

## Configuration
- `.env` vars:
  - `APP_SECRET='super_secret_string'`
  - `FLASK_ENV='development'`

For production, set `FLASK_ENV=production`

## Contributing
Fork the repo, create a feature branch, and submit a PR. Focus on modularity and tests (use `pytest`).

## License
GNU-GPL3. See [LICENSE](LICENSE) for details.
```
