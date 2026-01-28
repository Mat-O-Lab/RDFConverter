import os
from pydantic_settings import BaseSettings


class Setting(BaseSettings):
    name: str = str(os.environ.get("APP_NAME", "RDFConverter"))
    contact_name: str = str(os.environ.get("ADMIN_NAME", "Thomas Hanke"))
    admin_email: str = str(
        os.environ.get("ADMIN_MAIL", "thomas.hanke@iwm.fraunhofer.de")
    )
    items_per_user: int = 50
    version: str = str(os.environ.get("APP_VERSION", "v1.2.1"))
    config_name: str = str(os.environ.get("APP_MODE", "development"))
    openapi_url: str = "/api/openapi.json"
    docs_url: str = "/api/docs"
    source: str = str(
        os.environ.get("APP_SOURCE", "https://github.com/Mat-O-Lab/RDFConverter")
    )
    server: str = os.environ.get("SERVER_URL") or "http://localhost:6003"
    root_path: str = os.environ.get("ROOT_PATH", "")
    desc: str = (
        "A service for joining and converting meta data documents based on YARRRML mapping files to RDF, optionally a validiation can be conducted using SHACL Shapes."
    )
    org_site: str = "https://mat-o-lab.github.io/OrgSite"
