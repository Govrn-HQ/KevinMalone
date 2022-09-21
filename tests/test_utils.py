from datetime import timedelta, time, datetime
import pytest
from pytest_mock.plugin import MockerFixture
import discord

from bot.common.cache import Cache
from bot.common.tasks.tasks import Cadence


# Add in memory implementation
class MockCache(Cache):
    def __init__(self):
        self.internal = {}

    async def get(self, key):
        return self.internal.get(key)

    async def set(self, key, value):
        self.internal[key] = value

    async def delete(self, key):
        if self.internal.get(key):
            del self.internal[key]


# This is a continual cadence; it's always running
class MockCadence(Cadence):
    def __init__(self, time_to_run: time):
        self.time_to_run = time_to_run

    def get_timedelta_until_run(self, from_dt: datetime) -> timedelta:
        return timedelta(seconds=-1)

    def get_timedelta_until_next_occurrence(self, from_dt: datetime) -> timedelta:
        return timedelta(seconds=1)

    def get_next_runtime(self) -> datetime:
        return datetime.now() - timedelta(seconds=1)

    def set_time_to_run(self, time_to_run):
        self.time_to_run = time_to_run


class MockChannel:
    def __init__(self):
        pass

    async def send(self, content: str = None, embed: discord.Embed = None):
        mock_message = MockMessage()
        mock_message.channel = self
        mock_message.content = content
        return mock_message


class MockMessage:
    def __init__(self):
        self.reactions = []
        self.content = None
        self.channel: MockChannel = MockChannel()

    async def add_reaction(self, reaction: str):
        self.reactions.append(reaction)


class MockContext:
    def __init__(self):
        self.interaction: MockInteraction = MockInteraction()
        self.response: MockResponse = MockResponse()


class MockInteraction:
    def __init__(self):
        self.followup: MockResponse = MockResponse()


class MockResponse:
    def __init__(self):
        self.sent_content: str = None
        self.embed: discord.Embed = None
        self.ephemeral: bool = False
        self.file: discord.file = None

    async def send_message(
        self,
        content: str = None,
        embed: discord.Embed = None,
        ephemeral: bool = False,
        file: discord.file = None,
    ):
        self.sent_content = content
        self.ephemeral = ephemeral
        self.embed = embed
        self.file = file


def mock_bot_method(mocker: MockerFixture, method: str, returns=None):
    ret_value = None
    if returns is None:
        ret_value = get_default_return_for_bot_method(method)
    mocker.patch(f"{method}", return_value=ret_value)


def get_default_return_for_bot_method(method: str):
    pass


def mock_gql_query(mocker: MockerFixture, method: str, returns=None):
    # TODO add type assertion for returns and method
    mocker.patch(f"bot.common.graphql.{method}", return_value=returns)


# assert that a message has a particular emoji reaction
def assert_message_reaction(message: MockMessage, emoji: str = None):
    assert emoji in message.reactions, f"emoji {emoji} was not in message reactions"


def assert_message_content(message: MockMessage, expected_content: str = None):
    assert (
        expected_content == message.content
    ), f"message {expected_content} was not in message content"


# assert that the supplied context has a particular message sent
def assert_context_response(context: MockContext, message: str = None):
    assert (
        message == context.response.sent_content
    ), f"message {message} was not in context response"


# assert that a file was sent in response
def assert_file_in_response(response: MockResponse):
    assert response.file is not None, "no file was present in response"
