class InvalidHttpStatus(Exception):
    """Ошибка ответа от API Яндекс.Практикум."""
    pass


class StatusOfTheHomeworkIsUnknown(Exception):
    """Статус домашнего задания неизвестен."""
    pass


class StatusKeyMissingInTheResponse(Exception):
    """Ключ 'status' отсутствует в ответе."""
    pass
