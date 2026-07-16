from requests.exceptions import RequestException


class DateRangeError(ValueError):
    """Исключение, выбрасываемое при некорректном диапазоне дат (конечная дата раньше начальной)."""
    pass

class ParseError(RequestException):
    """Исключение, выбрасываемое при ошибах парсинга 400/500/requests.exceptions.RequestException комбинированных данных, объединяющих несколько pok или reg."""
    pass