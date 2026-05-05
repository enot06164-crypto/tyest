# 🔥 Искра (Iskra)

**Безопасная анонимная социальная сеть**, вдохновлённая ВКонтакте и Teleguard.

## Особенности

- 🔒 **Анонимная регистрация** — только username + пароль, никаких телефонов/email
- 🔐 **E2EE Шифрование** — сквозное шифрование сообщений
- 🛡️ **Максимальная безопасность** — bcrypt, JWT, защита от атак
- 💬 **Мгновенные сообщения** — WebSocket для real-time чатов
- 👥 **Группы и друзья** — полноценная социальная сеть
- 📱 **Адаптивный дизайн** — работает на всех устройствах

## Технологии

- **Backend:** FastAPI (Python)
- **Database:** SQLite (SQLAlchemy ORM)
- **Frontend:** HTML5 + CSS3 + Vanilla JS
- **Real-time:** WebSocket
- **Auth:** JWT + bcrypt
- **E2EE:** Fernet (cryptography)

## Быстрый старт

```bash
# 1. Клонируйте репозиторий
cd iskra

# 2. Установите зависимости
pip install -r requirements.txt

# 3. Запустите сервер
python main.py

# 4. Откройте в браузере
http://localhost:8000
```

## API Документация

После запуска доступна автоматическая документация:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Структура проекта

```
iskra/
├── app/
│   ├── models/          # SQLAlchemy модели
│   ├── routers/         # API роутеры
│   ├── schemas/         # Pydantic схемы
│   ├── services/        # Сервисы (auth, crypto)
│   ├── static/          # CSS, JS, изображения
│   ├── templates/       # HTML шаблоны
│   └── config.py        # Конфигурация
├── main.py              # Точка входа
├── requirements.txt     # Зависимости
└── README.md           # Этот файл
```

## Безопасность

- ✅ Пароли хешируются **bcrypt** (стоимость 12)
- ✅ **JWT токены** с автоматическим обновлением
- ✅ **E2EE шифрование** сообщений
- ✅ Защита от **SQL-инъекций** (ORM)
- ✅ **CORS** политики
- ✅ **Rate limiting**
- ✅ Анонимная регистрация (никаких персональных данных)

## Лицензия

MIT License
