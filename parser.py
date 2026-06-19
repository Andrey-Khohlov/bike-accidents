import json
import logging
import os
import sys
from time import sleep
import requests
from requests.exceptions import RequestException

from tqdm import tqdm

from custom_exceptions import DateRangeError
from schemas import Root


logging.basicConfig(level = logging.INFO,
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
            categories.append(f"{row.get('rows_code')}: {row.get('rows_name')}")
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

def fetch_and_save(url, params, filepath, logger):
    """Выполняет запрос, сохраняет JSON в файл. Возвращает bool: успех или нет."""
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()  # бросает HTTPError при 4xx/5xx
        data = response.json()
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except RequestException as e:
        logger.debug("Ошибка запроса для %s: %s", params, e)
        return False
        
def parser(pok, reg, okrug, start_date, end_date, path):
    """Парсит данные c сайта стат.гибдд.рф с заданными params в диапазоне указанных дат."""

    logger.info("Парсим данные.")
    
    url = "http://стат.гибдд.рф/opendataapi/v1/kartdtp/rows"
    data = None
    try:
        dates = generate_dates(start_date, end_date)
    except DateRangeError as e:
        logger.exception(e)
        raise
    params = dict()
    params['pok'] = ','.join((str(i) for i in pok))
    params['reg'] = ','.join((str(i) for i in reg))
    
    exist_files = [x for x in os.listdir(path) if x.endswith('json')]
    exist_files.sort(key=lambda x: tuple(map(int, x.split('.')[0].split('_')[1].split('-'))))
    logger.debug("exist_files: %s", exist_files)
    exist_files = os.listdir(path)

    broken_files = []
    for date in tqdm(dates):
        name = "-".join(date.split('.')[::-1])  # DD.MM.YYYY -> YYYY-MM-DD
        main_file = f"{okrug}_{name}.json"
        
        if main_file in exist_files:
            continue

        # Попытка получить данные по всем регионам сразу
        params_full = params | {'dat': date} 
        if fetch_and_save(url, params_full, path + "/" + main_file, logger):
            logger.info("Успешный ответ для %s (все регионы)", date)
            continue

        # Если не вышло — Уровень 2: пробуем по каждому региону отдельно
        broken_files.append(main_file)
        regions = params_full['reg'].split(',')
        params_reg = params_full.copy()

        logger.debug("Расщепляем регионы %s для даты %s", regions, date)
        
        for reg in regions:
            reg_file = f"{okrug}_{name}_{reg}.json"
            if reg_file in exist_files:
                continue
    
            params_reg['reg'] = reg        
            if fetch_and_save(url, params_reg, path + "/" + reg_file, logger):
                logger.info("Успешный ответ для даты %s и региона %s", date, reg)
            else:
                #  Уровень 3: пробуем по каждому pok внутри этого региона
                broken_files.append(reg_file)
                pok_list = params_reg['pok'].split(',')
                params_pok = params_reg.copy()
                logger.debug("Расщепляем регион %s на pok: %s", reg, pok_list)
                for pok in pok_list:
                    pok_file = f"{okrug}_{name}_{reg}_pok_{pok}.json"
                    if pok_file in exist_files:
                        continue
                    params_pok['pok'] = pok
                    if fetch_and_save(url, params_pok, path + "/" + pok_file, logger):
                        logger.info("Успех для даты %s, регион %s, pok %s", date, reg, pok)
                    else:
                        broken_files.append(pok_file)
                        logger.debug("Не удалось получить данные для pok %s региона %s", pok, reg)
                    sleep(1)
            sleep(2)
        sleep(5)
    if broken_files:
        logger.info("Не удалось получить данные для: \n%s", "\n".join(broken_files))
    else:
        logger.info("Все запланированные файлы получены успешно.")

def main():
    logger.debug("'folium' in sys.modules: %s", 'folium' in sys.modules)

    pok = [39, 119, 131, 110]
    reg_msk = [1145, 1146],  # мск и обл
    reg_cfo = [
        1114,  # 1 Белгородская область
        1115,  # 2 Брянская область
        1117,  # 3 Владимирская область
        1120,  # 4 Воронежская область
        1124,  # 5 Ивановская область
        1129,  # 6 Калужская область
        1134,  # 7 Костромская область
        1138,  # 8 Курская область
        1142,  # 9 Липецкая область
        1154,  # 11 Орловская область
        1161,  # 12 Рязанская область
        1166,  # 13 Смоленская область
        1168,  # 14 Тамбовская область
        1128,  # 15 Тверская область
        1170,  # 16 Тульская область
        1178,  # 17 Ярославская область
    ]  # ЦФО: 
    
    params = {
    'pok': [39, 119, 131, 110],
    # 'reg': [1145, 1146],  # мск и обл
    'reg': [
        1114,  # 1 Белгородская область
        1115,  # 2 Брянская область
        1117,  # 3 Владимирская область
        1120,  # 4 Воронежская область
        1124,  # 5 Ивановская область
        1129,  # 6 Калужская область
        1134,  # 7 Костромская область
        1138,  # 8 Курская область
        1142,  # 9 Липецкая область
        1154,  # 11 Орловская область
        1161,  # 12 Рязанская область
        1166,  # 13 Смоленская область
        1168,  # 14 Тамбовская область
        1128,  # 15 Тверская область
        1170,  # 16 Тульская область
        1178,  # 17 Ярославская область
    ]  # ЦФО: 
    }
    check_categories(params)
    # parser(pok=pok, reg=reg_msk, okrug='msk', start_date='1.2015', end_date='5.2026', path='data_msk')
    parser(pok=pok, reg=reg_cfo, okrug='cfo', start_date='1.2015', end_date='5.2026', path='data_cfo')


if __name__ == "__main__":
    main()

