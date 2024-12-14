#!/usr/bin/python3
import logging
import concurrent.futures
import requests
import pymysql
#import tldextract
import re
import ssl
import urllib3
from bs4 import BeautifulSoup
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}

from pymysql.cursors import DictCursor
connection = pymysql.connect(
    host='localhost',
    user='dmsk',
    password='gKL3102gKL3102',
    db='dmsk',
    charset='utf8mb4',
    cursorclass=DictCursor
)

sku_id = {}
qty = {}
price = {}

with connection.cursor() as cursor:
    query = 'SELECT pm.post_id, pm.meta_key, pm.meta_value, p.id, p.post_type FROM wp_postmeta pm, wp_posts p WHERE pm.post_id = p.id AND p.post_type = "product" AND pm.meta_key = "_sku"'
    cursor.execute(query)
    for row in cursor:
        sku_id[row['meta_value']] = row['post_id']
connection.close()

user_agent = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}
with requests.Session() as session:
    session.post('https://www.sima-land.ru/', headers=user_agent)
    cookies = {
        'city_id': 'ed036ea4dd6c554e85e4dba33bf9090566f3dc2bd252b26e04e981ca106c81b7a%3A2%3A%7Bi%3A0%3Bs%3A7%3A%22city_id%22%3Bi%3A1%3Bs%3A10%3A%221686293227%22%3B%7D',
        'isCitySelected': '1',
        'country': '50fa73c1717e928f15414ffc679f880ea767aa7cd87af488d2b810a15b6312b1a%3A2%3A%7Bi%3A0%3Bs%3A7%3A%22country%22%3Bi%3A1%3Bs%3A2%3A%22RU%22%3B%7D'
    }

def writesql(sku, price, stock):
    connection = pymysql.connect(
        host='localhost',
        user='dmsk',
        password='gKL3102gKL3102',
        db='dmsk',
        charset='utf8mb4',
        cursorclass=DictCursor
    )
    with connection.cursor() as cursor:
        query = 'UPDATE `wp_postmeta` SET `meta_value`= 0 WHERE `meta_key`= "_stock"'
        cursor.execute(query)
        connection.commit()
        query = 'UPDATE `wp_postmeta` SET `meta_value`="outofstock" WHERE `meta_key`= "_stock_status"'
        cursor.execute(query)
        connection.commit()
        query = 'SELECT post_id FROM wp_postmeta WHERE meta_key = "_sku" AND meta_value = "'+str(sku)+'"'
        cursor.execute(query)
        for row in cursor:
            product_id = row['post_id']
        query = 'UPDATE `wp_postmeta` SET `meta_value`="'+str(stock)+'" WHERE `meta_key`= "_stock" AND `post_id` = "'+str(product_id)+'"'
        cursor.execute(query)
        connection.commit()
        query = 'UPDATE `wp_postmeta` SET `meta_value`="onstock" WHERE `meta_key`= "_stock_status" AND `post_id` = "' + str(product_id) + '"'
        cursor.execute(query)
        connection.commit()
        print(query)
        query = 'UPDATE `wp_postmeta` SET `meta_value`=' +str(price)+ ' WHERE `meta_key` IN("_regular_price", "_price", "_sale_price") AND `post_id` = "' + str(product_id) + '"'
        cursor.execute(query)
        connection.commit()
        print(query)
    connection.close()


def thread_function(prsku):
    logging.info("Апдейт ID = %s: starting", prsku)
    url = 'https://sima-land.ru/' + prsku
    try:
        r = requests.get(url, headers=user_agent, cookies=cookies, timeout=15, verify=None)
        if r.status_code == 200:
            html = r.content
            soup = BeautifulSoup(html, 'lxml')
            stock = soup.find('div', attrs={"data-testid": "cart-block:in-stock-text"}).text
            print(stock)
            if stock:
                qty_out = stock.replace('На складе ', '')
                qty = qty_out.replace(' шт.', '')
            else:
                qty = 100
            price = soup.find(attrs={"data-testid":"cart-block:price"}).text

            price = price.replace(',', '.')
            price_opt = float(price.replace('₽', ''))
            print(price_opt)
            if price_opt < 50:
                price_out = price_opt * 3
            elif price_opt < 100:
                price_out = price_opt * 2
            elif price_opt < 1000:
                price_out = price_opt * 1.6
            else:
                price_out = price_opt * 1.3
            print(price_out)
        #    writesql(prsku, price_out, qty)

    except Exception:
        print('Запрос не выполнен')
        logging.info("Апдейт ID = %s: finishing", prsku)



#запуск потоков
if __name__ == "__main__":
    format = "%(asctime)s: %(message)s"
    logging.basicConfig(format=format, level=logging.INFO,
                        datefmt="%H:%M:%S")
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        executor.map(thread_function, sku_id)

