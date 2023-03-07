# Devman Telegram Bot Lesson 1

This is study project for [lesson 1](https://dvmn.org/modules/chat-bots/lesson/devman-bot/)
This bot simply checks site's api and sends notification about checking you lessons

### Prerequisites

To start working with project you need to:

- Installed [Git](https://git-scm.com/)
- Installed [Docker Desktop](https://www.docker.com/)
- Get [token](https://dvmn.org/api/docs/) for devman website
- [Register](https://telegram.me/BotFather) bot in telegram and get token
- Send message to bot created on previous step
- [Find out](https://telegram.me/userinfobot) your telegram chat_id

### Installing

Clone project

```
git clone git@github.com:rkinwork/devman-bot.git
```

In project root folder create `.env` file and add variables

```
DVMN_BOT__TELEGRAM_CREDS=*telegram token*
DVMN_BOT__TOKEN=*token from dvmn.org site*
DVMN_BOT__CHAT_ID=*your chat id*
```

## Run service

To start bot working

```bash
make start
```

To stop bot working type in another console

```bash
make stop
```

### Settings

| Env variable or option name | Description                             |
|-----------------------------|-----------------------------------------|
| DVMN_BOT__DEBUG             | True or False to toggle debug mode      |
| DVMN_BOT__TOKEN             | token from DVMN.ORG website             |
| DVMN_BOT__TELEGRAM_CREDS    | token of telegram bot                   |
| DVMN_BOT__CHAT_ID           | telegram chat id of the user            |
| --start-ts                  | from which time start checking results  |
| --poll-timeout              | change requests timeout to DVMN.ORG API |

## Authors

* **DVMN.ORG TEAM** - *Idea*
* **Roman Kazakov** - *Implementation*

## License

MIT License

Copyright (c) 2023 Roman Kazakov

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
documentation files (the "Software"), to deal in the Software without restriction, including without limitation the
rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit
persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the
Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

