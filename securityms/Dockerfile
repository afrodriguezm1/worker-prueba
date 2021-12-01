FROM python:3.7-alpine

RUN apk add --no-cache gcc musl-dev linux-headers\
    && pip install --upgrade pip

RUN apk add build-base

WORKDIR /app

ENV FLASK_APP=app.py

ENV FLASK_RUN_HOST=0.0.0.0

COPY requirements.txt requirements.txt

COPY . .

RUN pip --no-cache-dir install -r requirements.txt

EXPOSE 5000

#Production
ENTRYPOINT ["./gunicorn.sh"]

#Development
#CMD ["flask", "run"]