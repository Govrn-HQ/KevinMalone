import pytest

from bot.common.threads.update import UserUpdateFieldSelectStep
from bot.config import get_list_of_emojis

from tests.test_utils import assert_field_in_sent_embeds, mock_gql_query


@pytest.mark.asyncio
async def test_user_update_field_selection(mocker, thread_dependencies):
    (cache, context, message, bot) = thread_dependencies
    user_id = "1234"
    mock_user = {
        "twitter_user": {"username": "test_twitter_user"},
        "display_name": "test_display_name",
        "address": "0x0"
    }
    step = UserUpdateFieldSelectStep(None)
    expected_emojis = get_list_of_emojis(3)
    try:
        mock_gql_query(mocker, "get_user_by_discord_id", None)
        await step.send(None, None)
        assert False
    except Exception as e:
        assert "No user for updating field" == f"{e}"

    mock_gql_query(mocker, "get_user_by_discord_id", mock_user)
    (sent_message, metadata) = await step.send(message, user_id)
    mock_channel = message.channel

    assert_field_in_sent_embeds(mock_channel, f"Display Name {expected_emojis[0]}")
    assert_field_in_sent_embeds(mock_channel, f"Twitter Handle {expected_emojis[1]}")
    assert_field_in_sent_embeds(
        mock_channel,
        f"Ethereum Wallet Address {expected_emojis[2]}"
    )

    assert len(metadata.keys()) == 3
