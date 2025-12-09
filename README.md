# oshkelosh
### E-comm framework using Python/Flask & SQLite

The goal is to create a modular e-commerce framework using Flask.
To start with, it will be built for the Printfull api and PayPal api as the payment proccessor. But more POD and payment proccessors will be added later.

This is not a fully featured package like wordpress, but rather a starting point for creating your own ecomm sites. Programming skills is required, especially for html/js/css and python/jinja.

Setup to be done via the .env file. Reference the .env_sample, or simply remove the _sample part of the filename


######################################################################

## Please Note

### This project is not even close to ready for production!

### Progress:
As of now, the app launches with sqlite setting up.

### Working on:
I'm creating addons for Printful, Paypal and Postmark to get basic functionality ready

### Still to do:
- Create basic addons
- Finish up models for basic functionality
- Finish all routes for blueprints
- Finish 'basic' style
- Clean up and Standardize code
- Start expanding on standard addons
- Create extra styles
- Create 'shop' for addons and styles
- Create Docs for addon and style creation
- Create value-add addons(non-standard)

######################################################################


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
   python3 wsgi.py
   ```
   Visit `http://localhost:5000` to access the site.


### Key Features
- **Product Management**: Add/edit products via admin panel, integrated with various suppliers.
- **Cart & Checkout**: Session-based cart with PayPal Express Checkout.
- **Order Tracking**: SQLite-stored orders with webhook support for status updates.
- **Modular Design**: Easy to extend processors in `app/processor.py` (e.g., add Stripe or Guten).

Customize templates in `app/styles/<style>/templates` and static assets in `app/styles/<style>/theme/<theme>/static`.

## Project Structure
```
oshkelosh/
├── wsgi.py                 # Oshkelosh entry point
├── app/
│   ├── __init__.py         # Main app initialization
│   │
│   ├── config.py           # App config(development, production, testing, default)
│   │
│   ├── addons/             # Shop addons (Suppliers, Payment Proccessors, notification, ect)
│   │   ├── __init__.py
│   │   ├── <addon>
│   │   └── <addon>
│   │
│   ├── blueprints/         # Blueprint (Main, User, Admin)
│   │   ├── __init__.py
│   │   ├── main/
│   │   │   ├── __init__.py
│   │   │   └── routes.py
│   │   ├── user/
│   │   │   ├── __init__.py
│   │   │   └── routes.py
│   │   └── admin/
│   │       ├── __init__.py
│   │       └── routes.py
│   │
│   ├── database/           # Database scripts
│   │   ├── __init__.py
│   │   ├── migrations.py
│   │   ├── schema.py
│   │   └── defaults.py
│   │
│   ├── models/             # Database Interaction Classes
│   │   └── models.py
│   │
│   ├── styles/             # Multiple styles can be loaded, with each style having multiple themes(static)
│   │   ├── <style>
│   │   │   ├── templates/
│   │   │   └── theme/
│   │   │       ├── <theme>
│   │   │       │   └── static/
│   │   │       └── <theme>
│   │   ├── <style>
│   │   └── <style>
│   │
│   ├── templates/
│   │   └── core/           # Default templates for 'admin'
│   │
│   └── static/             # Static files for admin and other non themed assets 
│
├── tests/
│
├── instance/               # SQLite DB (gitignored)
│   ├── database.db
│   └── images/             # Product images
│
├── .env                    # SECRET_KEY and FLASK_ENV (gitignored)
│
├── requirements.txt
│
└── README.md
```

## Configuration
- `.env` vars:
  - `APP_SECRET='super_secret_string'`
  - `FLASK_ENV='development'`


## Production

I reccomend following the Digital Ocean tutorial for setting up a Flask site with gunicorn and nginx. Check it out [here](https://www.digitalocean.com/community/tutorials/how-to-serve-flask-applications-with-gunicorn-and-nginx-on-ubuntu-22-04#step-5-configuring-nginx-to-proxy-requests)

For production, set `FLASK_ENV=production`

## Contributing
Fork the repo, create a feature branch, and submit a PR. Focus on modularity and tests (use `pytest`).

## License
GNU-GPL3. See [LICENSE](LICENSE) for details.
```
