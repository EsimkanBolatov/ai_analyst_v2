# AI-Analyst Guard Extension

## Что умеет

- Popup для ручной проверки ссылки, номера, email или текста
- Тумблер `Continuous Protection`
- Context Menu: `Проверить в AI-Analyst` для выделенного текста
- Непрерывное сканирование DOM страницы на ссылки и телефоны
- Подсветка совпадений из blacklist красным

## Как запустить

1. Поднимите backend API на `http://localhost:8010/api/v1`
2. Откройте Chrome или Edge
3. Перейдите на `chrome://extensions` или `edge://extensions`
4. Включите `Developer mode`
5. Нажмите `Load unpacked`
6. Выберите папку `browser_extension`

## Что проверяет

- `POST /api/v1/fraud/check`
- `POST /api/v1/fraud/check-batch`

## Режимы

- При выключенном continuous mode используйте popup или context menu
- При включенном mode content script сканирует `href` и телефоны на странице и подсвечивает blacklist-совпадения
