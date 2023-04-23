import logging
import time
from dataclasses import dataclass

import configargparse
import requests
import telegram

from telegram_handler import TelegramHandler

log = logging.getLogger(__name__)

DVMN_LONG_POLLING = 'https://dvmn.org/api/long_polling/'
DEFAULT_TIMEOUT = 180
SECONDS_TO_SLEEP = 10

IS_NEGATIVE_RES_MSG = (
    'Преподавателю всё понравилось, можно приступать к следующему уроку',
    'К сожалению в работе нашлись ошибки',
)
NOTIFICATION_TEMPLATE = """У вас проверили <a href="{lesson_url}">работу</a> «{lesson_title}»

{check_result_message}
"""


@dataclass
class CheckResult:
    submitted_at: str
    timestamp: str
    is_negative: str
    lesson_title: str
    lesson_url: str

    def as_message(self) -> str:
        message = NOTIFICATION_TEMPLATE.format(
            lesson_title=self.lesson_title,
            check_result_message=IS_NEGATIVE_RES_MSG[bool(self.is_negative)],
            lesson_url=self.lesson_url,
        )
        log.debug('result message: %s', message)
        return message


def send_message(
        message: str,
        bot: telegram.Bot,
        chat_id: str,
):
    while True:
        try:
            return bot.send_message(
                text=message,
                chat_id=chat_id,
                parse_mode=telegram.ParseMode.HTML,
                disable_web_page_preview=True,
            )
        except telegram.error.TelegramError as tel_err:
            log.error(msg=tel_err)
            log.debug('retrying after telegram connection problems')
            time.sleep(SECONDS_TO_SLEEP)
        except Exception as err:
            log.error(msg=err)
            raise


def parse_args():
    parser = configargparse.ArgParser()
    parser.add_argument(
        '--debug',
        help='debug mode',
        action='store_true',
        env_var='DVMN_BOT__DEBUG',
    )
    parser.add_argument(
        '--token',
        help='token from devman.org website',
        env_var='DVMN_BOT__TOKEN',
        required=True,
    )
    parser.add_argument(
        '--tlgrm-creds',
        help='telegram bot access token',
        env_var='DVMN_BOT__TELEGRAM_CREDS',
        required=True,
    )
    parser.add_argument(
        '--chat-id',
        help='telegram chat id of the user',
        env_var='DVMN_BOT__CHAT_ID',
        required=True,
    )
    parser.add_argument(
        '--start-ts',
        help='from what time we should check results on site',
    )
    parser.add_argument(
        '--poll-timeout',
        default=DEFAULT_TIMEOUT,
        help='timeout for DVMN long polling API response',
    )

    return parser.parse_args()


def main():
    options = parse_args()
    # fot study purposes admin and user are the same persons

    # prepare basic logger
    th = TelegramHandler(
        token=options.tlgrm_creds,
        admin_chat_id=options.chat_id,
    )
    th.setLevel(level=logging.INFO)

    # prepare specific loggers
    log.setLevel(logging.INFO)
    log.addHandler(hdlr=th)

    if options.debug:
        log.setLevel(logging.DEBUG)
        logging.basicConfig(level=logging.DEBUG)

    start_ts = options.start_ts
    bot = telegram.Bot(token=options.tlgrm_creds)
    log.info(msg='Bot started')
    while True:
        try:
            response = requests.get(
                url=DVMN_LONG_POLLING,
                params={
                    'timestamp': start_ts,
                },
                timeout=options.poll_timeout,
                headers={
                    'Authorization': 'Token {0}'.format(options.token),
                },
            )
        except requests.exceptions.ReadTimeout:
            log.debug('starting new attempt of long polling')
            continue
        except requests.exceptions.ConnectionError as err:
            log.error(msg=err)
            time.sleep(SECONDS_TO_SLEEP)
            log.debug('retrying after DVMN.ORG connection problems')
            continue
        except Exception as err:
            # should I catch here system exceptions?
            log.error(msg=err)
            time.sleep(SECONDS_TO_SLEEP)
            raise

        log.debug('api poll status code: %s', response.status_code)
        log.debug('api poll headers: %s', response.headers)
        log.debug('api poll text resp: %s', response.text)

        if not response.ok:
            continue

        try:
            lessons_checks = response.json()
        except requests.JSONDecodeError as json_err:
            log.error(msg=json_err)
            continue

        start_ts = lessons_checks.get('timestamp_to_request', start_ts)
        if lessons_checks.get('status') != 'found':
            continue

        start_ts = lessons_checks.get('last_attempt_timestamp', start_ts)
        for attempt in lessons_checks['new_attempts']:
            send_message(
                message=CheckResult(**attempt).as_message(),
                chat_id=options.chat_id,
                bot=bot,
            )


if __name__ == '__main__':
    main()
