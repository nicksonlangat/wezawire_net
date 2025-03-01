celery:
	celery -A mysite worker --loglevel=info -E
beat:
	celery -A mysite beat --loglevel=info
run:
	python manage.py runserver 8001
redis:
	redis-server
migrate:
	python manage.py makemigrations && python manage.py migrate
install:
	pip install -r requirements.txt
static:
	python manage.py collectstatic
pull:
	git pull origin main
deploy:
	sudo systemctl restart codetail && sudo systemctl restart nginx
cm:
	git add . && git commit -m "bug fixes, feature and feedback updates"
