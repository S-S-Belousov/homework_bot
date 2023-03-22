import os
import logging
import requests
import exceptions
import time
from dotenv import load_dotenv
from http import HTTPStatus
from telegram import Bot

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    level=logging.INFO,
    filename=os.path.join(os.path.dirname(__file__), 'main.log'),
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s'
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
            return (False)
    return (True)


def send_message(bot, message):
    """Функция отправки сообщения."""
    try:
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
    try:
        timestamp = response['current_date']
    except KeyError:
        logging.error('Ключ "current_date" отсутствует в ответе')
    try:
        homeworks = response['homeworks']
    except KeyError:
        logging.error('Ключ "homeworks" отсутствует в ответе'
                      )
    if isinstance(timestamp, int) and isinstance(homeworks, list):
        return homeworks
    else:
        raise TypeError


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
            'Изменился статус проверки работы "{}" '.format(homework_name) +
            'Новый статус проверки домашней работы "{}": {}'.format(
            homework_name, HOMEWORK_VERDICTS.get(homework_status))
        )
    else:
        raise exceptions.StatusOfTheHomeworkIsUnknown


def main():
    """Основная логика работы бота."""
    if check_tokens():
        bot = Bot(token=TELEGRAM_TOKEN)
        timestamp = 0
        while True:
            try:
                response = get_api_answer(timestamp)
                homeworks = check_response(response)
                if len(homeworks) > 0:
                    message = parse_status(homeworks[0])
                    send_message(bot, message)
                timestamp = int(time.time())
                time.sleep(RETRY_PERIOD)

            except Exception as error:
                message = f'Сбой в работе программы: {error}'
                send_message(bot, message)
                logging.error(message)
                time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
