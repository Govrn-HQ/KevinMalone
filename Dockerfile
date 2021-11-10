FROM python:3.9-slim-bullseye as base

WORKDIR /service

RUN pip install poetry
COPY . /service

RUN poetry install
CMD poetry run python ./bot
