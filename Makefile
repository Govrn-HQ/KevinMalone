PROJECT_NAME=govrn
REGISTRY_NAME=$(shell grep REGISTRY_NAME .env | cut -d "=" -f2)
IMAGE_PATH = /guild/govrn
TAG = latest

# Make sure poetry virtual env is active
local:
	poetry run python ./bot

test:
	pytest .

lint:
	flake8 .

format:
	black .

format_check:
	black . --check

azure_login:
	az acr login --name $(REGISTRY_NAME)

build:
	docker build -t $(PROJECT_NAME):$(TAG)  . 

run:
	docker run -e API_TOKEN=$(API_TOKEN) \
			   -e SUGGESTION_CHANNEL=$(SUGGESTION_CHANNEL) \
			   -e CLIENT_ID=$(CLIENT_ID) \
			   -e GUILD_ID=$(GUILD_ID) \
			   $(PROJECT_NAME):$(TAG) $(cmd)

# Go into the container
inspect:
	docker run -it /bin/bash

generate_oauth:
	$(MAKE) run CLIENT_ID=$(CLIENT_ID) \
		        GUILD_ID=$(GUILD_ID) \
				cmd="poetry run python ./scripts/generate_oauth.py"
publish:
	$(MAKE) build PROJECT_NAME=$(REGISTRY_NAME)$(IMAGE_PATH) TAG=$(TAG)
	docker push $(REGISTRY_NAME)$(IMAGE_PATH):$(TAG)
