"""ActionKit target sink class, which handles writing streams."""

from target_actionkit.client import ActionKitSink


class ContactsSink(ActionKitSink):
    """ActionKit target sink class."""

    name = "Contacts"
    endpoint = "user"
    entity = "user"

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
    
    def add_lists(self, user_email: str, lists: list = None):
        if lists and isinstance(lists, list):
            self.logger.info(f"add lists to user: {user_email}. lists: {lists}")
            return self.request_api(
                "POST",
                request_data={
                    "email": user_email,
                    "page": "signup",
                    "lists": lists
                },
                endpoint="action",
                headers=self.prepare_request_headers()
            )
    
    def remove_lists(self, user_email: str, lists: list = None):
        if lists and isinstance(lists, list):
            self.logger.info(f"add lists to user: {user_email}. lists: {lists}")
            return self.request_api(
                "POST",
                request_data={
                    "email": user_email,
                    "page": "unsubscribe",
                    "lists": lists
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

        if record.get("email"):
            if record.get("error"):
                raise Exception(record.get("error"))
            search_response = self.request_api(
                "GET",
                endpoint="user",
                params = {"email": record['email']},
                headers=self.prepare_request_headers()
            )
            
            existing_users = search_response.json().get("objects", [])
            subscription_status = record.pop("subscription_status")
            
            if existing_users:
                user_id = existing_users[0].get("id")
                subscribed_lists = self.get_subscribed_lists(user_id)
                lists = record.get("lists", [])
                to_subscribe = list(set(lists) - set(subscribed_lists))
                self.add_lists(record["email"], to_subscribe)
                if subscription_status == "unsubscribed":
                    to_unsubscribe = list(set(subscribed_lists) - set(lists))
                    self.remove_lists(record["email"], to_unsubscribe)
                response = self.request_api(
                    "PATCH",
                    request_data=record,
                    endpoint=f"user/{user_id}",
                    headers=self.prepare_request_headers()
                )
                
                if response.ok:
                    self.add_phone_numbers(user_id, record)
                    state_dict["success"] = True
                    state_dict["is_updated"] = True
                    return user_id, response.ok, state_dict
        
        response = self.request_api(
            "POST",
            request_data=record,
            endpoint="user",
            headers=self.prepare_request_headers()
        )
        
        if response.ok:
            state_dict["success"] = True
            id = response.headers['Location'].replace(f"{self.base_url}user/", "")[:-1]
            self.logger.info(id)
            self.add_lists(record["email"], record.get("lists"))
            self.add_phone_numbers(id, record)
            return id, response.ok, state_dict
        
        return None, False, state_dict

    def preprocess_record(self, record: dict, context: dict) -> dict:
        payload = {
            "first_name": record.get("first_name"),
            "last_name": record.get("last_name"),
            "email": record.get("email"),
            "subscription_status": record.get("subscription_status"),
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
                    "country": address.get("country")
                })
                break

        if "lists" in record and isinstance(record["lists"], list):
            # list of ids
            for list_name in record["lists"]:
                if list_name in self.map_list_name_to_id:
                    continue
                self.create_list(list_name)
                
            payload["lists"] = [
                self.map_list_name_to_id[l]
                for l in record["lists"]
            ]
        if "custom_fields" in record and isinstance(record["custom_fields"], list):
            payload["fields"] = {
                custom_field["name"]: custom_field["value"]
                for custom_field in record["custom_fields"]
            }

        return payload
