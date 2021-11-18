FROM python:3.9-slim-bullseye as base

WORKDIR /service
EXPOSE 80
EXPOSE 443

RUN pip install poetry
COPY . /service

CMD poetry install && poetry run python ./bot
