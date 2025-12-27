from flask import current_app

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed

from wtforms import StringField, BooleanField, SubmitField, SelectField, EmailField, FloatField
from wtforms.validators import DataRequired, Length, Optional
from typing import Type, Any, List, Tuple

from app.models import models

def dynamic_form(configs: models.Config) -> Type[FlaskForm]:
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

def get_styles() -> List[str]:
    style: List[str] = []
    addons = models.Addon.query.all()
    for addon in addons:
        if addon.type == "STYLE":
            style.append(addon.name)
    return style


def create_product_form(product: models.Product) -> FlaskForm:
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

def create_image_form(image: models.Image) -> FlaskForm:
    class ImageForm(FlaskForm):
        title = StringField(
            'Title',
            validators=[DataRequired()],
            description="Image title",
            default=image.title
        )

        alt_text = StringField(
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

class AddImageForm(FlaskForm):
    image = FileField(
        'Image',
            validators=[
                FileRequired(),
                FileAllowed(current_app.config.get("IMAGE_EXTENSIONS"), f'Images only ({', '.join(current_app.config.get("IMAGE_EXTENSIONS"))})!')
            ]
    )
    title = StringField(
        'Title',
        validators=[DataRequired(), Length(max=100)]
    )
    alt_text = StringField(
        'Alt Text',
        validators=[Optional(), Length(max=450)]
    )
    submit = SubmitField('Upload Image')
