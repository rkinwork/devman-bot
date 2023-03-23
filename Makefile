build-image:
	docker build -f Dockerfile . -t pycharm-dvmn-bot

start:
	docker compose run --rm bot

stop:
	docker-compose kill -s SIGINT



