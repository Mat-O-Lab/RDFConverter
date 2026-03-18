import os
from pydantic_settings import BaseSettings


class Setting(BaseSettings):
    name: str = str(os.environ.get("APP_NAME", "RDFConverter"))
    contact_name: str = str(os.environ.get("ADMIN_NAME", "Thomas Hanke"))
    admin_email: str = str(
        os.environ.get("ADMIN_MAIL", "thomas.hanke@iwm.fraunhofer.de")
    )
    items_per_user: int = 50
    version: str = str(os.environ.get("APP_VERSION", "v1.3.0"))
    config_name: str = str(os.environ.get("APP_MODE", "development"))
    openapi_url: str = "/api/openapi.json"
    docs_url: str = "/api/docs"
    source: str = str(
        os.environ.get("APP_SOURCE", "https://github.com/Mat-O-Lab/RDFConverter")
    )
    server: str = os.environ.get("SERVER_URL") or "http://localhost:6003"
    root_path: str = os.environ.get("ROOT_PATH", "")
    desc: str = (
        "A REST API service for transforming data (JSON, CSV, RDF) into semantic RDF knowledge graphs using declarative YARRRML mappings. Optionally, a validation can be conducted using SHACL shapes."
    )
    org_site: str = "https://mat-o-lab.github.io/OrgSite"
