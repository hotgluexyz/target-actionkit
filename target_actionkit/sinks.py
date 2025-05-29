"""ActionKit target sink class, which handles writing streams."""


import os
import json

from target_actionkit.client import ActionKitSink

__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))

class ContactsSink(ActionKitSink):
    """ActionKit target sink class."""

    name = "Contacts"
    endpoint = "user"
    entity = "user"
    NON_UNIFIED_FIELDS = ["source"]
    

    def add_phone_numbers(self, user_id: str, record: dict):
        if "phone_numbers" in record and isinstance(record["phone_numbers"], list):
            response = self.request_api(
                "GET",
                endpoint=f"user/{user_id}",
                headers=self.prepare_request_headers()
            )
            existing_phones = response.json().get('phones', [])

            for phone in record["phone_numbers"]:
                existing_phones.append({
                    "type": phone.get("type", "mobile"),
                    "phone": phone.get("number"),
                    "user": f"/rest/v1/user/{user_id}/",
                    "source": "singer_target"
                })

            self.logger.info(f"user/{user_id}")
            self.request_api(
                "PATCH",
                endpoint=f"user/{user_id}",
                request_data={"phones": existing_phones},
                headers=self.prepare_request_headers()
            )
    
    def get_subscribed_lists(self, user_id):
        subscribed_list_ids = []
        if user_id:
            subscribed_lists = []
            subscriptions_url = f"subscription/"
            params = f"?user={user_id}&_limit=100"
            next_url = f"{subscriptions_url}{params}"

            while next_url:
                response = self.request_api("GET", endpoint=next_url, headers=self.prepare_request_headers())
                response_data = response.json()
                subscribed_lists.extend(response_data.get("objects", []))
                params: str = response_data.get("meta", {}).get("next", "")
                if params:
                    params = params.split("/")[-1]
                    next_url = f"{subscriptions_url}{params}"
                else:
                    next_url = None

            for subscribed_obj in subscribed_lists:
                list_id = subscribed_obj["list"].split("/")[-2]
                response = self.request_api("GET", endpoint=f"list/{list_id}/", headers=self.prepare_request_headers())
                subscribed_list_ids.append(response.json()["id"])

        return subscribed_list_ids

    def post_signup_action(self, user_email: str, lists: list = None):
        
        self.logger.info(f"Signup user: {user_email}. lists: {lists}")
        resp =  self.request_api(
            "POST",
            request_data={
                "email": user_email,
                "page": self.signup_page_short_name,
                "lists": lists,
            },
            endpoint="action",
            headers=self.prepare_request_headers()
        )
        self.logger.info(f"Signup result: {resp.status_code}")
        return resp
    
    def remove_lists(self, user_email: str):
        
        self.logger.info(f"Unsubscribe: {user_email} all lists.")
        return self.request_api(
            "POST",
            request_data={
                "email": user_email,
                "page": self.unsubscribe_page_short_name,
            },
            endpoint="action",
            headers=self.prepare_request_headers()
        )
    
    def create_list(self, list_name: str):
        if list_name and isinstance(list_name, str):
            self.logger.info(f"creating list: {list_name}")
            response = self.request_api(
                "POST",
                request_data={
                    "name": list_name
                },
                endpoint="list",
                headers=self.prepare_request_headers()
            )
            if response.ok:
                response = self.request_api("GET", endpoint="list", params={"name": list_name}, headers=self.prepare_request_headers())
                res_json = response.json()
                list_id = res_json.get("objects")[0].get("id")
                self.map_list_name_to_id[list_name] = list_id

    def upsert_record(self, record: dict, context: dict):
        state_dict = dict()
        # Email is a required field for ActionKit
        if not record.get("email"):
            raise Exception("Email is a required field for ActionKit")

        if record.get("error"):
            raise Exception(record.get("error"))
        
        self.logger.info(f"Upserting user: {record.get('email')}")

        subscribe_status = record.pop("subscribe_status") if "subscribe_status" in record else None
        intended_unsubscribe = subscribe_status == "unsubscribed"
        intended_subscribe = subscribe_status == "subscribed"
        
        lists = record.get("lists")


        # Unsubscribe user from all lists because API does not support unsubscribing from single lists
        if intended_unsubscribe:
            search_response = self.request_api(
                "GET",
                endpoint="user",
                params = {"email": record['email']},
                headers=self.prepare_request_headers()
            )
            
            existing_users = search_response.json().get("objects", [])
            if existing_users:
                currently_subscribed_lists = self.get_subscribed_lists(existing_users[0].get("id"))
                self.remove_lists(record["email"])
                lists_to_subscribe = [l for l in currently_subscribed_lists if l not in lists]
                list_response = self.post_signup_action(record["email"], lists_to_subscribe)
            else:
                # Create user from scratch
                list_response = self.post_signup_action(record["email"], [])
        elif intended_subscribe:
            list_response = self.post_signup_action(record["email"], lists)
        else:
            # Create if not exists without lists
            list_response = self.post_signup_action(record["email"])

        is_created = list_response.json().get("created_user")
        user_id = list_response.json().get("user").split("/")[-2]

        # Update non-email fields
        response = self.request_api(
            "PATCH",
            request_data=record,
            endpoint=f"user/{user_id}",
            headers=self.prepare_request_headers()
        )
        if response.ok:
            self.add_phone_numbers(user_id, record)
            state_dict["success"] = True
            state_dict["is_updated"] = not is_created
            return user_id, response.ok, state_dict
                
        return None, False, state_dict

    def load_json_data(self, filename):
        file_path = os.path.join(__location__, filename)
        with open(file_path, "r") as file_to_read:
            return json.load(file_to_read)

    def transform_country_code(self, country_code):
        if not country_code:
            return None

        countries = self.load_json_data("countries.json")
        
        return countries.get(country_code, country_code)

    def preprocess_record(self, record: dict, context: dict) -> dict:
        payload = {
            "first_name": record.get("first_name"),
            "last_name": record.get("last_name"),
            "email": record.get("email"),
            "subscribe_status": record.get("subscribe_status"),
        }
        if "addresses" in record and isinstance(record["addresses"], list):
            for address in record["addresses"]:
                zip_code = postal_code = address.get("postal_code")
                if isinstance(postal_code, str) and len(postal_code) > 5:
                    zip_code = postal_code[:5]

                payload.update({
                    "address1": address.get("line1"),
                    "city": address.get("city"),
                    "state": address.get("state"),
                    "region": address.get("state"),
                    "postal": postal_code,
                    "zip": zip_code,
                    "country": self.transform_country_code(address.get("country"))
                })
                break

        if "lists" in record and isinstance(record["lists"], list):
            
            # Leading and Trailing whitespace creates validation issues for ActionKit Lists
            trimmed_lists = [list_name.strip() for list_name in record["lists"]]
            
            for list_name in trimmed_lists:
                if list_name in self.map_list_name_to_id:
                    continue
                self.create_list(list_name)
                
            payload["lists"] = [
                self.map_list_name_to_id[l]
                for l in trimmed_lists
            ]
        if "custom_fields" in record and isinstance(record["custom_fields"], list):
            payload["fields"] = {}
            for field in record["custom_fields"]:
                field_name = field["name"].lower()
                if field_name in self.NON_UNIFIED_FIELDS:
                    payload[field_name] = field["value"]
                else:
                    payload["fields"][field["name"]] = field["value"]

        return payload
