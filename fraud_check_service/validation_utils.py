import phonenumbers
from pydantic import validate_email
from validators import url as validate_url

def is_valid_phone(value: str) -> bool:
    try:
        phone_number = phonenumbers.parse(value, None)
        return phonenumbers.is_valid_number(phone_number)
    except phonenumbers.NumberParseException:
        return False

def is_valid_email(value: str) -> bool:
    try:
        validate_email(value)
        return True
    except ValueError:
        return False

def is_valid_url(value: str) -> bool:
    if not value.startswith(('http://', 'https://')):
        value = 'http://' + value
    return validate_url(value) is True # validate_url возвращает True или ValidationFailure