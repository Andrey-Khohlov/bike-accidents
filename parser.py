from copy import deepcopy
import json
import logging
import os
import sys
from datetime import datetime
from pprint import pprint

import folium
from folium.plugins import HeatMap
import requests
from dateutil import relativedelta

from custom_exceptions import DateRangeError
from schemas import Root


logging.basicConfig(level = logging.DEBUG,
                    format= "[%(levelname)s] [%(name)s] %(message)s",
                    handlers=[logging.StreamHandler(sys.stderr)]
                    )                    
logger = logging.getLogger(__name__)

def check_categories(params):
    """
    Проверяет целостность категорий в params:
        - наличие категорий, указанных в params.
        - отсутствие категорий с вело, отсутствующих в params
    """

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


def generate_dates(start_date, end_date):
    """
    Генерирует список дат от (start_month, start_year) до (end_month, end_year) включительно.

    :start_date: начальный месяц в формате 'M.YYYY'
    :end_date: конечный месяц в формате 'M.YYYY'
    :return: список строк с датами в формате 'M.YYYY'
    """
    dates = []
    start_month, start_year = (int(i) for i in start_date.split('.'))
    end_month, end_year = (int(i) for i in end_date.split('.'))
    month, year = start_month, start_year

    if (end_year < start_year) or (end_year == start_year and end_month < start_month):
        error_msg = f"Конечная дата {end_month}.{end_year} не может быть раньше начальной {start_month}.{start_year}"
        raise DateRangeError(error_msg)

    while (year < end_year) or (year == end_year and month <= end_month):
        dates.append(f"{month}.{year}")
        month += 1
        if month > 12:
            month = 1
            year += 1
    return dates

def parser(params, start_date, end_date):
    """Парсит данные c сайта стат.гибдд.рф с заданными params в диапазоне указанных дат."""

    logger.info("Парсим данные.")
    url = "http://стат.гибдд.рф/opendataapi/v1/kartdtp/rows"
    data = None
    try:
        dates = generate_dates(start_date, end_date)
    except DateRangeError as e:
        logger.exception(e)
        raise
    params['pok'] = ','.join((str(i) for i in params['pok']))
    params['reg'] = ','.join((str(i) for i in params['reg']))
    exist_files = os.listdir('data')
    logger.debug("exist_files: %s", sorted(exist_files))
    for date in dates:
        name = "-".join(date.split('.')[::-1])
        if f"msk_{name}.json" in exist_files:
            continue
        try:
            
            response = requests.get(url, params=params | {'dat': date})
            data = response.json()
            with open(f"data/msk_{name}.json", "w") as f:
                json.dump(data, f)
            logger.info("Успешный ответ стат.гибдд.рф для %s", date)
        except requests.exceptions.RequestException as e:
            logger.warning("Ошибка запроса:", e)
            regs = params['reg'].split(',')
            logger.debug("Расщепляем регионы %s для даты %s", regs, date)
            for reg in regs:
                if f"msk_{name}_{reg}.json" in exist_files:
                    continue
                params_reg = params.copy()
                params_reg['reg'] = reg
                try:
                    response = requests.get(url, params=params_reg)
                    data = response.json()
                    with open(f"data/msk_{name}_{reg}.json", "w") as f:
                        json.dump(data, f)
                    logger.info("Успешный ответ стат.гибдд.рф для даты %s и региона %s", date, reg)
                except requests.exceptions.RequestException as e:
                    logger.warning("Снова шибка запроса:", e)
        except Exception as e:
            logger.exception("Ошибка парсинга: %s", e)      
            raise


def main():
    logger.debug("'folium' in sys.modules: %s", 'folium' in sys.modules)
    
    params = {
    'pok': [39, 119, 131, 110],
    'reg': [1145, 1146]
    }
    # check_categories(params)
    parser(params, start_date='1.2015', end_date='5.2026')


if __name__ == "__main__":
    main()

