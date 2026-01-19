import requests
import base64
from urllib.parse import urlparse

from typing import Dict, Tuple, Optional


class ActionKitAuth(requests.auth.AuthBase):
    def __init__(self, config):
        self.__config = config
        self.__username = config["username"]
        self.__password = config["password"]
        self.__session = requests.Session()
        # Store authentication errors by (method, url) tuple
        self.__auth_errors: Dict[Tuple[str, str], str] = {}

    def __call__(self, r):
        auth_string = f"{self.__username}:{self.__password}"
        encoded_auth = base64.b64encode(auth_string.encode()).decode()
        return f"Basic {encoded_auth}"

    def normalize_url(self, url: str) -> str:
        """Returns the base path of a URL."""
        return urlparse(url).path.rstrip("/")

    def get_auth_error(self, method: str, url: str) -> Optional[str]:
        """Returns the authentication error if any for a given method and URL."""
        return self.__auth_errors.get((method, self.normalize_url(url)))

    def set_auth_error(self, method: str, url: str, error: str):
        """Sets the authentication error for a given method and URL."""
        self.__auth_errors[(method, self.normalize_url(url))] = error
