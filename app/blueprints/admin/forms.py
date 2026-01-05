from flask import current_app

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed

from wtforms import StringField, BooleanField, SubmitField, SelectField, EmailField, FloatField, HiddenField
from wtforms.validators import DataRequired, Length, Optional, URL
from typing import Type, Any, List, Tuple

from app.models import models
import json

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
        
        supplier_config = models.get_config(addon_id=product.supplier_id)
        if getattr(supplier_config, 'manual', False):
            stock = StringField(
                'Stock',
                validators=[DataRequired()],
                description="Available stock",
                default=product.stock,
            )
        
        supplier_data = models.Addon.query.filter_by(id=product.supplier_id).first()
        supplier = StringField(
            'Supplier',
            validators=[DataRequired()],
            description="Supplier",
            default=supplier_data.name,
            render_kw={"readonly":True}
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

class AddonUploadForm(FlaskForm):
    url = StringField(
        'Addon URL',
        validators=[Optional(), URL(message='Please enter a valid URL')],
        description="URL to download addon ZIP file from"
    )
    zip_file = FileField(
        'Addon ZIP File',
        validators=[
            Optional(),
            FileAllowed(['zip'], 'Only ZIP files are allowed!')
        ],
        description="Upload addon as ZIP file"
    )
    submit = SubmitField('Install Addon')
    
    def validate(self, extra_validators=None):
        """Ensure at least one field is provided."""
        if not super().validate(extra_validators):
            return False
        
        if not self.url.data and not self.zip_file.data:
            self.url.errors.append('Please provide either a URL or upload a ZIP file')
            return False
        
        if self.url.data and self.zip_file.data:
            self.url.errors.append('Please provide either a URL or a file, not both')
            return False
        
        return True

class AddonConfirmForm(FlaskForm):
    addon_data = HiddenField('Addon Data', validators=[DataRequired()])
    confirm = SubmitField('Confirm Replacement')

class AddSupplierForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    contact_name = StringField('Contact Name', validators=[DataRequired()])
    email = EmailField('Email', validators=[DataRequired()])
    phone = StringField('Phone', validators=[DataRequired()])
    submit = SubmitField('Add Supplier')

def create_manual_product_form() -> FlaskForm:
    class ManualProductForm(FlaskForm):
        name = StringField('Name', validators=[DataRequired()])
        description = StringField('Description', validators=[DataRequired()])
        price = FloatField('Price', validators=[DataRequired()])
        stock = StringField('Stock', validators=[DataRequired()])
        supplier_id = SelectField('Supplier', validators=[DataRequired()], choices=get_suppliers())
        active = BooleanField('Active', validators=[DataRequired()])
        submit = SubmitField('Add Product')
    return ManualProductForm()

def get_suppliers() -> List[Tuple[int, str]]:
    suppliers = models.Addon.query.filter_by(type="SUPPLIER").all()
    supplier_data = [models.Config(addon_id=supplier.id) for supplier in suppliers] if suppliers else []
    for supplier in supplier_data:
        print(json.dumps(supplier.data(), indent=4))
    return [(supplier.id, supplier.name) for supplier in supplier_data if "manual" in supplier.keys()] if supplier_data else []
