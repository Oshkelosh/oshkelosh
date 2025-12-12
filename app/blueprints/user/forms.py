from flask_wtf import FlaskForm
from wtforms import EmailField, PasswordField, SubmitField, StringField
from wtforms.validators import DataRequired, Email, Length, EqualTo



class loginForm(FlaskForm):
    email = EmailField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('Log In')

class signupForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    surname = StringField('Surname', validators=[DataRequired()])
    email = EmailField('Email', validators=[DataRequired(), Email()]) 
    phone = StringField('Phone number')

    billing_street = StringField('Street', validators=[DataRequired()])
    billing_city = StringField('City', validators=[DataRequired()])
    billing_state = StringField('State', validators=[DataRequired()])
    billing_postal_code = StringField('Postal_code', validators=[DataRequired()])
    billing_country = StringField('Country', validators=[DataRequired()])

    shipping_street = StringField('Street', validators=[DataRequired()])
    shipping_city = StringField('City', validators=[DataRequired()])
    shipping_state = StringField('State', validators=[DataRequired()])
    shipping_postal_code = StringField('Postal_code', validators=[DataRequired()])
    shipping_country = StringField('Country', validators=[DataRequired()])

    password = PasswordField('Password', validators=[DataRequired(), Length(min=6, message="Password must be at least 6 characters")])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password', message="Passwords must match")])
    submit = SubmitField('Sign Up')

