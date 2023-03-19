import logging
import time
from dataclasses import dataclass
from typing import NewType, Tuple

import configargparse
import requests
import telegram

ts = NewType('ts', str)
timeout_seconds = NewType('timeout', int)
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


class ApiPoller:
    def __init__(
            self,
            token,
            start_ts: ts = None,
            poll_timeout: timeout_seconds = None,
    ):
        self._start_ts = start_ts
        self._token = token
        self._poll_timeout = poll_timeout or timeout_seconds(DEFAULT_TIMEOUT)
        self._session = None

    def poll(self) -> [Tuple[CheckResult]]:
        polling_params = {
            'timestamp': self._start_ts,
        }
        log.debug(
            'making request with params: %s, to: %s with timout: %s',
            polling_params,
            DVMN_LONG_POLLING,
            self._poll_timeout,
        )
        try:
            polling_result = requests.get(
                url=DVMN_LONG_POLLING,
                params=polling_params,
                timeout=self._poll_timeout,
                headers={
                    'Authorization': 'Token {0}'.format(self._token),
                },
            )
        except (
                requests.exceptions.ConnectionError,
                requests.exceptions.ReadTimeout,
        ) as err:
            log.warning('%s', str(err))
            log.debug('retrying after DVMN.ORG connection problems')
            time.sleep(SECONDS_TO_SLEEP)
            return None
        log.debug('api poll status code: %s', polling_result.status_code)
        log.debug('api poll headers: %s', polling_result.headers)
        log.debug('api poll text resp: %s', polling_result.text)

        if not polling_result.ok:
            return None
        response = polling_result.json()

        if response.get('status') != 'found':
            self._start_ts = response.get(
                'timestamp_to_request',
                self._start_ts,
            )
            return None

        last_attempt_timestamp = response.get('last_attempt_timestamp')
        if last_attempt_timestamp is None:
            log.debug(
                'There is no anticipated field in response: %s',
                response,
            )
            return None

        self._start_ts = last_attempt_timestamp
        return tuple((
            CheckResult(**attempt) for attempt in response['new_attempts']
        ))


def send_message(
        message: str,
        token: str,
        chat_id: str,
):
    bot = telegram.Bot(token=token)
    while True:
        try:
            return bot.send_message(
                text=message,
                chat_id=chat_id,
                parse_mode=telegram.ParseMode.HTML,
                disable_web_page_preview=True,
            )
        except telegram.error.TelegramError as tel_err:
            log.warning('%s', str(tel_err))
            log.debug('retrying after telegram connection problems')
            time.sleep(SECONDS_TO_SLEEP)


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
        help='timeout for DVMN long polling API response',
    )

    return parser.parse_args()


def main():
    options = parse_args()
    if options.debug:
        logging.basicConfig(level=logging.DEBUG)
    log.debug(options)
    api_poller = ApiPoller(
        token=options.token,
        start_ts=ts(options.start_ts),
        poll_timeout=timeout_seconds(options.poll_timeout),
    )
    while True:
        check_results = api_poller.poll()
        if check_results is None:
            continue
        for check in check_results:
            send_message(
                message=check.as_message(),
                chat_id=options.chat_id,
                token=options.token,
            )


if __name__ == '__main__':
    main()
