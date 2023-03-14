import logging
import time
from dataclasses import dataclass
from functools import partial
from typing import NewType, Tuple

import configargparse
import requests
import telegram
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

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
        # Need to be saved in persistent storage. Not a scope of this project
        self._start_ts = start_ts
        self._token = token
        self._poll_timeout = poll_timeout or timeout_seconds(DEFAULT_TIMEOUT)
        self._session = None

    def __call__(self, *args, **kwargs) -> Tuple[CheckResult]:
        return self._poll()

    @property
    def session(self):
        if self._session is None:
            retry_strategy = Retry(
                total=3,
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=(
                    'GET',
                ),
            )
            adapter = HTTPAdapter(max_retries=retry_strategy)
            http = requests.Session()
            http.headers.update({
                'Authorization': 'Token {0}'.format(self._token),
            })
            http.mount('https://', adapter)
            self._session = http
        return self._session

    def _poll(self) -> [Tuple[CheckResult]]:
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
            polling_result = self.session.get(
                url=DVMN_LONG_POLLING,
                params=polling_params,
                timeout=self._poll_timeout,
            )
        except requests.exceptions.ConnectionError as err:
            log.warning('%s', str(err))
            log.debug('retrying after DVMN.ORG connection problems')
            time.sleep(DEFAULT_TIMEOUT)
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


class TelegramNotificator:
    def __init__(
            self,
            token: str,
            chat_id: str,
    ):
        self._send_message = partial(
            telegram.Bot(token=token).send_message,
            chat_id=chat_id,
            parse_mode=telegram.ParseMode.HTML,
            disable_web_page_preview=True,
        )

    def __call__(self, message: str):
        return self._call(message=message)

    def _call(self, message: str):
        while True:
            try:
                return self._send_message(text=message)
            except telegram.error.TelegramError as tel_err:
                log.warning('%s', str(tel_err))
                log.debug('retrying after telegram connection problems')
                time.sleep(DEFAULT_TIMEOUT)


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
    send_message = TelegramNotificator(
        chat_id=options.chat_id,
        token=options.tlgrm_creds,
    )
    while True:
        res = api_poller()
        if res is None:
            continue
        for check in res:
            send_message(message=check.as_message())


if __name__ == '__main__':
    main()
