from hotglue_singer_sdk.target_sdk.client import HotglueSink
import requests
from hotglue_singer_sdk.plugin_base import PluginBase
from typing import Dict, List, Optional
import singer
from hotglue_singer_sdk.exceptions import FatalAPIError, RetriableAPIError
from hotglue_etl_exceptions import InvalidPayloadError, InvalidCredentialsError
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
        self.__map_list_name_to_id = None

    @property
    def map_list_name_to_id(self):
        if self.__map_list_name_to_id is None:
            self.initialize_lists()
        return self.__map_list_name_to_id

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
        if response.status_code == 400:
            try:
                error_msg = response.json()
                # the response can have different structures, so we need to handle them all
                if isinstance(error_msg, dict) and "errors" in error_msg:
                    error_msg = error_msg["errors"]
                if isinstance(error_msg, dict):
                    error_msg = next(iter(error_msg.values()))
                if isinstance(error_msg, list):
                    error_msg = error_msg[0]
            except:
                error_msg = response.text
            raise InvalidPayloadError(error_msg)
        msg = self.response_error_message(response)
        if response.status_code in [401, 403]:
            if hasattr(response, "text") and response.text:
                error_msg = response.text
            else:
                error_msg = msg
            self.__auth.set_auth_error(response.request.method, response.request.url, error_msg)
            raise InvalidCredentialsError(error_msg)
        if hasattr(response, "text") and response.text:
            msg = f"{msg}. Response: {response.text}"
        if response.status_code in [429] or 500 <= response.status_code < 600:
            raise RetriableAPIError(msg, response)
        elif 400 <= response.status_code < 500:
            raise FatalAPIError(msg)


    def request_api(self, http_method, endpoint=None, params={}, request_data=None, headers={}, verify=True):
        """
        Request records from REST endpoint(s), returning response records.
        Logs the request and response information to help debugging.
        """
        # Avoid retrying requests if we've already encountered an authentication error
        auth_error = self.__auth.get_auth_error(http_method, self.url(endpoint))
        if auth_error:
            raise InvalidCredentialsError(auth_error)
        req_info = f"{http_method} {endpoint or ''}"
        if params:
            req_info += f" params={list(params.keys())}"
        if request_data and isinstance(request_data, dict):
            req_info += f" body_keys={list(request_data.keys())}"
        self.logger.info(f"API request: {req_info}")
        response = super().request_api(http_method, endpoint, params, request_data, headers, verify)
        try:
            body = response.json() if response.text else None
        except Exception:
            body = None
        resp_info = f"status={response.status_code}"
        if not body:
            resp_info += f" body={response.text if response.text else 'empty response'}"
        else:
            resp_info += f" keys={list(body.keys()) if isinstance(body, dict) else type(body).__name__}"
            # log the entire body if the request was not a GET
            if http_method != "GET":
                resp_info += f" body={body}"
        self.logger.info(f"API response: {resp_info}")
        return response
    
    def prepare_request_headers(self):
        """Prepare request headers."""
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": self.__auth(requests.Request())
        }
    
    def initialize_lists(self):
        lists = []
        list_url = f"list/"
        params = "?_limit=100"
        next_url = f"{list_url}{params}"

        while next_url:
            response = self.request_api("GET", endpoint=next_url, headers=self.prepare_request_headers())
            response_data = response.json()
            lists.extend(response_data.get("objects", []))
            params: str = response_data.get("meta", {}).get("next", "")
            if params:
                params = params.split("/")[-1]
                next_url = f"{list_url}{params}"
            else:
                next_url = None
        
        self.__map_list_name_to_id = {l["name"]: l["id"] for l in lists}
