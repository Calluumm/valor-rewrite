from dotenv import load_dotenv
import os, json


current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
env_path = os.path.join(project_root, '.env')
load_dotenv(env_path)


def _normalize_discord_token(raw_token: str | None) -> str | None:
    if not raw_token:
        return None

    token = raw_token.strip()

    if token.startswith("Bot "):
        token = token[4:].strip()

    if (token.startswith('"') and token.endswith('"')) or (token.startswith("'") and token.endswith("'")):
        token = token[1:-1].strip()

    return token or None


class Config:
    TOKEN = _normalize_discord_token(os.getenv("DISCORD_TOKEN") or os.getenv("TOKEN"))

    OWNER_ID = int(os.getenv("OWNER_ID", 0))

    TESTING = os.getenv("TESTING", "false").lower() == "true"

    DB_HOST = os.getenv("DBHOST")
    DB_PORT = int(os.getenv("DATABASE_PORT", 3306))  # default MySQL port
    DB_USER = os.getenv("DBUSER")
    DB_PASSWORD = os.getenv("DBPASS")
    DB_NAME = os.getenv("DBNAME")

    HYPIXEL_API_KEY = os.getenv("HYPIXEL_API_KEY")

    WYNN_API_KEY = os.getenv("WYNN_API_KEY")

    ANO_COMMANDS_GUILD_IDS = json.loads(os.getenv("ANO_COMMANDS_GUILD_IDS"))

    ANO_MEMBER_ROLE = os.getenv("ANO_MEMBER_ROLE")
    ANO_MILITARY_ROLE = os.getenv("ANO_MILITARY_ROLE")

    ANO_HIGH_RANK_ROLES = json.loads(os.getenv("ANO_HIGH_RANK_ROLES"))
    ANO_TITAN_ROLES = json.loads(os.getenv("ANO_TITAN_ROLES"))
    ANO_CHIEF_ROLES = json.loads(os.getenv("ANO_CHIEF_ROLES"))
    TITAN_CHAT_CHANNEL_ID = json.loads(os.getenv("TITAN_CHAT_CHANNEL_ID"))



# Create a global config instance to import elsewhere
config = Config()
