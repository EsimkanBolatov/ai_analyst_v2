import os
from urllib.parse import urlparse

BLACKLIST_DIR = "blacklists"
_blacklists = {}

def load_blacklist(filename: str) -> set:
    if filename not in _blacklists:
        filepath = os.path.join(BLACKLIST_DIR, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                _blacklists[filename] = {line.strip() for line in f if line.strip()}
            print(f"Черный список '{filename}' успешно загружен.")
        except FileNotFoundError:
            print(f"Предупреждение: Файл черного списка '{filename}' не найден.")
            _blacklists[filename] = set()
    return _blacklists[filename]

def check_phone_blacklist(phone: str) -> bool:
    blacklist = load_blacklist("phones.txt")
    return phone in blacklist

def check_email_blacklist(email: str) -> bool:
    blacklist = load_blacklist("emails.txt")
    return email.lower() in blacklist

def check_url_blacklist(url_str: str) -> bool:
    blacklist = load_blacklist("urls.txt")
    try:
        if not url_str.startswith(('http://', 'https://')):
            url_str = 'http://' + url_str
        domain = urlparse(url_str).netloc
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain.lower() in blacklist
    except Exception:
        return False