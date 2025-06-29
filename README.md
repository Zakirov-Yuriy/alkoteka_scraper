# Alkoteka Scraper

Этот проект — Scrapy-краулер для парсинга каталога товаров с сайта [alkoteka.com](https://alkoteka.com).  
Собирает информацию о товарах по нескольким категориям, включая крепкий алкоголь, вино, слабоалкогольные и безалкогольные напитки.

## Установка
Клонируйте репозиторий:
git clone
cd alkoteka_scraper

## Создайте виртуальное окружение и установите зависимости
python -m venv .venv
.\.venv\Scripts\activate  # Windows
source .venv/bin/activate # Linux/macOS

pip install -r requirements.txt

## Для запуска краулера выполните команду
scrapy crawl spider_name -o output.json

