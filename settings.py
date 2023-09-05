import os

from pydantic_settings import BaseSettings


class Setting(BaseSettings):
    app_name: str = "RDFConverter"
    admin_email: str = os.environ.get("ADMIN_MAIL") or "rdfconverter@matolab.org"
    items_per_user: int = 50
    version: str = "v1.0.3"
    config_name: str = os.environ.get("APP_MODE") or "development"
    openapi_url: str = "/api/openapi.json"
    docs_url: str = "/api/docs"
