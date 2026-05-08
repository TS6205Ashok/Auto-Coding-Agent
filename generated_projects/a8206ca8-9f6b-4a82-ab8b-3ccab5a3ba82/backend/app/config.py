from pathlib import Path
import os

from dotenv import load_dotenv


APP_DIR = Path(__file__).resolve().parent
PROJECT_DIR = APP_DIR.parent
PARENT_PROJECT_DIR = PROJECT_DIR.parent

for candidate in (PROJECT_DIR / ".env", PARENT_PROJECT_DIR / ".env"):
    if candidate.exists():
        load_dotenv(candidate, override=False)


def get_env(name: str, description: str = "", required: bool = True, default: str | None = None) -> str:
    value = os.getenv(name)
    if value:
        return value
    if not required:
        return default or ""
    print(f"Missing required input: {name}")
    if description:
        print(description)
    prompt = f"Please enter {name}: "
    value = input(prompt).strip()
    if not value and required:
        raise RuntimeError(f"{name} is required.")
    return value


class Settings:
    def __init__(self) -> None:
        self.app_env = get_env("APP_ENV", required=False, default="development")
        self.port = int(get_env("PORT", required=False, default="8000") or "8000")
        self.database_url = get_env("DATABASE_URL", description="SQLite connection string for local development.", required=True)


settings = Settings()
