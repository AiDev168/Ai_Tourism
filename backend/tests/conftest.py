"""Keep test configuration isolated from the developer's root .env file."""

from app.core.config import Settings

# Runtime Settings still loads .env by default. Tests must opt into explicit
# settings or temporary files so local secrets never influence test behavior.
Settings.model_config["env_file"] = None
