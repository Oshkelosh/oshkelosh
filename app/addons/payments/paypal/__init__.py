from . import functions
import json
import logging

log = logging.getLogger(__name__)


default_list = [
    {
        "object_name": "SETUP",
        "type": "NOT_NULL",
        "key": "key",
        "value": "client_id",
        "data": {
            "value": "your_paypal_app_client_id",
            "description": "Paypal Client ID for your Oshkelosh App",
            "secure":True,
        },
    },
    {
        "object_name": "SETUP",
        "type": "NOT_NULL",
        "key": "key",
        "value": "client_secret",
        "data": {
            "value": "your_paypal_app_client_secret",
            "description": "Paypal Client Secret for your Oshkelosh App",
            "secure":True,
        },
    },
]
