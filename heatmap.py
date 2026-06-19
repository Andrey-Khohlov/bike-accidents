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

def remove_attribution_line(file_path: str | Path, target: str = "attribution", encoding: str = "utf-8") -> bool:
    """
    Удаляет строки, содержащие target, из файла.
    Добавляет "attributionControl": false после строки с "preferCanvas": false,.
    """
    path = Path(file_path)
    if not path.is_file():
        logger.warning("Файл не найден: %s", path)
        return False
    try:
        lines = path.read_text(encoding=encoding).splitlines(keepends=True)
    except OSError as e:
        logger.warning("Ошибка при чтении файла: %s", e)
        return False
    new_lines = [line for line in lines if target not in line]
    if len(new_lines) == len(lines):
        logger.warning("Строка с attribution не найдена. Файл не изменён.")
    out: list[str] = []
    prefer_found = False
    for line in new_lines:
        out.append(line)
        if "preferCanvas" in line:
            out.append('  "attributionControl": false, \n')
            prefer_found = True
    if not prefer_found:
        logger.warning('Строка с preferCanvas не найдена. "attributionControl": false не добавлен.')
    try:
        path.write_text("".join(out), encoding=encoding)
        return True
    except OSError as e:
        logger.warning("Ошибка при записи файла: %s", e)
        return False
def bbox(reg, coord_w, coord_l):
    """Определяет сто точка в границах прямоугольника reg"""
    if reg in ("msk", "cfo"):
        min_w, max_w = 49.6, 59.1
        min_l, max_l = 31.5, 47.6
    else:
        logger.warning("Регион задан не верно, %s", reg)
        raise
    return (min_w < coord_w < max_w ) and (min_l < coord_l < max_l)
        
def main():
    logger.debug("'folium' in sys.modules: %s", 'folium' in sys.modules)
    
    points = []
    corrupted_files = []
    directories = ['data_msk/', 'data_cfo/']
    for directory in directories:
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
                        region_ = file.split("_")[0] 
                        if region_ in ("msk", "cfo") and accident.coord_w < accident.coord_l:
                            if not bbox(region_, accident.coord_l, accident.coord_w):
                                logger.debug("Точка %s за пределами области %s, file %s", (accident.coord_l, accident.coord_w), region.reg_code, file)
                                continue
                            logger.debug("coord_w < coord_l для reg: %s, point: %s, file: %s", region.reg_code, (accident.coord_w, accident.coord_l), file)
                            points.append((accident.coord_l, accident.coord_w))
                        else:
                            if not bbox(region_, accident.coord_w, accident.coord_l):
                                logger.debug("Точка %s за пределами области %s, file %s", (accident.coord_w, accident.coord_l), region.reg_code, file)
                                continue
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

    for file in sorted(os.listdir('templates')):
        if file.endswith('.js') or file.endswith('.html'):
            template_path = Path(f"templates/{file}")
            js_code = template_path.read_text(encoding="utf-8")
            if 'body' in file:
                m.get_root().html.add_child(folium.Element(js_code))
            elif 'header' in file:
                m.get_root().header.add_child(folium.Element(js_code))
            else:
                logger.warning("Наименование файла %s должно содержать 'header' или 'body'", file)
    
    output_file = '/home/xgb/projects/rollermap/bike-hitting/index.html'
    m.save(output_file)
    logger.info("Карта сохранена: %s", output_file)
    attribution_removed = remove_attribution_line(output_file, target="attribution")  # удаляет подписи фреймворков с карты
    logger.debug("Постобработка attribution для %s: %s", output_file, attribution_removed)
    webbrowser.open(output_file)
    

if __name__ == "__main__":
    main()