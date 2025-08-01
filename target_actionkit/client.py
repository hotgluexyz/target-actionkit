from target_hotglue.client import HotglueSink
import requests
from singer_sdk.plugin_base import PluginBase
from typing import Dict, List, Optional
import singer
from singer_sdk.exceptions import FatalAPIError, RetriableAPIError
from target_actionkit.auth import ActionKitAuth

LOGGER = singer.get_logger()

class ActionKitSink(HotglueSink):
    """ActionKit target sink class."""
    
    def __init__(
        self,
        target: PluginBase,
        stream_name: str,
        schema: Dict,
        key_properties: Optional[List[str]],
    ) -> None:
        super().__init__(target, stream_name, schema, key_properties)
        self.__auth = ActionKitAuth(dict(self.config))
        self.lists = None
        self.initialize_lists()

    @property
    def base_url(self):
        if self.config.get('full_url'):
            # Strip trailing slashes to prevent double slashes when concatenating
            full_url = self.config.get('full_url').rstrip('/')
            return f"{full_url}/rest/v1/"
            
        return f"https://{self.config.get('hostname')}.actionkit.com/rest/v1/"
    
    @property
    def signup_page_short_name(self):
        return self.config.get('signup_page_short_name')
    
    @property
    def unsubscribe_page_short_name(self):
        return self.config.get('unsubscribe_page_short_name')

    def validate_response(self, response: requests.Response) -> None:
        """Validate HTTP response."""
        msg = self.response_error_message(response)
        if hasattr(response, "text") and response.text:
            msg = f"{msg}. Response: {response.text}"
        if response.status_code in [409]:
            msg = f"{msg}. reason: {response.reason}"
        if response.status_code in [429] or 500 <= response.status_code < 600:
            raise RetriableAPIError(msg, response)
        elif 400 <= response.status_code < 500:
            raise FatalAPIError(msg)


    def prepare_request_headers(self):
        """Prepare request headers."""
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": self.__auth(requests.Request())
        }
    
    def initialize_lists(self):
        if getattr(self, "lists"):
            return
        self.lists = []
        list_url = f"list/"
        params = "?_limit=100"
        next_url = f"{list_url}{params}"
        self.logger.info(f"Fetching lists from {self.base_url}{next_url}")

        while next_url:
            response = self.request_api("GET", endpoint=next_url, headers=self.prepare_request_headers())
            response_data = response.json()
            self.logger.info(f"Response: {response_data}")
            self.lists.extend(response_data.get("objects", []))
            params: str = response_data.get("meta", {}).get("next", "")
            if params:
                params = params.split("/")[-1]
                next_url = f"{list_url}{params}"
            else:
                next_url = None
        
        self.map_list_name_to_id = {l["name"]: l["id"] for l in self.lists}
