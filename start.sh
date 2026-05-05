#!/bin/bash
echo "🔥 Запуск Искры..."
echo "Установка зависимостей..."
pip install -r requirements.txt
echo "Запуск сервера..."
python main.py
