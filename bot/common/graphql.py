import logging
import time

from bot import constants
from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport

logger = logging.getLogger(__name__)


def get_async_transport(url):
    return AIOHTTPTransport(
        url=url, headers={"Authorization": constants.Bot.protocol_token}
    )


async def execute_query(query, values):
    transport = get_async_transport(constants.Bot.protocol_url)
    try:
        async with Client(
            transport=transport, fetch_schema_from_transport=False
        ) as session:
            query = gql(query)
            resp = await session.execute(query, variable_values=values)
            return resp
    except Exception:
        logger.exception(f"Failed to execute query {query}")
        return None


async def fetch_user(id):
    query = """
fragment UserFragment on User {
  address
  chain_type {
    id
    name
    createdAt
    updatedAt
  }
  createdAt
  display_name
  full_name
  id
  name
  updatedAt
  guild_users {
    id
    guild_id
  }
}

query getUser($where: UserWhereInput!,) {
    result: users(
        where: $where,
    ) {
      ...UserFragment
    }
}
    """
    result = await execute_query(
        query, {"where": {"discord_users": {"some": {"discord_id": {"equals": id}}}}}
    )
    if result.get("result"):
        print(result)
        print(id)
        return result.get("result")[0]
    return result


async def list_contributions(id):
    query = """
fragment ContributionFragment on Contribution {
  activity_type {
    active
    createdAt
    id
    name
    updatedAt
  }
  date_of_engagement
  date_of_submission
  details
  id
  name
  proof
  status {
    createdAt
    id
    name
    updatedAt
  }
  updatedAt
  user {
    address
    createdAt
    display_name
    full_name
    id
    name
    updatedAt
  }
  attestations {
    id
  }
}

query listContributions($where: ContributionWhereInput! = {}, $skip: Int! = 0, $first: Int! = 10, $orderBy: [ContributionOrderByWithRelationInput!]) {
    result: contributions(
        where: $where,
        skip: $skip,
        take: $first,
        orderBy: $orderBy,
    ) {
      ...ContributionFragment
    }
}

    """
    result = await execute_query(
        query, {"where": {"guilds": {"some": {"guild_id": id}}}}
    )
    if result:
        return result.results
    return result


async def get_guild(id):
    query = """
fragment GuildFragment on Guild {
  congrats_channel
  createdAt
  discord_id
  id
  logo
  name
  updatedAt
}

query getGuild($where: GuildWhereUniqueInput!,) {
    result: guild(
        where: $where,
    ) {
      ...GuildFragment
    }
}
    """
    result = await execute_query(query, {"where": {id}})
    if result:
        return result.result
    return result


async def create_guild_user(user_id, guild_id):
    query = """
mutation createGuildUser($data: GuildUserCreateInput!) {
  createGuildUser(data: $data) {
    guild_id
    user_id
  }
}
    """
    result = await execute_query(
        query,
        {
            "data": {
                "guild": {"connect": guild_id},
                "user": {"connect": {"id": user_id}},
            }
        },
    )
    if result:
        return result.createGuildUser
    return result


async def create_user(discord_id, wallet):
    query = """
mutation createUser($data: GuildUserCreateInput!) {
  createUser(data: $data) {
    id
  }
}
    """
    result = await execute_query(
        query,
        {
            "data": {
                "address": wallet,
                "discord_users": {
                    "connectOrCreate": [
                        {
                            "create": {"discord_id": discord_id},
                            "connect": {"discord_id": discord_id},
                        }
                    ]
                },
            }
        },
    )
    if result:
        print(result)
        return result.createUser
    return result
