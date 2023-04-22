import logging
from logging import StreamHandler, LogRecord

import telegram

log = logging.getLogger('telegram_handler')


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
        msg = self.format(record=record)
        try:
            self._bot.send_message(
                chat_id=self._chat_id,
                text=msg,
                disable_web_page_preview=True,
            )
        except telegram.error.TimedOut:
            pass
