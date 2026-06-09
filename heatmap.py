import json
import logging
import os
from pathlib import Path
from pprint import pprint
import sys
import webbrowser

import folium
from folium.plugins import HeatMap
import pydantic_core
import requests

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

    data = Root.model_validate(raw_json)
    # pprint(Root.model_json_schema())
    accident = data.results.region_list[0].pok_list[0].result.dtpcardlist.info_dtp[0]
    

    print("\033[1;93mAccident coords:\033[0m", accident.coord_l, accident.coord_w)

    print("\033[1;93m\nAccident vehicals (ts) data:\033[0m") 
    for accident_ts in accident.ts_info:
        pprint(accident_ts.model_dump())

    print("\033[1;93m\nAccident full info (info_dtp) as Pydantic schema:\033[0m") 
    pprint(accident)
    
    print("\033[1;93m\nAccident full info (info_dtp) as raw json:\033[0m") 
    pprint(raw_json['results']['region_list'][0]['pok_list'][0]['result'][0]['dtpcardlist']['info_dtp'][0])

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


def main():
    logger.debug("'folium' in sys.modules: %s", 'folium' in sys.modules)
    
    points = []
    corrupted_files = []
    directory = 'data_msk/'
    files = os.listdir(directory)
    for file in files:
        if file.split('.')[-1] != 'json':
            logger.info("В директории данных %s найден посторонний файл %s", directory, file)
            continue
        with open(f'{directory}/{file}', 'r', encoding='utf-8') as f:
            raw_json = json.load(f)
        try:
            data = Root.model_validate(raw_json)  # Парсим в Pydantic-модель
        except pydantic_core._pydantic_core.ValidationError as e:
            corrupted_files.append(file)
            logger.debug("Corrupted file %s, %s", file, e)
        # dtp_list = data.results.region_list[0].pok_list[0].result.dtpcardlist.info_dtp
        for region in data.results.region_list:
            for pok in region.pok_list:
                for accident in pok.result.dtpcardlist.info_dtp:
                    points.append((accident.coord_w, accident.coord_l))
    logger.info("Обнаружено %s точек ДТП.", f"{len(points):,d}")
    logger.info("Невалидные файлы: %s \n", "\n".join(sorted(corrupted_files)))
    center = (sum(p[0] for p in points) / len(points), sum(p[1] for p in points) / len(points))
    m = folium.Map(
        location=center,
        tiles="CartoDB Voyager",
        zoom_start=11,
        max_zoom=18,
    )
    HeatMap(
        points,
        max_zoom=18,
        radius=10,
        blur=10,
    ).add_to(m)
    output_file ='index.html'
    # TODO attribution_removed = remove_attribution_line(out_path, target="attribution")  # удаляет подписи фреймворков с карты
    out_path = Path(output_file)
    m.save(str(out_path))
    logger.info("Карта сохранена: %s", out_path)
    webbrowser.open(output_file)
    

if __name__ == "__main__":
    # schema_investigation('data_msk/msk_2015-1.json')
    main()