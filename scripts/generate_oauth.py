import os
from discord.permissions import Permissions
from discord.utils import oauth_url

from dotenv import load_dotenv

load_dotenv()


def generate_oauth():
    client_id = os.getenv("CLIENT_ID", "")
    # Has send messages permisison
    permissions = Permissions(permissions=2684356608)
    generated_url = oauth_url(client_id, permissions=permissions)
    print(f"Generated oauth for given client id: {generated_url}")


if __name__ == "__main__":
    generate_oauth()
