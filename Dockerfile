FROM ubuntu:18.04

run apt update && \
    apt install -y python3-pip python3-dev && \
    apt -y install ffmpeg

COPY ./requirements.txt /app/requirements.txt

WORKDIR /app

RUN pip3 install -r requirements.txt

COPY . /app

ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

ENTRYPOINT celery -A tasks worker --loglevel=info