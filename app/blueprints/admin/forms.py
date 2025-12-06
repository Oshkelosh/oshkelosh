
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, BooleanField, SubmitField, SelectField, EmailField

from app.models import models

def dynamic_form(configs):
    type_map = {
        "TEXT" : StringField,
        "COLOR" : lambda **kw: StringField(**kw, render_kw={'type': 'color'}),
        "OPTIONS" : SelectField,
        "BOOL" : BooleanField,
        "EMAIL" : EmailField
    }
    attrs = {}
    for key in configs.list_keys():
        if not configs[key].editable:
            continue
        field_cls = type_map[configs[key].type] or StringField
        kwargs = {
            "label" : key.capitalize(),
            "default" : configs[key],
            "description" : configs[key].description
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


