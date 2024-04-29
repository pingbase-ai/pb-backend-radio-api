from typing import Dict
from datetime import datetime
from uuid import UUID

import re
import uuid
import base64
import random
import string
import json


class UUIDEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, UUID):
            # if the obj is uuid, we simply return the value of uuid
            return obj.hex
        return json.JSONEncoder.default(self, obj)


def generate_random_string() -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=12))


def return_str_version(data: Dict[str, str], key: str) -> str:
    return str(data[key])


def password_rule_check(password: str) -> bool:
    has_upper_case = bool(re.search(r"[A-Z]", password))
    has_special_character = bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', password))
    has_min_length = len(password) >= 8
    return has_upper_case and has_special_character and has_min_length


def generate_strong_password() -> str:
    return "".join(
        random.choices(string.ascii_letters + string.digits + string.punctuation, k=12)
    )


def decode_base64(encoded_string: str) -> str:
    decoded_bytes = base64.b64decode(encoded_string)
    decoded_string = decoded_bytes.decode("utf-8")
    return decoded_string


def encode_base64(string: str) -> str:
    encoded_bytes = base64.b64encode(string.encode("utf-8"))
    encoded_string = encoded_bytes.decode("utf-8")
    return encoded_string


def get_time_difference(A: str, B: str) -> float:
    # Convert the ISO 8601 formatted strings to datetime objects
    A_dt = datetime.fromisoformat(A.replace("Z", "+00:00"))
    B_dt = datetime.fromisoformat(B.replace("Z", "+00:00"))

    # Calculate the difference in time between B and A
    time_difference = abs((B_dt - A_dt).total_seconds())
    return time_difference
