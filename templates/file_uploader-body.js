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