import os
from urllib.parse import urlparse

BLACKLIST_DIR = "blacklists"
_blacklists = {} # Кэш для загруженных списков

def load_blacklist(filename: str) -> set:
    """Загружает черный список из файла в кэш."""
    if filename not in _blacklists:
        filepath = os.path.join(BLACKLIST_DIR, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                # Читаем строки, убираем пробелы по краям, игнорируем пустые
                _blacklists[filename] = {line.strip() for line in f if line.strip()}
            print(f"Черный список '{filename}' успешно загружен.")
        except FileNotFoundError:
            print(f"Предупреждение: Файл черного списка '{filename}' не найден.")
            _blacklists[filename] = set()
    return _blacklists[filename]

def check_phone_blacklist(phone: str) -> bool:
    """Проверяет номер телефона по черному списку."""
    blacklist = load_blacklist("phones.txt")
    # Можно добавить нормализацию номера перед проверкой, если нужно
    return phone in blacklist

def check_email_blacklist(email: str) -> bool:
    """Проверяет email по черному списку."""
    blacklist = load_blacklist("emails.txt")
    return email.lower() in blacklist # Сравниваем в нижнем регистре

def check_url_blacklist(url_str: str) -> bool:
    """Проверяет домен из URL по черному списку."""
    blacklist = load_blacklist("urls.txt")
    try:
        # Добавляем http, если нет, чтобы парсер сработал
        if not url_str.startswith(('http://', 'https://')):
            url_str = 'http://' + url_str
        # Извлекаем только домен (например, 'bad-bank-login.com')
        domain = urlparse(url_str).netloc
        # Убираем 'www.', если есть
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain.lower() in blacklist
    except Exception:
        return False # Ошибка при парсинге URL