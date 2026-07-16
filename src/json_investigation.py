
import json
import logging
import os
from pprint import pprint
import sys

import pydantic_core

from schemas import Root


logging.basicConfig(level = logging.DEBUG,
                    format= "[%(levelname)s] [%(name)s] %(message)s",
                    handlers=[logging.StreamHandler(sys.stderr)]
                    )                    
logger = logging.getLogger(__name__)

def schema_investigation(file):
    """Исследование структуры и содержания json"""

    with open(file, 'r', encoding='utf-8') as f:
        raw_json = json.load(f)

    try:
        data = Root.model_validate(raw_json)
        # pprint(Root.model_json_schema())
        accident = data.results.region_list[0].pok_list[0].result.dtpcardlist.info_dtp[0]
        

        print("\033[1;93mAccident coords:\033[0m", accident.coord_l, accident.coord_w)

        print("\033[1;93m\nAccident vehicals (ts) data:\033[0m") 
        for accident_ts in accident.ts_info:
            pprint(accident_ts.model_dump())

        print("\033[1;93m\nAccident full info (info_dtp) as Pydantic schema:\033[0m") 
        pprint(accident)
    except Exception as e:
        logger.warning("Файл не парсится: %s", e)
    
    try:
        print("\033[1;93m\nAccident full info (info_dtp) as raw json:\033[0m") 
        pprint(raw_json['results']['region_list'][0]['pok_list'][0]['result'][0]['dtpcardlist']['info_dtp'][0])
    except KeyError:
        logger.warning("Нарушена структура файла")

    print("\033[1;93m\nFull raw json info and structure:\033[0m") 
    print_structure(raw_json)

def print_structure(data, indent=0, max_depth=10):
    """Покажет структуру сырого json"""

    if indent > max_depth:
        print("  " * indent + "...")
        return
    
    if isinstance(data, dict):
        print("  " * indent + "{")
        for i, (k, v) in enumerate(list(data.items())[:5]):
            print(f"  " * (indent + 1) + f"{k}: ", end="")
            if isinstance(v, (dict, list)):
                print()
                print_structure(v, indent + 1, max_depth)
            else:
                print(repr(v)[:50])
        if len(data) > 5:
            print("  " * (indent + 1) + f"... и еще {len(data) - 5} элементов")
        print("  " * indent + "}")
    
    elif isinstance(data, list):
        print("  " * indent + "[")
        for i, item in enumerate(data[:3]):
            print(f"  " * (indent + 1), end="")
            print_structure(item, indent + 1, max_depth)
        if len(data) > 3:
            print("  " * (indent + 1) + f"... и еще {len(data) - 3} элементов")
        print("  " * indent + "]")
    
    else:
        print(repr(data)[:100])

def group_files_analysis():
    directory = 'data_msk'
    files = [x for x in os.listdir(directory) if x.endswith('json')]
    files.sort(key=lambda x: tuple(map(int, x.split('.')[0].split('_')[1].split('-'))))
    logger.debug("files: %s", files)
    for file in files:
        with open(directory + "/" + file, 'r', encoding='utf-8') as f:
            raw_json = json.load(f)
        try:
            data = Root.model_validate(raw_json)
            accidents = data.results.region_list[0].pok_list[0].result.dtpcardlist.info_dtp
        except Exception as e:
            logger.warning("Wrong file %s: %s", file, e )

        info_dtp_len = 0  
        try:
            for region in data.results.region_list:
                for pok in region.pok_list:
                    info_dtp_len += len(pok.result.dtpcardlist.info_dtp)
        except Exception as e:
            logger.warning("Wrong file structure %s: %s", file, e )
        logger.info("Файл %s имеет кол-во полей инфо: %s", file, info_dtp_len)

if __name__ == "__main__":
    # schema_investigation('data_msk/msk_2026-5.json')
    group_files_analysis()