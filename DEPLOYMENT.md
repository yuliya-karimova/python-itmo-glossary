# Инструкции по развертыванию

## 🌐 Развертывание на публичном сервере

### Вариант 1: Docker на VPS

#### Шаг 1: Подготовка сервера

```bash
# Обновление системы (Ubuntu/Debian)
sudo apt update && sudo apt upgrade -y

# Установка Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Установка Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

#### Шаг 2: Клонирование и запуск

```bash
# Клонирование репозитория
git clone <your-repository-url>
cd python-itmo-glossary

# Запуск приложения
docker compose up -d

# Проверка статуса
docker compose ps

# Примечание: Для старых версий Docker используйте docker-compose вместо docker compose
```

#### Шаг 3: Настройка Nginx (опционально)

Создайте файл `/etc/nginx/sites-available/glossary`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Активируйте конфигурацию:

```bash
sudo ln -s /etc/nginx/sites-available/glossary /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### Вариант 2: Heroku

#### Шаг 1: Установка Heroku CLI

```bash
# macOS
brew tap heroku/brew && brew install heroku

# Linux
curl https://cli-assets.heroku.com/install.sh | sh
```

#### Шаг 2: Создание Procfile

Создайте файл `Procfile` в корне проекта:

```
web: uvicorn main:app --host 0.0.0.0 --port $PORT
```

#### Шаг 3: Развертывание

```bash
# Вход в Heroku
heroku login

# Создание приложения
heroku create your-app-name

# Развертывание
git push heroku main

# Открытие приложения
heroku open
```

### Вариант 3: Yandex Cloud

#### Шаг 1: Создание Container Registry

1. Перейдите в Yandex Cloud Console
2. Создайте Container Registry
3. Получите токен доступа

#### Шаг 2: Сборка и загрузка образа

```bash
# Авторизация
docker login --username iam --password <token> cr.yandex

# Сборка образа
docker build -t cr.yandex/<registry-id>/glossary-api:latest .

# Загрузка образа
docker push cr.yandex/<registry-id>/glossary-api:latest
```

#### Шаг 3: Создание серверной группы

1. В Yandex Cloud Console создайте серверную группу
2. Выберите загруженный образ
3. Настройте балансировщик нагрузки
4. Откройте порт 8000

### Вариант 4: Railway

#### Шаг 1: Подготовка

1. Зарегистрируйтесь на [Railway.app](https://railway.app)
2. Подключите GitHub репозиторий

#### Шаг 2: Развертывание

1. Создайте новый проект
2. Выберите репозиторий
3. Railway автоматически определит Dockerfile
4. Приложение будет развернуто автоматически

### Вариант 5: Render

#### Шаг 1: Подготовка

1. Зарегистрируйтесь на [Render.com](https://render.com)
2. Подключите GitHub репозиторий

#### Шаг 2: Создание Web Service

1. Создайте новый Web Service
2. Выберите репозиторий
3. Укажите:
   - **Build Command**: `docker build -t glossary-api .`
   - **Start Command**: `docker run -p $PORT:8000 glossary-api`
4. Нажмите "Create Web Service"

## 🔒 Настройка HTTPS (SSL)

### Использование Let's Encrypt с Nginx

```bash
# Установка Certbot
sudo apt install certbot python3-certbot-nginx

# Получение сертификата
sudo certbot --nginx -d your-domain.com

# Автоматическое обновление
sudo certbot renew --dry-run
```

## 📊 Мониторинг

### Проверка логов

```bash
# Docker Compose
docker compose logs -f

# Docker
docker logs -f glossary-backend
```

### Проверка здоровья приложения

```bash
curl http://localhost:8000/
```

## 🔄 Обновление приложения

```bash
# Остановка
docker compose down

# Обновление кода
git pull

# Пересборка и запуск
docker compose up -d --build
```

## 💾 Резервное копирование базы данных

```bash
# Создание резервной копии
docker exec glossary-backend sqlite3 /app/glossary.db .dump > backup.sql

# Восстановление
cat backup.sql | docker exec -i glossary-backend sqlite3 /app/glossary.db
```

## 🌍 Переменные окружения

Создайте файл `.env` для настройки:

```env
DATABASE_URL=sqlite:///./glossary.db
HOST=0.0.0.0
PORT=8000
```

И обновите `docker-compose.yml`:

```yaml
services:
  glossary-api:
    env_file:
      - .env
```

## 📝 Чек-лист развертывания

- [ ] Сервер подготовлен (Docker установлен)
- [ ] Репозиторий склонирован
- [ ] Приложение запущено и работает
- [ ] Проверен доступ к API (http://your-server:8000/docs)
- [ ] Проверен доступ к фронтенду (http://your-server:8000/static/index.html)
- [ ] Настроен Nginx (если используется)
- [ ] Настроен SSL/HTTPS (если используется)
- [ ] Настроено резервное копирование
- [ ] Настроен мониторинг (опционально)

## 🆘 Решение проблем

### Проблема: Приложение не запускается

```bash
# Проверка логов
docker-compose logs

# Проверка портов
netstat -tulpn | grep 8000
```

### Проблема: База данных не создается

```bash
# Проверка прав доступа
ls -la glossary.db

# Пересоздание базы данных
rm glossary.db
docker-compose restart
```

### Проблема: Статические файлы не загружаются

```bash
# Проверка наличия папки static
ls -la static/

# Проверка монтирования в docker-compose.yml
```

---

**Примечание**: После развертывания добавьте скриншоты работающего приложения в папку `screenshots/` для отчета.

