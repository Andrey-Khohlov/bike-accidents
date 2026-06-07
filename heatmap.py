import json
import logging
from pathlib import Path
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


def schema_investigation():
    with open('data/data.json', 'r', encoding='utf-8') as f:
        raw_json = json.load(f)

    data = Root.model_validate(raw_json)
    pprint(Root.model_json_schema())
    accident = data.results.region_list[0].pok_list[0].result.dtpcardlist.info_dtp[3]
    print("accident data:", accident.coord_l, accident.coord_w)
    for accident_ts in accident.ts_info:
        pprint(accident_ts.model_dump())
    pprint(accident)
     
    pprint(data['results']['region_list'][0]['pok_list'][0]['result'][0]['dtpcardlist']['info_dtp'][0])
    print_structure(raw_json)

def print_structure(data, indent=0, max_depth=10):
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
    

    with open('data/data.json', 'r', encoding='utf-8') as f:
        raw_json = json.load(f)

    data = Root.model_validate(raw_json)  # Парсим в Pydantic-модель
    # dtp_list = data.results.region_list[0].pok_list[0].result.dtpcardlist.info_dtp
    points = []
    for region in data.results.region_list:
        for pok in region.pok_list:
            for accident in pok.result.dtpcardlist.info_dtp:
                points.append((accident.coord_w, accident.coord_l))
    
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
        radius=3,
        blur=1,
    ).add_to(m)
    output_file ='index.html'
    # TODO attribution_removed = remove_attribution_line(out_path, target="attribution")  # удаляет подписи фреймворков с карты
    out_path = Path(output_file)
    m.save(str(out_path))
    logger.info("Карта сохранена: %s", out_path)
    

if __name__ == "__main__":
    # schema_investigation()
    main()