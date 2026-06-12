import json
import logging
import os
from pathlib import Path
import sys
import webbrowser

import folium
from folium.plugins import HeatMap
import pydantic_core

from schemas import Root


logging.basicConfig(level = logging.DEBUG,
                    format= "[%(levelname)s] [%(name)s] %(message)s",
                    handlers=[logging.StreamHandler(sys.stderr)]
                    )                    
logger = logging.getLogger(__name__)


def main():
    logger.debug("'folium' in sys.modules: %s", 'folium' in sys.modules)
    
    points = []
    corrupted_files = []
    directory = 'data_msk/'
    files = os.listdir(directory)
    for file in files:
        if file.split('.')[-1] != 'json':
            logger.info("В директории данных %s найден не json файл %s", directory, file)
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
    if corrupted_files:
        logger.info("Невалидные файлы:\n%s", "\n".join(sorted(corrupted_files)))

    center = (sum(p[0] for p in points) / len(points), sum(p[1] for p in points) / len(points))
    m = folium.Map(
        location=center,
        tiles="CartoDB Voyager",
        zoom_start=11,
        max_zoom=18,
    )
    HeatMap(
        points,
        min_opacity = 0.5,
        max_zoom=10,
        radius=7,
        blur=1,
    ).add_to(m)

    template_path = Path("templates/file_uploader.js")
    js_code = template_path.read_text(encoding="utf-8")
    m.get_root().html.add_child(folium.Element(js_code))

    # TODO attribution_removed = remove_attribution_line(out_path, target="attribution")  # удаляет подписи фреймворков с карты

    output_file = '/home/xgb/projects/rollermap/bike-collisions/index.html'
    m.save(output_file)
    logger.info("Карта сохранена: %s", output_file)
    webbrowser.open(output_file)
    

if __name__ == "__main__":
    main()