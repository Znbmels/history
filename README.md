# Telegram-бот для аудиоуроков

## Подготовка сервера и деплой

### 1. Подключение к серверу

```bash
ssh root@92.38.49.45
```

### 2. Установка Docker и Docker Compose

```bash
# Обновление пакетов
apt update
apt upgrade -y

# Установка необходимых пакетов
apt install -y apt-transport-https ca-certificates curl software-properties-common

# Добавление официального GPG-ключа Docker
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Добавление репозитория Docker
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

# Обновление пакетов после добавления репозитория
apt update

# Установка Docker
apt install -y docker-ce docker-ce-cli containerd.io

# Установка Docker Compose
apt install -y docker-compose-plugin

# Проверка установки Docker
docker --version
docker compose version

# Добавление текущего пользователя в группу docker
usermod -aG docker $USER
```

### 3. Клонирование репозитория с проектом

```bash
# Создание рабочей директории
mkdir -p /opt/telegram-bot
cd /opt/telegram-bot

# Загрузка файлов проекта
# Вы можете использовать Git или просто скопировать файлы на сервер
# с помощью scp или другого инструмента
```

### 4. Копирование файлов проекта на сервер

С локального компьютера используйте команду scp для копирования файлов:

```bash
# Замените путь/к/локальной/директории на реальный путь к папке с проектом
scp -r путь/к/локальной/директории/* root@92.38.49.45:/opt/telegram-bot/
```

### 5. Запуск контейнеров

```bash
cd /opt/telegram-bot
docker compose up -d
```

### 6. Проверка статуса контейнеров

```bash
docker ps
```

### 7. Просмотр логов бота

```bash
docker logs telegram-bot
```

### 8. Перезапуск бота (при необходимости)

```bash
docker compose restart telegram-bot
```

### 9. Остановка контейнеров (при необходимости)

```bash
docker compose down
```

## Важные замечания

1. База данных PostgreSQL сохраняет свои данные в именованном томе Docker (`postgres_data`), что обеспечивает сохранность данных между перезапусками.

2. Файлы уроков и видео монтируются как тома, поэтому их можно обновлять без пересборки образа.

3. Настройки подключения к базе данных и Telegram API-токен настроены в `docker-compose.yml`. 