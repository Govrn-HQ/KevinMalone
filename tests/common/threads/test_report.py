import pytest
import json

from tests.test_utils import MockCache, MockContext, MockMessage
from tests.test_utils import mock_gql_query
from tests.test_utils import (
    assert_message_content,
    assert_message_reaction,
)

from bot.common.threads.report import (
    ReportStep
)
from bot.common.threads.thread_builder import StepKeys


@pytest.mark.asyncio
async def test_reporting_step(mocker, thread_dependencies):
    (cache, context, message, bot) = thread_dependencies
    report = ReportStep("0", cache)