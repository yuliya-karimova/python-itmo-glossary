# Быстрый старт

## Запуск через Docker Compose (рекомендуется)

```bash
# Клонируйте репозиторий
git clone <your-repo-url>
cd python-itmo-glossary

# Запустите приложение
docker compose up --build

# Откройте в браузере
# http://localhost:8000 - фронтенд
# http://localhost:8000/docs - API документация
```

## Локальный запуск

```bash
# Установите зависимости
pip install -r requirements.txt

# Импортируйте данные
python app/import_data.py

# Запустите сервер
uvicorn app.main:app --reload
```

## Проверка работы

1. Откройте http://localhost:8000 - должна загрузиться страница с визуализацией графа
2. Откройте http://localhost:8000/docs - должна открыться документация API
3. Попробуйте получить список терминов:
   ```bash
   curl http://localhost:8000/api/terms
   ```

## Структура данных

- `terms.csv` - термины и их определения
- `links.csv` - связи между терминами для построения графа

Данные автоматически импортируются при первом запуске приложения.

