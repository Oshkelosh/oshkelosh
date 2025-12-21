import requests
import time



class PaypalClient():
    SANDBOX_BASE = "https://api-m.sandbox.paypal.com"
    LIVE_BASE = "https://api-m.paypal.com"
    def __init__(self):
        self._ts = 0
        self._token = ""
        self.sandbox = True
        
    def _get_auth_header(client_id, client_secret) -> str:
        """Base64-encoded Basic auth header for client credentials."""
        credentials = f"{self.client_id}:{self.client_secret}".encode("utf-8")
        encoded = base64.b64encode(credentials).decode("utf-8")
        return f"Basic {encoded}"

    def get_access_token(self, client_id, client_secret):
        ts = time.time()
        if 
