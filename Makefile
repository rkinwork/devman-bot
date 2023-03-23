build-image:
	docker build -f Dockerfile . -t pycharm-dvmn-bot

start:
	docker compose run --rm bot

stop:
	docker-compose kill -s SIGINT

run_server:
	export $(cat .env | xargs) && python src/main.py

