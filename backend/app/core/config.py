from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SECRET_KEY: str = "changeme-use-env-var-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    GEMINI_API_KEY: str = ""
<<<<<<< HEAD
    GOOGLE_API_KEY: str = ""
=======
>>>>>>> 75c91182625ee9dee6a4528b59c1768904dcdf6b

    model_config = {"env_file": ".env"}


settings = Settings()
