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
    except pydantic_core._pydantic_core.ValidationError:
        logger.warning("Файл не парсится.")
    
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


def main():
    # Это наш будущий скрипт для загрузчика GPX
    file_uploader_js = """
        <script>
    (function() {
        // Функция, которая будет выполнена после загрузки карты
        function initGPXUploader() {
            // 1. Находим объект карты Leaflet среди глобальных переменных
            var map = null;
            for (var key in window) {
                if (window[key] && window[key] instanceof L.Map) {
                    map = window[key];
                    break;
                }
            }
            if (!map) {
                // Если карта ещё не создана – пробуем снова через 200 мс
                console.log("Карта не найдена, повтор через 200ms");
                setTimeout(initGPXUploader, 200);
                return;
            }
            console.log("Карта найдена, добавляем контрол загрузки GPX");

            // 2. Создаём контрол с кнопкой выбора файла
            var controlPanel = L.control({position: 'topright'});
            controlPanel.onAdd = function(map) {
                var div = L.DomUtil.create('div', 'info legend');
                div.innerHTML = '<input type="file" id="gpxFileInput" accept=".gpx" style="padding: 8px; background: white; border: 2px solid #ccc; border-radius: 5px;">';
                div.style.backgroundColor = 'white';
                div.style.padding = '8px';
                div.style.borderRadius = '5px';
                div.style.boxShadow = '0 0 15px rgba(0,0,0,0.2)';
                return div;
            };
            controlPanel.addTo(map);

            // 3. Функция парсинга GPX
            function parseGPX(xmlString) {
                var parser = new DOMParser();
                var xmlDoc = parser.parseFromString(xmlString, "text/xml");
                var points = [];
                var trkpts = xmlDoc.getElementsByTagName("trkpt");
                for (var i = 0; i < trkpts.length; i++) {
                    var lat = parseFloat(trkpts[i].getAttribute("lat"));
                    var lon = parseFloat(trkpts[i].getAttribute("lon"));
                    points.push([lat, lon]);
                }
                return points;
            }

            // 4. Обработчик загрузки файла (используем делегирование или ждём появления элемента)
            // Элемент input появится динамически, поэтому вешаем обработчик на document
            document.addEventListener('change', function(e) {
                if (e.target && e.target.id === 'gpxFileInput') {
                    var file = e.target.files[0];
                    if (!file) return;

                    var reader = new FileReader();
                    reader.onload = function(evt) {
                        var gpxContent = evt.target.result;
                        var coordinates = parseGPX(gpxContent);
                        if (coordinates.length === 0) {
                            alert("Не найдено точек trkpt в GPX файле");
                            return;
                        }
                        var polyline = L.polyline(coordinates, {color: 'red', weight: 4}).addTo(map);
                        map.fitBounds(polyline.getBounds());
                        console.log("GPX загружен, точек: " + coordinates.length);
                    };
                    reader.readAsText(file);
                }
            });
        }

        // Запускаем процесс поиска карты после загрузки DOM
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', initGPXUploader);
        } else {
            initGPXUploader();
        }
    })();
    </script>
    """

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
        max_zoom=18,
        radius=10,
        blur=10,
    ).add_to(m)
    # Внедряем JS-код в нашу карту
    m.get_root().html.add_child(folium.Element(file_uploader_js))


    output_file ='index.html'
    # TODO attribution_removed = remove_attribution_line(out_path, target="attribution")  # удаляет подписи фреймворков с карты
    out_path = Path(output_file)
    m.save(str(out_path))
    m.save('/home/xgb/projects/rollermap/bike-collisions/index.html')
    logger.info("Карта сохранена: %s", out_path)
    webbrowser.open(output_file)
    

if __name__ == "__main__":
    # schema_investigation('data_msk/msk_2021-10.json')
    main()