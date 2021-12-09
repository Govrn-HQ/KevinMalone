import logging

logger = logging.getLogger(__name__)


def get_user(user):
    return not bool(user.id)


def store_user_ids(guild_id, user_id):
    logging.infor(f"Storing user_id: {user_id} and guild_id: {guild_id}")
