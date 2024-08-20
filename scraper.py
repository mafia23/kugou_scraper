import os
import re
import asyncio
import aiohttp
import pymysql
import requests
from flask import Flask, send_file, abort, request
from pyquery import PyQuery as pq
from selenium import webdriver
from selenium.common import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from concurrent.futures import ThreadPoolExecutor
import chardet

chrome_options = Options()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--disable-gpu')
chrome_options.add_argument('--no-sandbox')

def init_browser():
    return webdriver.Chrome(options=chrome_options)

db = pymysql.connect(
    host="localhost",
    user="root",
    password="root",
    port=3306,
    database='lyrics',
    charset='utf8'
)
cursor = db.cursor()
table = 'web_singer'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36'
}

async def fetch(session, url):
    async with session.get(url, headers=headers) as response:
        response_bytes = await response.read()
        detected_encoding = chardet.detect(response_bytes)['encoding']
        try:
            return response_bytes.decode(detected_encoding)
        except (UnicodeDecodeError, TypeError):
            return response_bytes.decode('utf-8', errors='replace')


async def parse_page(session, browser, page_number, category_number):
    url = f'http://www.kugou.com/yy/singer/index/{page_number}-all-{category_number}.html'
    browser.get(url)

    try:
        wait = WebDriverWait(browser, 5)  # 增加等待时间至 20 秒
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '.r ul li a')))
    except TimeoutException:
        print(f"TimeoutException: Elements not found on page {url}")
        return []  # 返回一个空列表，防止后续处理失败

    data_list = []
    html = browser.page_source  # 直接使用 Selenium 获取页面源代码
    doc = pq(html)

    for i in doc.remove('.pic').find('.r ul li a').items():
        href = i.attr('href')
        print(href)
        detail_html = await fetch(session, href)
        detail_doc = pq(detail_html)

        title = detail_doc('body > div.wrap.clear_fix > div.sng_ins_1 > div.top > div > div > strong').text()
        description = detail_doc('body > div.wrap.clear_fix > div.sng_ins_1 > div.top > div > p').text()
        img_url = detail_doc('body > div.wrap.clear_fix > div.sng_ins_1 > div.top > img').attr('_src')

        data = {
            'singername': title,
            'singerjieshao': description,
            'img_url': img_url,
            'singerImages': ''
        }
        print('data', data)
        data_list.append(data)

    return data_list


async def main():
    if not os.path.exists('img'):
        os.mkdir('img')
    os.chdir('img')

    all_data = []
    start_page = 1
    end_page = 5
    start_category = 2
    end_category = 11

    browser = init_browser()

    async with aiohttp.ClientSession() as session:
        tasks = []
        for category_number in range(start_category, end_category + 1):
            for page_number in range(start_page, end_page + 1):
                tasks.append(parse_page(session, browser, page_number, category_number))
        results = await asyncio.gather(*tasks)
        for result in results:
            all_data.extend(result)

    browser.quit()
    savedata(all_data)

def download_image(url):
    file_path = None
    try:
        response = requests.get(url)
        if response.status_code == 200:
            file_name = re.search(r'(\d+).jpg$', url)
            if file_name:
                file_path = file_name.group(1) + '.jpg'
                if not os.path.exists(file_path):
                    with open(file_path, 'wb') as f:
                        f.write(response.content)
                else:
                    print('Already downloaded!!!')
        return file_path
    except requests.ConnectionError:
        print("Downloading failed!!!")

def savetoMysql(data):
    keys = ','.join(data.keys())
    values = ','.join(['%s'] * len(data))
    sql = f'INSERT INTO {table}({keys}) VALUES ({values})'
    try:
        if cursor.execute(sql, tuple(data.values())):
            db.commit()
            print('Data inserted successfully')
    except pymysql.MySQLError as e:
        print('MySQL Error:', e)
        db.rollback()
    except Exception as e:
        print('General Error:', e)
        db.rollback()

def savedata(data_list):
    with ThreadPoolExecutor() as executor:
        for data in data_list:
            filepath = download_image(data.get('img_url'))
            if filepath:
                data['singerImages'] = filepath
                executor.submit(savetoMysql, data)

if __name__ == '__main__':
    asyncio.run(main())
    db.close()
