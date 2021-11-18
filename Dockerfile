FROM python:3.9-slim-bullseye as base

WORKDIR /service

RUN pip install poetry
COPY . /service

CMD poetry install && poetry run python ./bot
