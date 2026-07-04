from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Symon Image Server"
    host: str = "0.0.0.0"
    port: int = 8090

    llm_base_url: str = "http://127.0.0.1:8080/v1"
    llm_model: str = "local"

    output_dir: str = "/home/google/symon-image-server/data/outputs"
    upload_dir: str = "/home/google/symon-image-server/data/uploads"

    api_keys: str = ""
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    public_base_url: str = "http://127.0.0.1:8090"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
