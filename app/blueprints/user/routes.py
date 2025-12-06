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

from flask_wtf import FlaskForm
from wtforms import EmailField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, Length

from . import bp
from app.models import models
from app.utils import helpers
import json, os, random


class loginForm(FlaskForm):
    email = EmailField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('Log In')

@bp.route("/login", methods=["GET","POST"])
def login():
    form = loginForm()
    if form.validate_on_submit():
        users = models.User.get(email=form.email.data)
        user = users[0] if users else None
        if user and user.check_password(form.password.data):
            if 'cart' in session:
                user.cart.extend(session['cart'])
                user.update()
                session.pop('cart', None)
            login_user(user)
            return redirect(url_for('main.index'))
        flash('Invalid login attempt')
    return render_template(
        helpers.template_route("user/login.html"),
        site=helpers.site_data(),
        login_form = form
    )


@bp.route("/logout")
def logout():
    logout_user()
    return render_template(
        helpers.template_route("user/logout.html"),
        site=helpers.site_data()
    )


@bp.route("/profile")
@login_required
def profile():
    return render_template(
        helpers.template_route("user/profile.html"),
        site=helpers.site_data(),
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
        helpers.template_route("user/cart.html"),
        site=helpers.site_data(),
        products = cart_products,
    )

@bp.route("/checkout")
@login_required
def checkout():
    return render_template(
        helpers.template_route("user/checkout.html"),
        site=helpers.site_data(),
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
