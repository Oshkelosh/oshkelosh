from flask import (
    render_template,
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
from app.database import db
from app.utils import site_config 

import bcrypt
from sqlalchemy.exc import IntegrityError
from typing import Any, Dict, List




@bp.route("/login", methods=["GET","POST"])
def login() -> str | Response:
    form = forms.loginForm()
    if form.validate_on_submit():
        user = models.User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            if 'cart' in session:
                # Convert session cart items to Cart objects
                for item in session['cart']:
                    cart_item = models.Cart.query.filter_by(
                        user_id=user.id,
                        product_id=item['product_id']
                    ).first()
                    if cart_item:
                        cart_item.quantity += item.get('amount', 1)
                    else:
                        cart_item = models.Cart(
                            user_id=user.id,
                            product_id=item['product_id'],
                            quantity=item.get('amount', 1)
                        )
                        db.session.add(cart_item)
                db.session.commit()
                session.pop('cart', None)
            return redirect(url_for('main.index'))
        flash('Invalid login attempt')
    return render_template(
        "user/login.html",
        site = site_config.get_config("site_config"),
        login_form = form
    )


@bp.route("/logout")
def logout() -> str:
    logout_user()
    return render_template(
        "user/logout.html",
        site = site_config.get_config("site_config"),
    )

@bp.route("/signup", methods=["GET", "POST"])
def signup() -> str | Response:
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
        try:
            user = models.User(**user_data)
            db.session.add(user)
            db.session.flush()  # Get the user ID
            
            user.add_address(**billing_address)
            user.add_address(**shipping_address)
            
            login_user(user)
            flash("Successfully registered!")
            return redirect(url_for("main.index"))

        except IntegrityError as e:
            db.session.rollback()
            error_msg = str(e.orig).lower()
            if 'unique' in error_msg or 'duplicate' in error_msg or 'email' in error_msg:
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
def profile() -> str:
    addresses = models.Address.query.filter_by(user_id=current_user.id).all()
    orders = models.Order.query.filter_by(user_id=current_user.id).all()
    return render_template(
        "user/profile.html",
        site = site_config.get_config("site_config"),
        addresses = addresses,
        orders = orders
    )

@bp.route("/cart")
def cart() -> str:
    cart_products = []
    subtotal = 0.0
    
    if current_user.is_authenticated:
        for cart_item in current_user.cart_items:
            product = cart_item.product
            if product:
                details = {
                    "product": product,
                    "amount": cart_item.quantity,
                    "cart_item_id": cart_item.id
                }
                cart_products.append(details)
                subtotal += product.price * cart_item.quantity
    else:
        if 'cart' in session:
            for entry in session['cart']:
                product = models.Product.query.get(entry['product_id'])
                if product:
                    amount = entry.get("amount", 1)
                    details={
                        "product": product,
                        "amount": amount,
                        "product_id": product.id
                    }
                    cart_products.append(details)
                    subtotal += product.price * amount
    return render_template(
        "user/cart.html",
        site = site_config.get_config("site_config"),
        products = cart_products,
        subtotal = subtotal,
    )

@bp.route("/checkout")
@login_required
def checkout() -> str:
    return render_template(
        "user/checkout.html",
        site = site_config.get_config("site_config"),
    )

@bp.route('/addcart', methods=['POST'])
def add_to_cart() -> tuple[Response, int]:
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid request'}), 400
    product_id = data.get('product_id')
    amount = data.get('amount', 1)
    cart_size = 0
    
    if current_user.is_authenticated:
        cart_item = models.Cart.query.filter_by(
            user_id=current_user.id,
            product_id=product_id
        ).first()
        
        if cart_item:
            cart_item.quantity += amount
        else:
            cart_item = models.Cart(
                user_id=current_user.id,
                product_id=product_id,
                quantity=amount
            )
            db.session.add(cart_item)
        db.session.commit()
        cart_size = current_user.cart_items.count()
    else:
        if 'cart' not in session:
            session['cart'] = []
        session['cart'].append({'product_id': product_id, 'amount': amount})
        session.modified = True  # Ensure session saves
        cart_size = len(session['cart'])
    
    return jsonify({'message': 'Added to cart', 'cart_size': cart_size}), 201

@bp.route('/updatecart', methods=['POST'])
def update_cart_item() -> tuple[Response, int]:
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid request'}), 400
    
    product_id = data.get('product_id')
    quantity = data.get('quantity', 1)
    
    if quantity < 1:
        return jsonify({'error': 'Quantity must be at least 1'}), 400
    
    if current_user.is_authenticated:
        cart_item = models.Cart.query.filter_by(
            user_id=current_user.id,
            product_id=product_id
        ).first()
        
        if not cart_item:
            return jsonify({'error': 'Item not found in cart'}), 404
        
        cart_item.quantity = quantity
        db.session.commit()
        
        # Calculate updated subtotal
        subtotal = sum(item.product.price * item.quantity for item in current_user.cart_items if item.product)
        
        return jsonify({
            'message': 'Cart updated',
            'quantity': quantity,
            'subtotal': subtotal
        }), 200
    else:
        if 'cart' not in session:
            return jsonify({'error': 'Cart not found'}), 404
        
        # Find and update item in session cart
        found = False
        for item in session['cart']:
            if item.get('product_id') == product_id:
                item['amount'] = quantity
                found = True
                break
        
        if not found:
            return jsonify({'error': 'Item not found in cart'}), 404
        
        session.modified = True
        
        # Calculate updated subtotal
        subtotal = 0.0
        for entry in session['cart']:
            product = models.Product.query.get(entry['product_id'])
            if product:
                subtotal += product.price * entry.get('amount', 1)
        
        return jsonify({
            'message': 'Cart updated',
            'quantity': quantity,
            'subtotal': subtotal
        }), 200

@bp.route('/removecart', methods=['POST'])
def remove_cart_item() -> tuple[Response, int]:
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid request'}), 400
    
    product_id = data.get('product_id')
    
    if current_user.is_authenticated:
        cart_item = models.Cart.query.filter_by(
            user_id=current_user.id,
            product_id=product_id
        ).first()
        
        if not cart_item:
            return jsonify({'error': 'Item not found in cart'}), 404
        
        db.session.delete(cart_item)
        db.session.commit()
        
        # Calculate updated subtotal
        subtotal = sum(item.product.price * item.quantity for item in current_user.cart_items if item.product)
        
        return jsonify({
            'message': 'Item removed from cart',
            'subtotal': subtotal
        }), 200
    else:
        if 'cart' not in session:
            return jsonify({'error': 'Cart not found'}), 404
        
        # Remove item from session cart
        session['cart'] = [item for item in session['cart'] if item.get('product_id') != product_id]
        session.modified = True
        
        # Calculate updated subtotal
        subtotal = 0.0
        for entry in session['cart']:
            product = models.Product.query.get(entry['product_id'])
            if product:
                subtotal += product.price * entry.get('amount', 1)
        
        return jsonify({
            'message': 'Item removed from cart',
            'subtotal': subtotal
        }), 200
