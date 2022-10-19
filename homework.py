import logging
import os
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter(
    '%(asctime)s, %(levelname)s, %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logger.addHandler(handler)
before_message = ''


def send_message(bot, message):
    """Отправка сообщения в чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info('Успешная отправка сообщения.')
    except Exception as error:
        raise SystemError(f'Не отправляются сообщения, {error}')


def get_api_answer(current_timestamp):
    """Запрашиваем ответ от API."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        homework_statuses = requests.get(ENDPOINT,
                                         headers=HEADERS,
                                         params=params)
    except Exception as error:
        raise SystemError(f'Ошибка получения request, {error}')
    else:
        if homework_statuses.status_code == HTTPStatus.OK:
            logger.info('успешное получение Эндпоинта')
            homework = homework_statuses.json()
            if 'error' in homework:
                raise SystemError(f'Ошибка json, {homework["error"]}')
            elif 'code' in homework:
                raise SystemError(f'Ошибка json, {homework["code"]}')
            else:
                return homework
        elif homework_statuses.status_code == HTTPStatus.REQUEST_TIMEOUT:
            raise SystemError(f'Ошибка код {homework_statuses.status_code}')
        elif homework_statuses.status_code == HTTPStatus.INTERNAL_SERVER_ERROR:
            raise SystemError(f'Ошибка код {homework_statuses.status_code}')
        else:
            raise SystemError(
                f'Недоступен Эндпоинт, код {homework_statuses.status_code}')


def check_response(response):
    """
    Провряем ответ на корректность.
    Если ключ [homeworks] не найден,
    то всё перехватится в main().
    """
    if type(response) == dict:
        response['current_date']
        homeworks = response['homeworks']
        if type(homeworks) == list:
            return homeworks
        else:
            raise SystemError('Тип homeworks не list')
    else:
        raise TypeError('Ответ от API не словарь')


def parse_status(homework):
    """Парсим информацию о домашке."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')

    if homework_name is not None and homework_status is not None:
        if homework_status in HOMEWORK_STATUSES:
            verdict = HOMEWORK_STATUSES.get(homework_status)
            return ('Изменился статус проверки '
                    + f'работы "{homework_name}". {verdict}')
        else:
            raise SystemError('Hеизвестный статус')
    else:
        raise KeyError('Hет нужных ключей в словаре')


def check_tokens():
    """Проверка доступности необходимых токенов."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        logger.critical('Ошибка импорта токенов Telegramm.')
        return False
    elif not PRACTICUM_TOKEN:
        raise SystemError('Ошибка импорта токенов Домашки.')
    else:
        return True


def main():
    """Основная логика работы."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time()) - RETRY_TIME
    if not check_tokens():
        raise SystemExit('Ошибка токенов.')
    global before_message

    while True:
        try:
            if type(current_timestamp) is not int:
                raise SystemError('Передана не дата.')
            response = get_api_answer(current_timestamp)
            response = check_response(response)

            if len(response) > 0:
                homework_status = parse_status(response[0])
                if homework_status is not None:
                    send_message(bot, homework_status)
            else:
                logger.debug('Новые статусы отсутсвуют.')

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            if message != before_message:
                bot.send_message(TELEGRAM_CHAT_ID, message)
                before_message = message
        finally:
            current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
