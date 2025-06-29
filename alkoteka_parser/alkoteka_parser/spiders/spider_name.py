import scrapy
from datetime import datetime
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
import random


START_URLS = [
    "https://alkoteka.com/web-api/v1/product?city_uuid=4a70f9e0-46ae-11e7-83ff-00155d026416&page=1&per_page=150&root_category_slug=krepkiy-alkogol",
    "https://alkoteka.com/web-api/v1/product?city_uuid=4a70f9e0-46ae-11e7-83ff-00155d026416&page=1&per_page=150&root_category_slug=vino",
    "https://alkoteka.com/web-api/v1/product?city_uuid=4a70f9e0-46ae-11e7-83ff-00155d026416&page=1&per_page=150&root_category_slug=slaboalkogolnye-napitki-2"

]


def update_url_page(url, page_number):
    parts = urlparse(url)
    query = parse_qs(parts.query)
    query['page'] = [str(page_number)]
    new_query = urlencode(query, doseq=True)
    return urlunparse(parts._replace(query=new_query))

PROXIES = [
    'http://51.81.245.3:17981'
]

class AlkotekaSpider(scrapy.Spider):
    name = "spider_name"  # ВАЖНО: имя для запуска!
    allowed_domains = ["alkoteka.com"]

    custom_headers = {
        "accept": "*/*",
        "accept-encoding": "gzip, deflate, br",
        "accept-language": "ru,en;q=0.9",
        "referer": "https://alkoteka.com/catalog/krepkiy-alkogol?city_uuid=4a70f9e0-46ae-11e7-83ff-00155d026416",
        "sec-ch-ua": '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
    }

    cookies = {
        "alkoteka_age_confirm": "true",
        "alkoteka_geo": "true",
        "alkoteka_cookies": "true",
        "alkoteka_locality": '{"uuid":"4a70f9e0-46ae-11e7-83ff-00155d026416","name":"Краснодар","slug":"krasnodar","longitude":"38.975996","latitude":"45.040216","accented":true}'
    }

    def get_random_proxy(self):
        return random.choice(PROXIES)

    def start_requests(self):
        for url in START_URLS:
            proxy = self.get_random_proxy()
            self.logger.debug(f"[START] Используем прокси: {proxy}")
            yield scrapy.Request(
                url,
                headers=self.custom_headers,
                cookies=self.cookies,
                callback=self.parse,
                meta={'proxy': proxy}
            )

    def parse(self, response):
        try:
            data = response.json()
        except Exception:
            self.logger.error(f"Ошибка парсинга JSON с {response.url}")
            return

        # Добавь сюда логи для отладки
        self.logger.info(f"Получено ключей в data: {list(data.keys())}")
        self.logger.info(f"Поле 'data': {data.get('data')}")

        products = data.get('results', [])

        current = data.get('data', {}).get('page', 1)
        total = data.get('data', {}).get('pages', 1)

        self.logger.info(f"Страница {current} из {total}, товаров на странице: {len(products)}")

        for product in products:
            slug = product.get("slug")
            if not slug:
                continue

            detail_url = f"https://alkoteka.com/web-api/v1/product/{slug}?city_uuid=4a70f9e0-46ae-11e7-83ff-00155d026416"
            proxy = self.get_random_proxy()
            self.logger.debug(f"[DETAIL] Продукт: {slug}, прокси: {proxy}")
            yield scrapy.Request(
                url=detail_url,
                headers=self.custom_headers,
                cookies=self.cookies,
                callback=self.parse_product,
                meta={'proxy': proxy, 'product': product}
            )

        current = data.get('data', {}).get('page', 1)
        total = data.get('data', {}).get('pages', 1)
        if current < total:
            next_url = update_url_page(response.url, current + 1)
            proxy = self.get_random_proxy()
            self.logger.debug(f"[NEXT PAGE] {next_url}, прокси: {proxy}")
            yield scrapy.Request(
                next_url,
                headers=self.custom_headers,
                cookies=self.cookies,
                callback=self.parse,
                meta={'proxy': proxy}
            )

    def parse_product(self, response):
        base_product = response.meta['product']
        try:
            data = response.json()
        except Exception:
            self.logger.error(f"Ошибка парсинга JSON с {response.url}")
            return

        self.logger.info(f"Продукт {base_product.get('name')}, quantity = {base_product.get('quantity')}")

        product_data = data.get("results", {})

        brand = ""
        for block in product_data.get("description_blocks", []):
            if block.get("code") == "brend":
                values = block.get("values", [])
                if values:
                    brand = values[0].get("name", "")
                break

        if not brand:
            for label in data.get("filter_labels", []):
                if label.get("filter") == "brend":
                    brand = label.get("title", "")
                    break

        if not brand:
            for label in base_product.get("filter_labels", []):
                if label.get("filter") == "brend":
                    brand = label.get("title", "")
                    break

        if not brand:
            subname = data.get("subname", "")
            if subname:
                brand = subname.split()[0]

        if not brand:
            name = base_product.get("name", "")
            if name:
                brand = name.split()[0]

        description = ""
        for block in product_data.get("text_blocks", []):
            if block.get("title", "").lower().strip() == "описание":
                description = block.get("content", "").strip()
                break

        if not description:
            for block in product_data.get("description_blocks", []):
                if block.get("code") in ["opisanie", "dopolnitelnoe_opisanie"]:
                    values = block.get("values", [])
                    if values:
                        description = values[0].get("text", "").strip()
                    if description:
                        break

        if not description:
            description = product_data.get("description", "").strip()

        if not description:
            description = product_data.get("meta_description", "").strip()

        if not description:
            description = product_data.get("subname", "").strip()

        if not description:
            self.logger.info(f"[{base_product.get('name')}] Описание не найдено. Пробуем HTML-страницу.")
            product_url = base_product.get("product_url") or base_product.get("url")
            if product_url:
                proxy = self.get_random_proxy()
                self.logger.debug(f"[HTML] Описание из HTML. Продукт: {base_product.get('name')}, прокси: {proxy}")
                yield scrapy.Request(
                    url=product_url,
                    headers=self.custom_headers,
                    cookies=self.cookies,
                    callback=self.parse_description_html,
                    meta={
                        'base_product': base_product,
                        'brand': brand,
                        'proxy': proxy
                    }
                )
                return

        yield self.build_item(base_product, brand, description, product_data)

    def parse_description_html(self, response):
        base_product = response.meta['base_product']
        brand = response.meta['brand']

        description = response.xpath('//p[@class="product-info__description-text"]/text()').get()

        if description:
            description = description.strip()
            self.logger.debug(f"[{base_product.get('name')}] Описание из HTML: {description[:100]}...")
        else:
            self.logger.warning(f"[{base_product.get('name')}] Описание не найдено на HTML-странице: {response.url}")

        yield self.build_item(base_product, brand, description or "", {})

    def build_item(self, base_product, brand, description, full_product):
        return {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "RPC": base_product.get("uuid"),
            "url": base_product.get("product_url") or base_product.get("url") or "",
            "title": self.construct_title(base_product),
            "marketing_tags": [],
            "brand": brand,
            "section": self.get_section(base_product),
            "price_data": self.get_price_data(base_product),
            "stock": {
                "in_stock": bool(base_product.get("quantity")),
                "count": int(base_product.get("quantity") or 0)
            },
            "assets": {
                "main_image": base_product.get("image_url"),
                "set_images": [base_product.get("image_url")] if base_product.get("image_url") else [],
                "view360": [],
                "video": []
            },
            "metadata": self.get_metadata(base_product, description, full_product),
            "variants": self.count_variants(base_product)
        }

    def construct_title(self, product):
        base = product.get("name", "")
        vol = next((f["title"] for f in product.get("filter_labels", []) if f["filter"] == "obem"), "")
        return f"{base}, {vol}" if vol else base

    def get_section(self, product):
        child = product.get("category", {}).get("name")
        parent = product.get("category", {}).get("parent", {}).get("name")
        return [s for s in [parent, child] if s]

    def get_price_data(self, product):
        cur = product.get("price")
        orig = product.get("prev_price")

        if cur is None:
            cur = 0

        if orig is None:
            orig = cur

        if orig > cur:
            discount = round((orig - cur) / orig * 100)
            sale = f"Скидка {discount}%"
        else:
            sale = ""

        return {"current": float(cur), "original": float(orig), "sale_tag": sale}

    def get_metadata(self, product, description, full_product):
        meta = {"__description": description}

        for f in product.get("filter_labels", []):
            key = f.get("filter", "").strip()
            value = f.get("title", "").strip()
            if key and value:
                meta[key] = value

        for block in full_product.get("description_blocks", []):
            code = block.get("code", "").strip()
            values = block.get("values", [])
            if code and values:
                value = values[0].get("name") or values[0].get("text")
                if value:
                    meta[code] = value.strip()
            elif code in ["krepost", "obem"]:
                min_val = block.get("min")
                max_val = block.get("max")
                if min_val == max_val and min_val is not None:
                    meta[code] = str(min_val)

        for key in ["vendor_code", "code", "country", "subname", "country_name"]:
            value = full_product.get(key)
            if value:
                meta[key] = str(value).strip()

        return meta

    def count_variants(self, product):
        cnt = 0
        for f in product.get("filter_labels", []):
            if f.get("filter") in ["obem", "tsvet"]:
                cnt += 1
        return cnt
