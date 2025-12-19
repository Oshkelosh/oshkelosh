
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, BooleanField, SubmitField, SelectField, EmailField, FloatField
from wtforms.validators import DataRequired

from app.models import models

import datetime

def dynamic_form(configs):
    type_map = {
        "TEXT" : StringField,
        "COLOR" : lambda **kw: StringField(**kw, render_kw={'type': 'color'}),
        "OPTIONS" : SelectField,
        "BOOL" : BooleanField,
        "EMAIL" : EmailField
    }
    attrs = {}
    for key in configs.keys():
        if not configs[key].editable:
            continue
        field_cls = type_map[configs[key].type] or StringField
        kwargs = {
            "label" : key.capitalize(),
            "default" : configs[key],
            "description" : configs[key].description,
        }
        if configs[key].type == "OPTIONS":
            choices = None
            if key == "style":
                choices = [('','')] + [(opt, opt) for opt in get_styles()]
                kwargs["choices"] = choices
        attrs[key] = field_cls(**kwargs)
    attrs["submit"] = SubmitField('Submit')
    return type('DynamicForm', (FlaskForm,), attrs)

def get_styles():
    style = []
    addons = models.Addon.get()
    for addon in addons:
        if addon.type == "STYLE":
            style.append(addon.name)
    return style


def create_product_form(product):
    class ProductForm(FlaskForm):
        name = StringField(
            'Name',
            validators=[DataRequired()],
            description="Product name",
            default=product.name
        )

        description = StringField(
            'Description',
            validators=[DataRequired()],
            description="Product description",
            default=product.description
        )

        price = FloatField(
            'Price',
            validators=[DataRequired()],
            description="Product price",
            default=product.price
        )
        
        supplier = models.get_config(addon_id=product.supplier_id)
        if getattr(supplier, 'manual', False):
            stock = StringField(
                'Stock',
                validators=[DataRequired()],
                description="Available stock",
                default=product.stock,
            )

        active = BooleanField(
            'Active',
            description="Is product active",
            default=product.active
        )

        submit = SubmitField('Submit')
    return ProductForm()

def create_image_form(image):
    class ImageForm(FlaskForm):
        title = StringField(
            'Title',
            validators=[DataRequired()],
            description="Image title",
            default=image.title
        )

        alt_taxt = StringField(
            'Alt Text',
            validators=[DataRequired()],
            description="Alternative text",
            default=image.alt_text
        )

        position = FloatField(
            'Position',
            validators=[DataRequired()],
            description="Order position. Adjust in Product page",
            default=image.position,
            render_kw={"readonly":True}
        )
        
        submit = SubmitField('Submit')
    return ImageForm()
