import requests
import sqlite3
from pyquery import PyQuery as pq
from selenium.common import TimeoutException
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import chardet
import logging
import os

# 设置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

service = Service(executable_path=ChromeDriverManager().install())
# 定义 HTTP 请求头
options = webdriver.ChromeOptions()
options.add_argument("--headless")
options.add_argument("--disable-gpu")
options.add_argument("--disable-extensions")
options.add_argument("--disable-infobars")
options.add_argument("--start-maximized")
options.add_argument("--disable-notifications")
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')

def init_browser():
    return webdriver.Chrome(service=service, options=options)

# 获取当前脚本文件所在目录，并在该目录下创建数据库文件路径
script_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(script_dir, 'lyrics.db')

def create_table_if_not_exists():
    with sqlite3.connect(db_path) as db:
        cursor = db.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS web_singer (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            singername TEXT UNIQUE,
            singerjieshao TEXT,
            img_url TEXT,
            singerImages TEXT
        )
        ''')
        db.commit()

def fetch(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.5735.90 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # 如果请求失败，抛出异常
        response_bytes = response.content
        detected_encoding = chardet.detect(response_bytes)['encoding']
        try:
            return response_bytes.decode(detected_encoding)
        except (UnicodeDecodeError, TypeError):
            return response_bytes.decode('utf-8', errors='replace')
    except requests.RequestException as e:
        logging.error(f"请求失败: {url} - {e}")
        return ""

def parse_page(browser, page_number, category_number):
    url = f'http://www.kugou.com/yy/singer/index/{page_number}-all-{category_number}.html'
    browser.get(url)

    try:
        wait = WebDriverWait(browser, 10)  # 增加等待时间至 10 秒
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '.r ul li a')))
    except TimeoutException:
        logging.error(f"超时异常: 在页面 {url} 上未找到元素")
        return []  # 返回一个空列表，防止后续处理失败

    data_list = []
    html = browser.page_source
    logging.info(f"解析页面 {url}")
    doc = pq(html)

    for i in doc.remove('.pic').find('.r ul li a').items():
        href = i.attr('href')
        logging.info(f"获取详细信息 {href}")
        try:
            detail_html = fetch(href)
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
            logging.info(f"提取的数据: {data}")

            data_list.append(data)
        except Exception as e:
            logging.error(f"获取详细信息时出错 {href}: {e}")
    return data_list

def is_singer_in_db():
    with sqlite3.connect(db_path) as db:
        cursor = db.cursor()
        cursor.execute('SELECT COUNT(*) FROM web_singer')
        count = cursor.fetchone()[0]
    return count > 0

def main():
    create_table_if_not_exists()

    if not is_singer_in_db():
        all_data = []
        start_page = 1
        end_page = 5
        start_category = 2
        end_category = 11

        browser = init_browser()

        for category_number in range(start_category, end_category + 1):
            for page_number in range(start_page, end_page + 1):
                result = parse_page(browser, page_number, category_number)
                all_data.extend(result)

        browser.quit()  # 确保浏览器在所有任务完成后被正确关闭
        savedata(all_data)
    else:
        logging.info("数据库中已经有数据，跳过数据抓取。")

def savetoSQLite(data):
    keys = ', '.join(data.keys())
    values = ', '.join(['?'] * len(data))
    sql = f'INSERT INTO web_singer({keys}) VALUES ({values})'
    try:
        with sqlite3.connect(db_path) as db:
            cursor = db.cursor()
            cursor.execute(sql, tuple(data.values()))
            db.commit()
        logging.info('数据插入成功')
    except sqlite3.IntegrityError:
        logging.warning(f'跳过已经存在的数据: {data["singername"]}')
    except sqlite3.Error as e:
        logging.error(f'SQLite 错误: {e}')
    except Exception as e:
        logging.error(f'一般错误: {e}')

def savedata(data_list):
    for data in data_list:
        savetoSQLite(data)

if __name__ == '__main__':
    try:
        main()  # 使用同步函数执行
    except Exception as e:
        logging.error(f"运行时发生错误: {e}")
