from contextlib import suppress
from logging import StreamHandler, LogRecord

import telegram


class TelegramHandler(StreamHandler):

    def __init__(
            self,
            token: str,
            admin_chat_id: str,
            *args,
            **kwargs,
    ):
        self._bot = telegram.Bot(token=token)
        self._bot.get_me()
        self._chat_id = admin_chat_id
        super().__init__(*args, **kwargs)

    def emit(self, record: LogRecord) -> None:
        with suppress(telegram.error.TimedOut):
            self._bot.send_message(
                chat_id=self._chat_id,
                text=self.format(record=record),
                disable_web_page_preview=True,
            )
