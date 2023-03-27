import os
import logging
import requests
import exceptions
import time
import telegram
from http import HTTPStatus
from constants import (
    PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID,
    ENDPOINT, HEADERS, HOMEWORK_VERDICTS, RETRY_PERIOD
)


def check_tokens():
    """Функция проверки доступности переменных окружения."""
    my_tokens = {
        'practicum_token': PRACTICUM_TOKEN,
        'telegram_token': TELEGRAM_TOKEN,
        'telegram_chat_id': TELEGRAM_CHAT_ID,
    }
    for token_key, token_value in my_tokens.items():
        if token_value is None:
            logging.critical(
                'Отсутствует токен: {}'.format(token_key)
            )
            return False
    return True


def send_message(bot, message):
    """Функция отправки сообщения."""
    try:
        logging.info(
            'Сообщение "{}" отправляется'.format(message)
        )
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(
            'Сообщение "{}" успешно отправленно'.format(message)
        )
    except Exception as error:
        logging.error(
            'Сообщение не отправленно. Ошибка: {}'.format(error)
        )


def get_api_answer(timestamp):
    """Функция запроса к API Яндекс.Практикум."""
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp}
        )
        response_json = response.json()
        if response.status_code == HTTPStatus.OK:
            logging.info('Ответ от Яндекс.Практикум: {}'.format(
                response.status_code))
            return response_json
        else:
            raise exceptions.InvalidHttpStatus(
                'Ошибка ответа от Яндекс.Практикум: ',
                'Код: {}'.format(response_json.get("code")),
                'Сообщение: {}'.format(response_json.get("message"))
            )
    except requests.exceptions.RequestException as error:
        raise exceptions.RequestError(
            'ошибка при запросе к Яндекс.Практикум: {}.'.format(error)
        )


def check_response(response):
    """Функция проверки ответа API на соответствие документации."""
    if not isinstance(response, dict):
        raise TypeError(
            'Ответ "{}" не является словарем.'.format(response)
        )
    else:
        try:
            timestamp = response['current_date']
        except KeyError:
            logging.error('Ключ "current_date" отсутствует в ответе')
        try:
            homeworks = response['homeworks']
        except KeyError:
            logging.error('Ключ "homeworks" отсутствует в ответе'
                          )
        if not (isinstance(timestamp, int) and isinstance(homeworks, list)):
            raise TypeError
        return homeworks


def parse_status(homework):
    """Функция, проверяющая статус домашнего задания."""
    try:
        homework_name = homework['homework_name']
    except KeyError:
        logging.error('Отсутствует ключ "homework_name"')
    try:
        homework_status = homework.get('status')
    except KeyError:
        logging.error('Отсутствует ключ "status"')
    if homework_status in HOMEWORK_VERDICTS:
        return (
            'Изменился статус проверки работы "{}" '.format(homework_name)
            + 'Новый статус проверки домашней работы "{}": {}'.format(
                homework_name, HOMEWORK_VERDICTS.get(homework_status))
        )
    else:
        raise exceptions.StatusOfTheHomeworkIsUnknown


def main():
    """Основная логика работы программы."""
    if not check_tokens():
        exit()
    else:
        last_homework = ''
        bot = telegram.Bot(token=TELEGRAM_TOKEN)
        timestamp = 0
        while True:
            try:
                response = get_api_answer(timestamp)
                homeworks = check_response(response)
                if len(homeworks) > 0:
                    message = parse_status(homeworks[0])
                    if last_homework != message:
                        send_message(bot, message)
                        last_homework = message
                timestamp = int(time.time())
                time.sleep(RETRY_PERIOD)

            except Exception as error:
                message = f'Сбой в работе программы: {error}'
                send_message(bot, message)
                logging.error(message)
            finally:
                time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        filename=os.path.join(os.path.dirname(__file__), 'main.log'),
        format='%(asctime)s, %(levelname)s, %(message)s, %(name)s'
    )
    main()
