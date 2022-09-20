import pytest

from tests.test_utils import MockCache, MockContext, MockMessage
from tests.test_utils import mock_gql_query
from tests.test_utils import (
    assert_channel_message_sent,
    assert_context_response,
    assert_file_in_response,
    assert_message_reaction,
)

from bot.common.threads.history import DisplayHistoryStep


@pytest.mark.asyncio
async def test_display_history_step(mocker):
    cache = MockCache()
    context = MockContext()
    message = MockMessage()
    user_id = "1"
    history_step = DisplayHistoryStep(None, cache, None, context)

    mock_gql_query(mocker, method="fetch_user_by_discord_id", returns=None)
    await history_step.send(message, user_id)

    # Check prompt for joining
    expected_message = DisplayHistoryStep.onboard_prompt_content
    assert_channel_message_sent(message.channel, expected_message)


def test_get_contributions_csv_prompt(mocker):
    pass


def test_get_contributions_csv_prompt_emoji(mocker):
    pass


def test_get_contributions_csv_prompt_accept(mocker):
    pass


def test_history_thread_happypath(mocker):
    mock_gql_query(mocker, method="", returns=None)
