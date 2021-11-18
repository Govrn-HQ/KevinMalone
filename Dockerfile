FROM python:3.9-slim-bullseye as base

WORKDIR /service
EXPOSE 80
EXPOSE 443

RUN pip install poetry
COPY . /service

RUN poetry install
CMD poetry run python ./bot
