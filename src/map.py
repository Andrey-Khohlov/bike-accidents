import json
import logging
import os
from pathlib import Path
import sys
import webbrowser

import folium
from folium.plugins import Fullscreen as FullscreenPlugin
import pydantic_core

from schemas import Root
from config import settings


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
    """Определяет что точка в границах прямоугольника reg"""
    if reg in ("msk", "cfo"):
        min_w, max_w = 49.6, 59.1
        min_l, max_l = 31.5, 47.6
    else:
        logger.warning("Регион задан не верно, %s", reg)
        raise
    return (min_w < coord_w < max_w ) and (min_l < coord_l < max_l)

def inject_template(template_file: str, m: folium.Element, replacements: dict = {}) -> None:
    f"""Чтение файла шаблона, опциональная замена подстановок и добавление сгенерированного элемента в объект folium.
        template_path - файла шаблон, 
        m - карта folium, 
        replacements - объекты подстановки: dict(placeholder: value).
    """
    logger.debug("Внедряем шаблон: %s", template_file)

    template_path = Path(f"templates/{template_file}")
    js_code = template_path.read_text(encoding="utf-8")

    if replacements:
        for placeholder, value in replacements.items():
            js_code = js_code.replace(placeholder, value)

    js_code = "{% raw %}" + js_code + "{% endraw %}"

    if 'body' in template_file:
        m.get_root().html.add_child(folium.Element(js_code))
    elif 'header' in template_file:
        m.get_root().header.add_child(folium.Element(js_code))
    else:
        logger.warning("Наименование файла %s должно содержать 'header' или 'body'", template_file)

    logger.debug("Шаблон внедрен: %s", template_file)

def main():
    logger.debug("'folium' in sys.modules: %s", 'folium' in sys.modules)
    
    points = []
    geojson_features = []
    corrupted_files = []
    directories = [
        'data_msk/', 
        'data_cfo/', 
        ]
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
                            accident.coord_w, accident.coord_l = accident.coord_l, accident.coord_w
                            logger.debug("coord_w < coord_l для reg: %s, point: %s, file: %s", region.reg_code, (accident.coord_w, accident.coord_l), file)
                        if not bbox(region_, accident.coord_w, accident.coord_l):
                            logger.debug("Точка %s за пределами области %s, file %s, empt_number: %s", (accident.coord_w, accident.coord_l), region.reg_code, file, accident.empt_number)
                            continue
                        points.append((accident.coord_w, accident.coord_l))
                        geojson_features.append({
                            "type": "Feature",
                            "geometry": {"type": "Point", "coordinates": [accident.coord_l, accident.coord_w]},
                            "properties": {
                                "file": file, 
                                "addr": ", ".join( [x for x in (accident.dor, accident.np, accident.street, accident.house) if x]), 
                                "coords": f"{accident.coord_l}, {accident.coord_w}",
                                "empt": accident.empt_number
                                }
                        })
    geojson_data = {"type": "FeatureCollection", "features": geojson_features}
    logger.info("Обнаружено %s точек ДТП.", f"{len(points):,d}")
    if corrupted_files:
        logger.info("Невалидные файлы:\n%s", "\n".join(sorted(corrupted_files)))

    center = (55.755790, 37.620038)
    m = folium.Map(
        location=center,
        tiles=f"https://tiles.api-maps.yandex.ru/v1/tiles/?projection=web_mercator&x={{x}}&y={{y}}&z={{z}}&lang=ru_RU&l=map&apikey={settings.YANDEX_API_KEY}",
        attr="Яндекс.Карты",
        zoom_start=10,
        max_zoom=18,
    )

    folium.GeoJson(
        geojson_data,
        marker=folium.CircleMarker(radius=2, color='red', fill=False),
        popup=folium.GeoJsonPopup(fields=['addr'], labels=False)
    ).add_to(m)

    FullscreenPlugin().add_to(m)

    for file in sorted(os.listdir('templates')):
        if file.endswith('.js') or file.endswith('.html'):
            d = dict()
            if file == 'claim-uploader-body.html':
                d = {f'[[APP_SCRIPT_URL]]': settings.APP_SCRIPT_URL}
            inject_template(file, m,  d)
    
    output_file = '/home/xgb/projects/rollermap/bike-hitting/index.html'
    m.save(output_file)
    logger.info("Карта сохранена: %s", output_file)
    attribution_removed = remove_attribution_line(output_file, target="attribution")  # удаляет подписи фреймворков с карты
    logger.debug("Постобработка attribution для %s: %s", output_file, attribution_removed)
    webbrowser.open(output_file)
    

if __name__ == "__main__":
    main()