up:
	docker compose up --build

test:
	python -m pytest tests -q

lint:
	python -m compileall src

down:
	docker compose down -v

