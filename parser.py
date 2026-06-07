import json
import logging
from pprint import pprint
import sys

import folium
from folium.plugins import HeatMap
import requests

from schemas import Root


logging.basicConfig(level = logging.DEBUG,
                    format= "[%(levelname)s] [%(name)s] %(message)s",
                    handlers=[logging.StreamHandler(sys.stderr)]
                    )                    
logger = logging.getLogger(__name__)

def check_categories(params):
    """Проверяет наличие категорий"""

    logger.info("Парсим категории.")
    url = "http://стат.гибдд.рф/opendataapi/v1/dictionary/rows?code=2"
    response = requests.get(url)
    response.raise_for_status() 
    data = response.json()
    dict_rows = data.get('results', [])[0].get('dict_rows', [])
    categories = []
    for row in dict_rows:
        if int(row.get('rows_code')) in params['pok']:
            categories.append(row.get('rows_name'))
        if "вело" in row.get('rows_name') and int(row.get('rows_code')) not in params['pok']:
            logger.warning("Обнаружен новый код для вело: %s, %s", int(row.get('rows_code')), row.get('rows_name'))
    logger.info("Имеются категории:\n\t- %s ", '\n\t- '.join(categories))

def parser(params):
    """Парсит данные"""

    logger.info("Парсим данные.")
    url = "http://стат.гибдд.рф/opendataapi/v1/kartdtp/rows"
    data = None
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()  # Проверка на ошибки HTTP (4xx/5xx)
        # Обработка ответа
        if response.status_code == 200:
            data = response.json()
            with open("/data/data.json", "w") as f:
                json.dump(data, f)
            logger.info("Успешный ответ стат.гибдд.рф")
        else:
            logger.warning("Ошибка:", response.status_code, response.text)
    except requests.exceptions.RequestException as e:
        logger.warning("Ошибка запроса:", e)


def main():
    logger.debug("'folium' in sys.modules: %s", 'folium' in sys.modules)
    
    params = {'pok': [39, 119, 131, 110], 'dat': '2.2024', 'reg': [1145, 1146]}
    # check_categories(params)
    parser(params)
    # http://стат.гибдд.рф/opendataapi/v1/kartdtp/rows?pok=39,119,131,110,&dat=3.2026&reg=1145,1146

    

if __name__ == "__main__":
    main()

