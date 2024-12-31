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

    def upsert_record(self, record: dict, context: dict):
        state_dict = dict()

        if record.get("email"):
            search_response = self.request_api(
                "GET",
                endpoint=f"user/?email={record['email']}",
                headers=self.prepare_request_headers()
            )
            
            existing_users = search_response.json().get("objects", [])
            
            if existing_users:
                user_id = existing_users[0].get("id")
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
            id = response.headers['Location'].replace(f"https://{self.config.get('hostname')}.actionkit.com/rest/v1/user/", "")[:-1]
            self.logger.info(id)
            self.add_phone_numbers(id, record)
            return id, response.ok, state_dict
        
        return None, False, state_dict

    def preprocess_record(self, record: dict, context: dict) -> dict:
        payload = {
            "first_name": record.get("first_name"),
            "last_name": record.get("last_name"),
            "email": record.get("email")
        }

        if "addresses" in record and isinstance(record["addresses"], list):
            for address in record["addresses"]:
                payload.update({
                    "address1": address.get("line1"),
                    "city": address.get("city"),
                    "state": address.get("state"),
                    "region": address.get("state"),
                    "postal": address.get("postal_code"),
                    "zip": address.get("postal_code"),
                    "country": address.get("country")
                })
                break

        return payload

    def postprocess_record(self, record: dict, context: dict) -> dict:
        if not self.config.get("page_name"):
            return record
        email = record.get("email")
        if not email:
            return record
        response = self.request_api(
            "POST",
            endpoint="rest/v1/action",
            request_data={
                "page": self.config.get("page_name"),
                "email": email
            },
            headers=self.prepare_request_headers()
        )
        if response.ok:
            self.logger.info(f"Action created for {email} on {self.config.get('page_name')}")
            return record
        raise Exception(f"Failed to create action for {email} on {self.config.get('page_name')}: {response.text}")