import requests
import base64


class ActionKitAuth(requests.auth.AuthBase):
    def __init__(self, config):
        self.__config = config
        self.__username = config["username"]
        self.__password = config["password"]
        self.__session = requests.Session()

    def __call__(self, r):
        auth_string = f"{self.__username}:{self.__password}"
        encoded_auth = base64.b64encode(auth_string.encode()).decode()
        return f"Basic {encoded_auth}"
