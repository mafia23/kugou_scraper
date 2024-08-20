import os
import asyncio
import aiohttp
import sqlite3
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

# SQLite 数据库设置
db = sqlite3.connect('lyrics.db')
cursor = db.cursor()
table = 'web_singer'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36'
}

# 如果表不存在则创建
cursor.execute(f'''
CREATE TABLE IF NOT EXISTS {table} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    singername TEXT UNIQUE,
    singerjieshao TEXT,
    img_url TEXT,
    singerImages TEXT
)
''')
db.commit()

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
        wait = WebDriverWait(browser, 10)  # 增加等待时间至 10 秒
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '.r ul li a')))
    except TimeoutException:
        print(f"超时异常: 在页面 {url} 上未找到元素")
        return []  # 返回一个空列表，防止后续处理失败

    data_list = []
    html = browser.page_source
    print(browser.title)
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
        print('数据', data)


        data_list.append(data)

    return data_list

def is_singer_in_db():
    cursor.execute(f'SELECT COUNT(*) FROM {table}')
    count = cursor.fetchone()[0]
    return count > 0

async def main():
    if not is_singer_in_db():
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
    else:
        print("数据库中已经有数据，跳过数据抓取。")

def savetoSQLite(data):
    keys = ', '.join(data.keys())
    values = ', '.join(['?'] * len(data))
    sql = f'INSERT INTO {table}({keys}) VALUES ({values})'
    try:
        cursor.execute(sql, tuple(data.values()))
        db.commit()
        print('数据插入成功')
    except sqlite3.IntegrityError:
        # 处理已经存在的数据
        print(f'跳过已经存在的数据: {data["singername"]}')
    except sqlite3.Error as e:
        print('SQLite 错误:', e)
        db.rollback()
    except Exception as e:
        print('一般错误:', e)
        db.rollback()

def savedata(data_list):
    for data in data_list:
        savetoSQLite(data)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"运行时发生错误: {e}")
    finally:
        db.close()