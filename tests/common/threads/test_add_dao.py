import pytest

from bot.common.threads.add_dao import (
    AddDaoPromptIdStep
)

from tests.test_utils import mock_gql_query

@pytest.mark.asyncio
async def test_add_dao_prompt_id(mocker, thread_dependencies):
    (cache, context, message, bot) = thread_dependencies
    user_id = "1234"
    step = AddDaoPromptIdStep()
    (sent_message, metadata) = await step.send(message, user_id)
    assert(sent_message)
