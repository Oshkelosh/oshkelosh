import requests
import time
import base64
from typing import Optional

class PaypalClient:
    SANDBOX_BASE: str = "https://api-m.sandbox.paypal.com"
    LIVE_BASE: str = "https://api-m.paypal.com"
    
    def __init__(self) -> None:
        self._ts: float = 0.0
        self._token: str = ""
        self.sandbox: bool = True
        
    @staticmethod
    def _get_auth_header(client_id: str, client_secret: str) -> str:
        """Base64-encoded Basic auth header for client credentials."""
        credentials = f"{client_id}:{client_secret}".encode("utf-8")
        encoded = base64.b64encode(credentials).decode("utf-8")
        return f"Basic {encoded}"

    def get_access_token(self, client_id: str, client_secret: str) -> Optional[str]:
        ts = time.time()
        if ts - self._ts < 3600 and self._token:
            return self._token
        # TODO: Implement token retrieval logic
        return None 
