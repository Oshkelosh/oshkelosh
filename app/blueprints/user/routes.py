from flask import (
    current_app,
    render_template,
    send_from_directory,
    render_template_string,
    Response,
    request,
    redirect,
    url_for,
    flash,
    session,
    jsonify
)

from flask_login import login_user, logout_user, login_required, current_user

from . import bp
from . import forms
from app.models import models
from app.utils import site_config 

import json, os, random
import bcrypt




@bp.route("/login", methods=["GET","POST"])
def login():
    form = forms.loginForm()
    if form.validate_on_submit():
        users = models.User.get(email=form.email.data)
        user = users[0] if users else None
        if user and user.check_password(form.password.data):
            login_user(user)
            if 'cart' in session:
                user.cart.extend(session['cart'])
                user.update()
                session.pop('cart', None)
            return redirect(url_for('main.index'))
        flash('Invalid login attempt')
    return render_template(
        "user/login.html",
        site = site_config.get_config("site_config"),
        login_form = form
    )


@bp.route("/logout")
def logout():
    logout_user()
    return render_template(
        "user/logout.html",
        site = site_config.get_config("site_config"),
    )

@bp.route("/signup", methods=["GET", "POST"])
def signup():
    form = forms.signupForm()
    if form.validate_on_submit():
        password = str(form.password.data)
        user_data = {
            "name": form.name.data,
            "surname": form.surname.data,
            "email": form.email.data,
            "phone": form.phone.data,
            "password": bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        }

        billing_address = {
            "type": "BILLING",
            "street": form.billing_street.data,
            "city": form.billing_city.data,
            "state": form.billing_state.data,
            "postal_code": form.billing_postal_code.data,
            "country": form.billing_country.data,
        }

        shipping_address = {
            "type": "SHIPPING",
            "street": form.shipping_street.data,
            "city": form.shipping_city.data,
            "state": form.shipping_state.data,
            "postal_code": form.shipping_postal_code.data,
            "country": form.shipping_country.data,
        }
        from app import db
        try:
            user = models.User.new(**user_data)
            if not user:
                flash("Something went wrong, could not register the user")
                return redirect(url_for("main.index"))
            user.add_address(**billing_address)
            user.add_address(**shipping_address)
            
            login_user(user)
            flash("Successfully registered!")
            return redirect(url_for("main.index"))

        except db.IntegrityError as e:
            if db.is_duplicate(e, 'email'):
                form.email.errors.append("This email is already registered.")
            else:
                flash("Something went wrong during client registration")
            return redirect(url_for("main.index"))

    return render_template(
        "user/signup.html",
        site = site_config.get_config("site_config"),
        signup_form = form
    )


@bp.route("/profile")
@login_required
def profile():
    addresses = models.Address.get(user_id=current_user.id)
    orders = models.Order.get(user_id = current_user.id)
    return render_template(
        "user/profile.html",
        site = site_config.get_config("site_config"),
        addresses = addresses,
        orders = orders
    )

@bp.route("/cart")
def cart():
    cart_products = []
    if current_user.is_authenticated:
        for entry in current_user.cart:
            products = models.Product.get(id=entry["product_id"])
            product = products[0] if products else None
            if product:
                details = {
                    "product": product,
                    "amount": entry["amount"]
                }
                cart_products.append(details)
    else:
        if 'cart' in session:
            for entry in session['cart']:
                products = models.Product.get(id=entry['product_id'])
                product = products[0] if products else None
                if product:
                    details={
                        "product": product,
                        "amount": entry["amount"]
                    }
                    cart_products.append(details)
    return render_template(
        "user/cart.html",
        site = site_config.get_config("site_config"),
        products = cart_products,
    )

@bp.route("/checkout")
@login_required
def checkout():
    return render_template(
        "user/checkout.html",
        site = site_config.get_config("site_config"),
    )

@bp.route('/addcart', methods=['POST'])
def add_to_cart():
    data = request.get_json()  # Or request.form for form data
    product_id = data.get('product_id')
    amount = data.get('amount', 1)
    cart_size = 0
    
    if current_user.is_authenticated:
        current_user.cart.append({
            "product_id": product_id,
            "amount": amount
        })
        cart_size = len(current_user.cart)
        current_user.update()
    else:
        if 'cart' not in session:
            session['cart'] = []
        session['cart'].append({'product_id': product_id, 'amount': amount})
        session.modified = True  # Ensure session saves
        cart_size = len(session['cart'])
    
    return jsonify({'message': 'Added to cart', 'cart_size': cart_size}), 201
