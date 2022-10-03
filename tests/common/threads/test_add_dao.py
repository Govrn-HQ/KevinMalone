import pytest

from bot.common.threads.add_dao import (
    AddDaoPromptIdStep,
    AddDaoGetOrCreate
)
from bot.exceptions import ThreadTerminatingException
from tests.test_utils import mock_gql_query


class MockThread:
    def __init__(self):
        self.guild_id = None


@pytest.mark.asyncio
async def test_add_dao_prompt_id(mocker, thread_dependencies):
    (cache, context, message, bot) = thread_dependencies
    user_id = "1234"
    step = AddDaoPromptIdStep()
    (sent_message, metadata) = await step.send(message, user_id)
    assert(sent_message)


@pytest.mark.asyncio
async def test_add_dao_get_or_create_send_fails(mocker, thread_dependencies):
    mock_thread = MockThread()
    (cache, context, message, bot) = thread_dependencies
    message.content = "this is not a valid discord id"
    step = AddDaoGetOrCreate(mock_thread, cache)
    user_id = "1234"
    try:
        (sent_message, metadata) = await step.send(message, user_id)
        assert(False)
    except ThreadTerminatingException:
        # happy
        pass


@pytest.mark.asyncio
async def test_add_dao_get_or_create_send(mocker, thread_dependencies):
    mock_thread = MockThread()
    (cache, context, message, bot) = thread_dependencies
    step = AddDaoGetOrCreate(mock_thread, cache)
    user_id = "1234"
    dao_id = "956271220951765001"
    expected_metadata = {
        "guild_id": dao_id
    }

    message.content = dao_id
    (sent_message, metadata) = await step.send(message, user_id)
    assert(sent_message is None)
    assert(metadata is expected_metadata)
