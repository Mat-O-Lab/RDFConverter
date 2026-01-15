import base64
import logging
import os
import re
from io import BytesIO
from typing import Any, List, Optional, Tuple
from urllib.parse import unquote, urlparse
from xmlrpc.client import Boolean

import requests
import uvicorn
import yaml
from fastapi import Body, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.encoders import jsonable_encoder
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import AnyUrl, BaseModel, Field
from pyshacl import validate
from rdflib import Graph, Namespace, URIRef, BNode, Literal
from rdflib.namespace import CSVW, RDF, RDFS, PROV, XSD
from rdflib.util import guess_format
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from starlette_wtf import StarletteForm
from starlette.background import BackgroundTask

from wtforms import BooleanField, URLField
from wtforms.validators import Optional as WTFOptional

from rmlmapper import count_rules_str, replace_data_source, replace_all_data_sources, strip_namespace
from enum import Enum

YARRRML_URL = os.environ.get("YARRRML_URL")
MAPPER_URL = os.environ.get("MAPPER_URL")

SSL_VERIFY = os.getenv("SSL_VERIFY", "True").lower() in ("true", "1", "t")
if not SSL_VERIFY:
    requests.packages.urllib3.disable_warnings()

TEMPLATE_NAMESPACE = "http://template_base/"

import settings

setting = settings.Setting()

config_name = os.environ.get("APP_MODE", "production")

middleware = [
    Middleware(
        SessionMiddleware, secret_key=os.environ.get("APP_SECRET", "changemeNOW")
    ),
    # Middleware(CSRFProtectMiddleware, csrf_secret=os.environ.get('APP_SECRET','changemeNOW')),
    Middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allows all origins
        allow_methods=["*"],  # Allows all methods
        allow_headers=["*"],  # Allows all headers
    ),
    Middleware(
        uvicorn.middleware.proxy_headers.ProxyHeadersMiddleware, trusted_hosts="*"
    ),
]

tags_metadata = [
    {
        "name": "transform",
        "description": "transforms data to other format",
    }
]

app = FastAPI(
    title=setting.name,
    description=setting.desc,
    version=setting.version,
    contact={
        "name": "Thomas Hanke, Mat-O-Lab",
        "url": "https://github.com/Mat-O-Lab",
        "email": setting.admin_email,
    },
    # contact={"name": setting.contact_name, "url": setting.org_site, "email": setting.admin_email},
    license_info={
        "name": "Apache 2.0",
        "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
    },
    openapi_url=setting.openapi_url,
    openapi_tags=tags_metadata,
    docs_url=setting.docs_url,
    redoc_url=None,
    swagger_ui_parameters={"syntaxHighlight": False},
    # swagger_favicon_url="/static/resources/favicon.svg",
    middleware=middleware,
    servers=[
        {"url": setting.server, "description": "Production environment"},
    ],
)


app.mount("/static/", StaticFiles(directory="static", html=True), name="static")
templates = Jinja2Templates(directory="templates")


# flash integration flike flask flash
def flash(request: Request, message: Any, category: str = "info") -> None:
    if "_messages" not in request.session:
        request.session["_messages"] = []
    request.session["_messages"].append({"message": message, "category": category})


def get_flashed_messages(request: Request):
    return request.session.pop("_messages") if "_messages" in request.session else []


templates.env.globals["get_flashed_messages"] = get_flashed_messages


OBO = Namespace("http://purl.obolibrary.org/obo/")
MSEO_URL = "http://purl.matolab.org/mseo/mid/"
CCO_URL = "https://github.com/CommonCoreOntology/CommonCoreOntologies/raw/master/cco-merged/MergedAllCoreOntology-v1.3-2021-03-01.ttl"
MSEO = Namespace(MSEO_URL)
CCO = Namespace("http://www.ontologyrepository.com/CommonCoreOntologies/")
CSVW = Namespace("http://www.w3.org/ns/csvw#")
OA = Namespace("http://www.w3.org/ns/oa#")
QUDT = Namespace("http://qudt.org/schema/qudt/")
QUNIT = Namespace("http://qudt.org/vocab/unit/")
IOF = Namespace("https://spec.industrialontologies.org/ontology/core/Core/")
# RDF = Namespace('http://www.w3.org/2000/01/rdf-schema#')


class ReturnType(str, Enum):
    jsonld = "json-ld"
    n3 = "n3"
    # nquads="nquads" #only makes sense for context-aware stores
    nt = "nt"
    hext = "hext"
    # prettyxml="pretty-xml" #only makes sense for context-aware stores
    trig = "trig"
    # trix="trix" #only makes sense for context-aware stores
    turtle = "turtle"
    longturtle = "longturtle"
    xml = "xml"

    @classmethod
    def get(cls, format):
        for member in cls:
            if format.lower() == member.value.lower():
                return member
        raise ValueError(f"Invalid Return type: {format}")


class RDFMimeType(str, Enum):
    xml = "application/rdf+xml"
    turtle = "text/turtle"
    n3 = "application/n-triples"
    nquads = "application/n-quads"
    jsonld = "application/ld+json"

    @classmethod
    def get(cls, format):
        for member in cls:
            if format.lower() == member.value.lower():
                return member
        raise ValueError(f"Invalid Return type: {format}")


class RDFStreamingResponse(StreamingResponse):
    def __init__(
        self,
        content,
        filename: str,
        status_code: int = 200,
        background: Optional[BackgroundTask] = None,
    ):
        headers = {
            "Content-Disposition": "attachment; filename={}".format(filename),
            "Access-Control-Expose-Headers": "Content-Disposition",
        }
        media_type = RDFMimeType[ReturnType.get(guess_format(filename)).name].value
        super(RDFStreamingResponse, self).__init__(
            content, status_code, headers, media_type
        )


def replace_between(
    text: str, begin: str = "", end: str = "", alternative: str = ""
) -> str:
    if not (begin and end):
        raise ValueError
    return re.sub(
        r"{}.*?{}".format(re.escape(begin), re.escape(end)), alternative, text
    )


def open_file(uri: AnyUrl, authorization=None) -> Tuple["filedata":str, "filename":str]:
    try:
        uri_parsed = urlparse(uri)
        # print(uri_parsed)

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"{uri} is not a valid URI - if local file add file:// as prefix. Error: {str(e)}",
        ) from e
    else:
        filename = unquote(uri_parsed.path).rsplit("/download/upload")[0].split("/")[-1]
        if uri_parsed.scheme in ["https", "http"]:
            # r = urlopen(uri)
            s = requests.Session()
            s.verify = SSL_VERIFY
            s.headers.update({"Authorization": authorization})
            r = s.get(uri, allow_redirects=True, stream=True)

            # r.raise_for_status()
            if r.status_code != 200:
                # logging.debug(r.content)
                raise HTTPException(
                    status_code=r.status_code, detail="cant get file at {}".format(uri)
                )
            filedata = r.content
            # charset=r.info().get_content_charset()
            # if not charset:
            #     charset='utf-8'
            # filedata = r.read().decode(charset)
        elif uri_parsed.scheme == "file":
            filedata = open(unquote(uri_parsed.path), "rb").read()
        else:
            raise HTTPException(
                status_code=400, detail="unknown scheme {}".format(uri_parsed.scheme)
            )
        return filedata, filename


from datetime import datetime


# ============================================================================
# HELPER FUNCTIONS - Data Processing & RML Execution
# ============================================================================

def get_standard_jsonld_context() -> dict:
    """Return standard JSON-LD context for CSVW normalization.
    
    Returns:
        Dict containing standard namespace mappings for JSON-LD serialization
    """
    return {
        "@vocab": str(CSVW),
        "rdf": str(RDF),
        "qudt": str(QUDT),
        "qunit": str(QUNIT),
        "label": "http://www.w3.org/2000/01/rdf-schema#label",
    }


def extract_jsonld_namespaces(content: bytes) -> tuple[dict, str | None]:
    """Extract namespace bindings from JSON-LD @context.
    
    Args:
        content: JSON-LD content as bytes
        
    Returns:
        Tuple of (namespace_dict, csv_namespace)
        - namespace_dict: Dict mapping prefix -> namespace URL
        - csv_namespace: The 'csv' namespace URL if found, else None
    """
    import json
    
    namespace_dict = {}
    csv_namespace = None
    
    try:
        json_data = json.loads(content)
        ctx = json_data.get("@context", [])
        
        # Context can be a list or dict
        contexts_to_process = []
        if isinstance(ctx, list):
            contexts_to_process = [item for item in ctx if isinstance(item, dict)]
        elif isinstance(ctx, dict):
            contexts_to_process = [ctx]
            
        for context in contexts_to_process:
            for prefix, ns in context.items():
                if isinstance(ns, str) and prefix not in ["@vocab"]:
                    namespace_dict[prefix] = ns
                    logging.debug(f"Extracted namespace from JSON-LD context: {prefix} -> {ns}")
                    if prefix == "csv":
                        csv_namespace = ns
                        logging.info(f"Stored CSV namespace from JSON-LD: {csv_namespace}")
    except Exception as e:
        logging.warning(f"Could not extract context from JSON-LD: {e}")
        
    return namespace_dict


def detect_data_format(content: bytes, url: str) -> tuple[str | None, bool]:
    """Detect if content is JSON, RDF, or unknown.
    
    Args:
        content: Data content as bytes
        url: Source URL (used for format guessing)
        
    Returns:
        Tuple of (format_string, is_rdf)
        - format_string: 'json' for plain JSON, or RDF format like 'turtle', 'json-ld', etc.
        - is_rdf: True if RDF format detected, False for plain JSON
        
    Raises:
        HTTPException: If format cannot be determined
    """
    import json
    
    # Try plain JSON first
    try:
        json.loads(content)
        logging.info("Content detected as plain JSON")
        return "json", False
    except (json.JSONDecodeError, ValueError):
        pass
    
    # Try RDF format
    data_format = guess_format(url)
    if data_format:
        logging.info(f"Content detected as RDF format: {data_format}")
        return data_format, True
    
    raise HTTPException(
        status_code=422,
        detail=f"Could not determine data format from URL: {url}",
    )


def process_data_to_jsonld(
    content: bytes, 
    url: str,
    preserve_namespaces: bool = True
) -> tuple[str, bool, str | None]:
    """Process data content to JSON-LD format for RML mapper.
    
    Args:
        content: Data content as bytes
        url: Source URL
        preserve_namespaces: Whether to preserve original namespaces from JSON-LD
        
    Returns:
        Tuple of (processed_content, is_rdf_data, csv_namespace)
        - processed_content: Data in JSON-LD format as string
        - is_rdf_data: True if source was RDF, False if plain JSON
        - csv_namespace: CSV namespace if found in original data, else None
        
    Raises:
        HTTPException: If data processing fails
    """
    import json
    
    # ALWAYS try to extract @context from JSON FIRST, before any RDF parsing
    namespaces = None
    if preserve_namespaces:
        try:
            namespaces = extract_jsonld_namespaces(content)
        except Exception as e:
            logging.debug(f"No JSON @context found (file may not be JSON or JSON-LD): {e}")
    
    # Now detect format
    data_format, is_rdf = detect_data_format(content, url)
    
    if not is_rdf:
        # Plain JSON - use as-is (we already extracted @context above)
        processed_content = content.decode() if isinstance(content, bytes) else content
        return processed_content, False, namespaces
    
    # RDF data - normalize to JSON-LD
    try:
        logging.debug(f"Loading {url} as RDF in {data_format} format")
        
        
        # Parse as RDF
        temp_graph = Graph()
        temp_graph.parse(data=content, format=data_format)
        
        # Normalize to JSON-LD with standard context + preserved namespaces
        context = get_standard_jsonld_context()
        context.update(namespaces)
        
        processed_content = temp_graph.serialize(format="json-ld", context=context)
        logging.info(f"Normalized RDF to JSON-LD")
        
        return processed_content, True, namespaces
        
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail=f"Could not read source {url} - not valid RDF or JSON format: {str(e)}",
        ) from e


def convert_yarrrml_to_rml(mapping_data: bytes | str) -> str:
    """Convert YARRRML to RML format via web API.
    
    Args:
        mapping_data: YARRRML content as bytes or string
        
    Returns:
        RML rules as string in Turtle format
        
    Raises:
        requests.RequestException: If conversion fails
    """
    response = requests.post(YARRRML_URL, data={"yarrrml": mapping_data})
    response.raise_for_status()
    return response.text


def parse_and_replace_rml_source(rml_rules: str, source_placeholder: str) -> str:
    """Parse RML rules and replace data source with placeholder.
    
    Args:
        rml_rules: RML rules in Turtle format
        source_placeholder: Placeholder filename (e.g., 'source.json')
        
    Returns:
        Modified RML rules as string
        
    Raises:
        Exception: If parsing fails
    """
    rml_graph = Graph()
    rml_graph.parse(data=rml_rules, format="ttl")
    replace_data_source(rml_graph, source_placeholder)
    return rml_graph.serialize(format="ttl")


def execute_rml_mapper(
    rml_rules: str,
    sources: dict[str, str],
    serialization: str = "turtle"
) -> str:
    """Execute RML mapper web API and return output.
    
    Args:
        rml_rules: RML rules in Turtle format
        sources: Dict of {placeholder_filename: content_string}
        serialization: Output format (default: 'turtle')
        
    Returns:
        Mapping output as string
        
    Raises:
        HTTPException: If mapper fails
    """
    payload = {
        "rml": rml_rules,
        "sources": sources,
        "serialization": serialization,
    }
    
    logging.debug(f"Calling RML mapper at: {MAPPER_URL}/execute")
    logging.debug(f"Number of sources: {len(sources)}")
    
    try:
        response = requests.post(MAPPER_URL + "/execute", json=payload)
        
        logging.debug(f"RML Mapper response status: {response.status_code}")
        
        if response.status_code != 200:
            logging.error(f"RML Mapper error response: {response.text}")
            raise HTTPException(
                status_code=response.status_code,
                detail=f"RML mapper failed: {response.text}"
            )
        
        result = response.json()["output"]
        logging.debug(f"RML Mapper output length: {len(result)} chars")
        
        return result
        
    except requests.RequestException as e:
        logging.error(f"Exception calling RML mapper: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Could not generate mapping results with rmlmapper: {str(e)}",
        ) from e


def download_sources(
    sources: dict,
    opt_data_url: str | None = None,
    authorization: str | None = None
) -> tuple[dict, str, str]:
    """Download all sources from mapping and build URL mapping.
    
    Args:
        sources: Sources dict from YARRRML mapping
        opt_data_url: Optional override URL for first source
        authorization: Authorization header value
        
    Returns:
        Tuple of (url_mapping, primary_data_url, filename)
        - url_mapping: Dict mapping original_url -> {placeholder, content, actual_url, original_url}
        - primary_data_url: The primary data URL (first source)
        - filename: Suggested output filename
        
    Raises:
        HTTPException: If download fails
    """
    if not sources:
        raise HTTPException(
            status_code=422, detail="No sources found in mapping file"
        )
    
    url_mapping = {}
    counter = 1
    primary_data_url = None
    filename = "data-joined.ttl"
    
    for source_name, source_def in sources.items():
        # Strip trailing slash only for downloading - preserve for namespace matching later
        original_url_for_download = source_def["access"].strip("/")
        original_url = source_def["access"]  # Keep as-is for namespace matching
        
        # Handle optional data_url override for the first source
        if counter == 1:
            if opt_data_url:
                actual_url = opt_data_url.strip("/")  # Strip for download
                primary_data_url = opt_data_url  # Keep as-is for namespace
            else:
                actual_url = original_url_for_download
                primary_data_url = original_url
        else:
            actual_url = original_url_for_download
        
        placeholder = f"source_{counter}.json"
        
        # Download content
        logging.debug(f"Downloading source {source_name} from {actual_url}")
        data_content, data_filename = open_file(actual_url, authorization)
        
        url_mapping[original_url] = {
            "placeholder": placeholder,
            "content": data_content,
            "original_url": original_url,
            "actual_url": actual_url
        }
        
        # Store filename from first source
        if counter == 1:
            filename = data_filename.rsplit(".", 1)[0].rsplit("-", 1)[0] + "-joined.ttl"
        
        counter += 1
    
    return url_mapping, primary_data_url, filename


def replace_base_uris(graph: Graph, base_uri: str) -> Graph:
    """Replace all http://example.com URIs with the specified base URI.
    
    Args:
        graph: RDF graph containing URIs to replace
        base_uri: Base URI to use (e.g., 'http://example.org/' or '#' for relative)
        
    Returns:
        Modified graph with replaced URIs
    """
    if not base_uri:
        return graph
    
    # Handle different base formats
    # - Full URI: "http://purl.matolab.org/mseo/mappings/" 
    # - Relative: "#"
    # Ensure trailing separator if not "#" and doesn't already have one
    if base_uri != "#":
        if not base_uri.endswith(("/", "#")):
            base_uri += "/"
    
    logging.info(f"Replacing http://example.com URIs with base: {base_uri}")
    
    triples_to_replace = []
    for s, p, o in graph:
        new_s, new_p, new_o = s, p, o
        changed = False
        
        # Replace subjects starting with http://example.com
        if isinstance(s, URIRef) and str(s).startswith("http://example.com"):
            local_part = str(s).replace("http://example.com", "")
            if base_uri == "#":
                new_s = URIRef("#" + local_part)
            else:
                new_s = URIRef(base_uri + local_part)
            changed = True
            logging.debug(f"  Subject: {s} -> {new_s}")
        
        # Replace predicates starting with http://example.com (rare but possible)
        if isinstance(p, URIRef) and str(p).startswith("http://example.com"):
            local_part = str(p).replace("http://example.com", "")
            if base_uri == "#":
                new_p = URIRef("#" + local_part)
            else:
                new_p = URIRef(base_uri + local_part)
            changed = True
            logging.debug(f"  Predicate: {p} -> {new_p}")
        
        # Replace objects starting with http://example.com
        if isinstance(o, URIRef) and str(o).startswith("http://example.com"):
            local_part = str(o).replace("http://example.com", "")
            if base_uri == "#":
                new_o = URIRef("#" + local_part)
            else:
                new_o = URIRef(base_uri + local_part)
            changed = True
            logging.debug(f"  Object: {o} -> {new_o}")
        
        if changed:
            triples_to_replace.append(((s, p, o), (new_s, new_p, new_o)))
    
    # Apply replacements
    for old_triple, new_triple in triples_to_replace:
        graph.remove(old_triple)
        graph.add(new_triple)
    
    if triples_to_replace:
        logging.info(f"✓ Replaced {len(triples_to_replace)} triples with base URI: {base_uri}")
    else:
        logging.info("No http://example.com URIs found to replace")
    
    return graph


# ============================================================================
# END HELPER FUNCTIONS
# ============================================================================


def apply_all_namespaces(
    graph: Graph,
    accumulated_namespaces: dict,
    data_namespace: str | None,
    method_namespace: str | None
) -> Graph:
    """Centralized namespace binding routine - call ONCE before serialization.
    
    Args:
        graph: The RDF graph to bind namespaces to
        accumulated_namespaces: Dict of {prefix: namespace_url} from template/mapping
        csv_namespace: CSV namespace from JSON-LD @context (highest priority)
        data_namespace: Data namespace from primary data URL
        method_namespace: Method namespace from YARRRML mapping prefixes
        
    Returns:
        The graph with all namespaces properly bound
    """
    logging.info("=" * 80)
    logging.info("APPLYING ALL NAMESPACES (CENTRALIZED)")
    logging.info("=" * 80)
    
    # 1. Bind empty prefix for relative IRIs (e.g., :SpecimenID)
    graph.namespace_manager.bind("", Namespace(""), override=True, replace=True)
    logging.info("✓ Bound empty prefix '' to empty namespace")
    
    # 2. Bind 'base' prefix to empty namespace
    graph.namespace_manager.bind("base", Namespace(""), override=True, replace=True)
    logging.info("✓ Bound 'base' prefix to empty namespace")
    logging.debug(accumulated_namespaces)
    # 3. Bind all accumulated namespaces from template/mapping graphs
    logging.info(f"Binding {len(accumulated_namespaces)} accumulated namespaces:")
    for prefix, namespace_str in accumulated_namespaces.items():
        graph.namespace_manager.bind(prefix, Namespace(namespace_str), override=True)
        logging.info(f"  ✓ {prefix}: {namespace_str}")
    
    
    # 6. Log final namespace bindings
    logging.info("=" * 80)
    logging.info("FINAL NAMESPACE BINDINGS IN GRAPH:")
    for prefix, namespace in graph.namespaces():
        logging.info(f"  {prefix or '(empty)'}: {namespace}")
    logging.info("=" * 80)
    
    return graph


def add_prov(graph: Graph, api_url: str, data_url: str, used: list = []) -> Graph:
    """Add prov-o information to output graph

    Args:
        graph (Graph): Graph to add prov information to
        api_url (str): the api url
        data_url (str): the url to the rdf file that was used

    Returns:
        Graph: Input Graph with prov metadata of the api call
    """
    graph.bind("prov", PROV)

    root = BNode()
    api_node = URIRef(api_url)
    graph.add((root, PROV.wasGeneratedBy, api_node))
    graph.add((api_node, RDF.type, PROV.Activity))
    software_node = URIRef(setting.source + "/releases/tag/" + setting.version)
    graph.add((api_node, PROV.wasAssociatedWith, software_node))
    graph.add((software_node, RDF.type, PROV.SoftwareAgent))
    graph.add((software_node, RDFS.label, Literal(setting.name + setting.version)))
    graph.add((software_node, PROV.hadPrimarySource, URIRef(setting.source)))
    graph.add(
        (
            root,
            PROV.generatedAtTime,
            Literal(str(datetime.now().isoformat()), datatype=XSD.dateTime),
        )
    )
    entity = URIRef(str(data_url))
    graph.add((entity, RDF.type, PROV.Entity))
    derivation = BNode()
    graph.add((derivation, RDF.type, PROV.Derivation))
    graph.add((derivation, PROV.entity, entity))
    graph.add((derivation, PROV.hadActivity, api_node))
    graph.add((root, PROV.qualifiedDerivation, derivation))
    graph.add((root, PROV.wasDerivedFrom, entity))
    if used:
        [graph.add((api_node, PROV.wasInformedBy, URIRef(entry))) for entry in used]
    return graph


def apply_mapping(
    mapping_url: AnyUrl, opt_data_url: AnyUrl = None, authorization=None, api_url: str = None
) -> Tuple[str, int, int]:
    """Apply YARRRML mapping to data sources.

    Args:
        mapping_url: URL to YARRRML mapping file
        opt_data_url: Optional override URL for first data source
        authorization: Authorization header value
        api_url: Full API URL (e.g., http://host:port/api/createrdf) for provenance

    Returns:
        Tuple of (filename, graph_output, num_rules_total, num_rules_applied)

    Raises:
        HTTPException: If any step fails
    """
    # Load and parse mapping file
    mapping_data, mapping_filename = open_file(mapping_url, authorization)
    try:
        mapping_dict = yaml.safe_load(mapping_data)
    except yaml.YAMLError as e:
        raise HTTPException(
            status_code=422,
            detail=f"Could not read mapping file - is it valid YAML format? {str(e)}"
        ) from e

    duplicate_for_table = mapping_dict.get("use_template_rowwise", False)
    logging.info(f"use_template_rowwise: {duplicate_for_table}")

    # PHASE 0: If opt_data_url is provided, replace the original data source URL in YARRRML
    # This MUST happen BEFORE converting YARRRML to RML
    sources = mapping_dict.get("sources", {})
    if opt_data_url and sources:
        # Get the first source URL (the one we want to replace)
        first_source_name = next(iter(sources))
        original_data_url = sources[first_source_name]["access"].strip("/")
        
        # Replace ALL occurrences of the original data URL with the new one in the YARRRML string
        # This ensures the RML rules will have the correct URL from the start
        if isinstance(mapping_data, bytes):
            mapping_data_str = mapping_data.decode('utf-8')
        else:
            mapping_data_str = mapping_data
            
        # Replace the data URL in the YARRRML content
        mapping_data_str = mapping_data_str.replace(original_data_url, opt_data_url.strip("/"))
        mapping_data = mapping_data_str.encode('utf-8') if isinstance(mapping_data, bytes) else mapping_data_str
        
        # Re-parse the modified YAML to update mapping_dict
        mapping_dict = yaml.safe_load(mapping_data)
        sources = mapping_dict.get("sources", {})
        
        logging.info(f"Replaced data source URL in YARRRML: {original_data_url} -> {opt_data_url}")

    # PHASE 1: Download all source files using helper function
    url_mapping, primary_data_url, filename = download_sources(
        sources, opt_data_url, authorization
    )

    # Check if template prefix exists (optional feature)
    template_url = mapping_dict.get("prefixes", {}).get("template", None)

    # PHASE 2: Convert YARRRML to RML and replace all source URLs with placeholders
    rml_rules = convert_yarrrml_to_rml(mapping_data)
    rml_graph = Graph()
    rml_graph.parse(data=rml_rules, format="ttl")

    logging.debug(f"Replacing {len(url_mapping)} source URLs with placeholders")
    replace_all_data_sources(rml_graph, url_mapping)
    
    # Serialize RML rules
    rml_rules_new = rml_graph.serialize(format="ttl")
    
    # Add @base directive to RML rules so mapper uses correct base for data subjects
    # RDFLib serialize(base=...) doesn't actually inject @base, so we do it manually
    base_uri = mapping_dict.get("base", "")
    if base_uri:
        logging.info(f"Injecting @base <{base_uri}> directive into RML rules")
        # Inject @base after @prefix declarations
        lines = rml_rules_new.split('\n')
        # Find the last @prefix line
        last_prefix_idx = -1
        for idx, line in enumerate(lines):
            if line.strip().startswith('@prefix'):
                last_prefix_idx = idx
        
        # Insert @base after last @prefix
        if last_prefix_idx >= 0:
            lines.insert(last_prefix_idx + 1, f'@base <{base_uri}> .')
            rml_rules_new = '\n'.join(lines)
            logging.info(f"✓ @base directive injected successfully")
        else:
            # No @prefix found, add @base at the beginning
            rml_rules_new = f'@base <{base_uri}> .\n\n{rml_rules_new}'
            logging.info(f"✓ @base directive added at beginning")
    else:
        logging.warning("No base URI found in mapping, RML mapper will use default base")

    # PHASE 3: Process all data sources using helper function
    sources_for_mapper = {}
    data_graph = Graph()  # For primary data if RDF
    is_rdf_data = False
    data_namespaces = None

    for original_url, info in url_mapping.items():
        placeholder = info["placeholder"]
        actual_url = info["actual_url"]
        content = info["content"]

        # Use helper function to process data
        processed_content, is_rdf, data_namespaces = process_data_to_jsonld(content, actual_url)
        sources_for_mapper[placeholder] = processed_content

        # First source determines primary data graph and namespace
        if placeholder == "source_1.json":
            is_rdf_data = is_rdf
            if is_rdf:
                data_graph = Graph()
                data_graph.parse(data=content, format=guess_format(actual_url))

    # PHASE 4: Execute RML mapper using helper function
    logging.debug("="*80)
    logging.debug("DATA BEING SENT TO RML MAPPER:")
    logging.debug(f"is_rdf_data: {is_rdf_data}")
    logging.debug(f"Number of sources: {len(sources_for_mapper)}")
    logging.debug("="*80)

    res = execute_rml_mapper(rml_rules_new, sources_for_mapper)

    # Parse mapping results
    try:
        mapping_graph = Graph()
        mapping_graph.parse(data=res, format="ttl")
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail=f"Could not parse mapping results to result graph: {str(e)}"
        ) from e
    
    # POST-PROCESS 1: Replace http://example.com URIs with base URI from mapping
    base_uri = mapping_dict.get("base", "")
    if base_uri:
        mapping_graph = replace_base_uris(mapping_graph, base_uri)
    
    # POST-PROCESS 2: Fix string literal type declarations that should be URIRefs
    # The RML mapper sometimes outputs type declarations as string literals instead of URIRefs
    # We need to convert these back to proper URIRefs using our accumulated prefixes
    yarrrml_prefixes = mapping_dict.get("prefixes", {})
    triples_to_fix = []
    
    for s, p, o in mapping_graph:
        # Check if this is a type declaration with a string literal object
        if p == RDF.type and isinstance(o, Literal):
            o_str = str(o)
            # Check if it looks like a URN or URI that should be a URIRef
            if o_str.startswith("urn:") or o_str.startswith("http"):
                # Try to find matching prefix
                matched_prefix = None
                for prefix, ns_url in yarrrml_prefixes.items():
                    if o_str.startswith(ns_url):
                        # Extract local part and create prefixed version
                        local_part = o_str[len(ns_url):]
                        matched_prefix = f"{prefix}:{local_part}"
                        new_o = URIRef(o_str)
                        triples_to_fix.append(((s, p, o), (s, p, new_o)))
                        logging.info(f"Converting type string literal to URIRef: '{o_str}' -> {new_o}")
                        break
                
                # If no prefix matched, still convert to URIRef
                if not matched_prefix:
                    new_o = URIRef(o_str)
                    triples_to_fix.append(((s, p, o), (s, p, new_o)))
                    logging.info(f"Converting type string literal to URIRef (no prefix): '{o_str}' -> {new_o}")
    
    # Apply the fixes
    for (old_triple, new_triple) in triples_to_fix:
        mapping_graph.remove(old_triple)
        mapping_graph.add(new_triple)
    
    if triples_to_fix:
        logging.info(f"Fixed {len(triples_to_fix)} string literal type declarations")
    
    # Don't transform yet - join graphs first, then transform
    # mapping_graph.serialize('mapping_result.ttl')

    num_mappings_applied = len(mapping_graph)
    num_mappings_possible = count_rules_str(rml_rules)
    logging.info(
        "number of rules: {}, applied: {}".format(
            num_mappings_possible, num_mappings_applied
        )
    )
    joined_graph = Graph()
    
    
    # # Bind all custom prefixes from YARRRML mapping
    # custom_prefixes = mapping_dict.get("prefixes", {})
    # for prefix_name, prefix_url in custom_prefixes.items():
    #     # Skip 'base' as it's handled separately
    #     if prefix_name != "base":
    #         joined_graph.namespace_manager.bind(prefix_name, Namespace(prefix_url))
    #         logging.debug(f"Bound prefix '{prefix_name}' to '{prefix_url}'")

    # replace base url with place holder, should reference the now storage position of the resulting file
    # rdf_filename = "example.rdf"
    # new_base_url = ""

    ##add ontology entieties for reasoning
    # joined_graph.parse(CCO_URL, format='turtle')
    # joined_graph.parse(str(MSEO), format='xml')

    # Load template graph if template prefix is provided (optional feature)
    template_graph = None
    template_content = None
    
    if template_url:
        logging.info(f"📄 Template prefix found - loading template graph from: {template_url}")
        try:
            templatedata, template_filename = open_file(template_url, authorization)
            template_graph = Graph()
            template_graph.parse(data=templatedata, format="ttl")
            
            # STEP 1: Replace template namespace if it has base namespace
            base_namespace = None
            for ns_prefix, namespace in template_graph.namespaces():
                if ns_prefix in ["base", ""]:
                    base_namespace = namespace
            
            # Ensure template_url ends with /
            if not template_url.endswith("/"):
                template_url += "/"
            
            if base_namespace:
                logging.info(f"Replacing template base namespace {base_namespace} with {template_url}")
                template_content = template_graph.serialize().replace(
                    base_namespace, template_url
                )
                template_graph = Graph()
                template_graph.parse(data=template_content)
            else:
                template_content = template_graph.serialize()
            
            logging.info(f"✓ Template graph loaded successfully ({len(template_graph)} triples)")
        except Exception as e:
            logging.error(f"Failed to load template graph: {str(e)}")
            raise HTTPException(
                status_code=422,
                detail=f"Could not load template graph from {template_url}: {str(e)}",
            ) from e
    else:
        logging.info("ℹ️  No template prefix found in mapping - skipping template graph loading")
    
 
    # for subject in template_graph.subjects():
    #     # replace the subject URI with your new template URI
    #     new_iri=URIRef(str(subject).rsplit("/", 1)[-1].rsplit("#", 1)[-1])
    #     replace_iris(subject,new_iri,template_graph)
    # template_graph.serialize('template.ttl')

    # duplicate template if needed
    rows = list(data_graph[: RDF.type : CSVW.Row])

    # join and prepare for output
    # copy data entities into joined graph only if data was RDF
    # For plain JSON, RML mapper generates all the triples
    if is_rdf_data:
        joined_graph += data_graph
    # joined_graph += mapping_graph

    # use template to create new individuals for every row
    # This only works with RDF/CSVW data, not plain JSON
    if duplicate_for_table and is_rdf_data and rows and template_url and template_content:
        # map_content=mapping_graph.serialize()
        # mapping_graph.serialize("map_graph.ttl")
        # data_graph.serialize("data_graph.ttl")
        tablegroup = next(data_graph[: RDF.type : CSVW.TableGroup])
        column_maps = {}
        for column in data_graph[: RDF.type : CSVW.Column]:
            column_maps[column] = {
                "po": list(mapping_graph.predicate_objects(subject=column)),
                "propertyUrl": next(
                    data_graph.objects(subject=column, predicate=CSVW.propertyUrl),
                    column,
                ),
            }
        non_column_subjects = [
            subject
            for subject in mapping_graph.subjects(unique=True)
            if subject not in column_maps.keys()
        ]
        note_maps = {
            note: {"po": list(mapping_graph.predicate_objects(note))}
            for note in non_column_subjects
        }
        for_row_to_set = list()

        # adding tripples for columns
        print("column_map:{}".format(column_maps))
        for column, data in column_maps.items():
            print(column, data)
            property = data["propertyUrl"]
            for predicate, object in data["po"]:
                for_row_to_set.append(
                    (property, predicate, strip_namespace(str(object)))
                )
        print("to set for row: {}".format(for_row_to_set))

        # adding tripples for notes
        for_copy_to_set = list()
        for note, data in note_maps.items():
            for predicate, object in data["po"]:
                for_copy_to_set.append((note, predicate, strip_namespace(str(object))))

        # print(for_copy_to_set)
        logging.info("dublicating template graph for {} rows".format(len(rows)))
        for row in rows:
            data_node = data_graph.value(row, CSVW.describes)
            if template_url and template_content:
                joined_graph.parse(
                    data=template_content.replace(template_url, data_node + "/")
                )
            row_ns = Namespace(data_node + "/")
            joined_graph.bind("row" + str(data_node).rsplit("-", 1)[-1], row_ns)
            # set mapping realtions on each individual row
            for property, predicate, object in for_row_to_set:
                subject = next(joined_graph.objects(data_node, property), None)
                if subject:
                    joined_graph.add((subject, predicate, row_ns[object]))
            for subject, predicate, object in for_copy_to_set:
                joined_graph.add((subject, predicate, row_ns[object]))

    else:
        # Join graphs based on what's available
        if template_graph and template_content:
            # Parse template AS IS (don't replace namespace yet - it causes file:///src/ issue!)
            temp_template_graph = Graph()
            temp_template_graph.parse(data=template_content)
            joined_graph += temp_template_graph
        
        joined_graph += mapping_graph
        
        # Only add data_graph if the data source was RDF
        # For plain JSON, RML rules generate all needed triples
        if is_rdf_data:
            joined_graph += data_graph

    # DEBUG: Serialize after joining all graphs
    #joined_graph.serialize("debug_03_after_joining_graphs.ttl")
    logging.info("DEBUG: Serialized joined graph to debug_03_after_joining_graphs.ttl")

    # NAMESPACE ACCUMULATION STRATEGY:
    # Collect all namespaces BEFORE binding to avoid conflicts
    # Priority: mapping < template < @context < YARRRML (data_graph EXCLUDED - it loses @context!)
    logging.info("Accumulating namespaces from all sources...")

    accumulated_namespaces = {}

    # 1. From mapping graph (lowest priority)
    for prefix, namespace in mapping_graph.namespaces():
        if prefix not in ['', 'base']:
            accumulated_namespaces[prefix] = str(namespace)
            logging.debug(f"Accumulated from mapping: {prefix} -> {namespace}")

    # 2. From template graph (medium priority) - only if template was loaded
    if template_graph:
        for prefix, namespace in template_graph.namespaces():
            if prefix not in ['', 'base']:
                accumulated_namespaces[prefix] = str(namespace)
                logging.debug(f"Accumulated from template: {prefix} -> {namespace}")

    # 3. From JSON-LD @context if it was extracted (high priority for csv!)
    # This is the ORIGINAL csv namespace before any RDFLib parsing
    if data_namespaces:
        for prefix, namespace in data_namespaces.items():
            if prefix not in ['', 'base']:
                accumulated_namespaces[prefix] = str(namespace)
                logging.debug(f"Accumulated from @context: {prefix} -> {namespace}")

    # 4. From YARRRML prefixes dictionary (HIGHEST PRIORITY - preserves user intent!)
    # Extract prefixes directly from the mapping definition
    yarrrml_prefixes = mapping_dict.get("prefixes", {})
    for prefix, namespace in yarrrml_prefixes.items():
        # Skip special prefixes that have dedicated handling
        if prefix not in ['', 'base', 'template', 'method', 'data']:
            accumulated_namespaces[prefix] = str(namespace)
            logging.info(f"✓ Preserved YARRRML prefix: {prefix} -> {namespace}")

    logging.debug(accumulated_namespaces)
    logging.info(f"Total accumulated namespaces: {len(accumulated_namespaces)}")

    # Transform template namespace URIs to RELATIVE URIs (no scheme) - only if template was loaded
    if template_url:
        logging.info(f"Transforming template URIs from {template_url} to relative URIs")

        triples_to_transform = []
        for s, p, o in joined_graph:
            new_s = s
            new_p = p
            new_o = o
            changed = False

            # Transform subject if it starts with template URL
            if isinstance(s, URIRef) and str(s).startswith(template_url):
                local_part = str(s).replace(template_url, "")
                # Create relative URIRef (no scheme)
                new_s = URIRef("#" + local_part)
                changed = True
                logging.debug(f"Transform subject: {s} -> {new_s}")

            # Transform predicate if it starts with template URL
            if isinstance(p, URIRef) and str(p).startswith(template_url):
                local_part = str(p).replace(template_url, "")
                new_p = URIRef("#" + local_part)
                changed = True
                logging.debug(f"Transform predicate: {p} -> {new_p}")

            # Transform object if it's a URIRef and starts with template URL
            if isinstance(o, URIRef) and str(o).startswith(template_url):
                local_part = str(o).replace(template_url, "")
                new_o = URIRef("#" + local_part)
                changed = True
                logging.debug(f"Transform object: {o} -> {new_o}")

            if changed:
                triples_to_transform.append(((s, p, o), (new_s, new_p, new_o)))

        # Apply transformations
        for (old_triple, new_triple) in triples_to_transform:
            joined_graph.remove(old_triple)
            joined_graph.add(new_triple)

        logging.info(f"Transformed {len(triples_to_transform)} triples from template namespace to relative URIs")

    # Add provenance metadata using full API URL from request
    if api_url:
        full_api_url = api_url
    else:
        full_api_url = "/api/createrdf"

    used_resources = [str(mapping_url)]
    if template_url:
        used_resources.append(template_url)
    add_prov(joined_graph, full_api_url, primary_data_url, used_resources)
    logging.info(f"Added provenance metadata for data: {primary_data_url}, API: {full_api_url}")

    # APPLY ALL NAMESPACES ONCE - centralized binding right before serialization
    apply_all_namespaces(
        joined_graph,
        accumulated_namespaces,
        primary_data_url,
        template_url
    )

    # Serialize the graph - all prefixes now preserved
    out = joined_graph.serialize(format="turtle", base="")
    
    return filename, out, num_mappings_possible, num_mappings_applied


def shacl_validate(
    shapes_url: AnyUrl, rdf_url: AnyUrl, authorization=None
) -> Tuple[str, Graph]:
    if not len(urlparse(shapes_url)) == 6:  # not a regular url might be data string
        shapes_data = shapes_url
    else:
        shapes_data, filename = open_file(shapes_url, authorization)

    if not len(urlparse(rdf_url)) == 6:  # not a regular url might be data string
        rdf_data = rdf_url
    else:
        rdf_data, filename = open_file(rdf_url, authorization)

    # readin graphs
    try:
        shapes_graph = Graph()
        shapes_graph.parse(data=shapes_data, format=guess_format(shapes_data))
        rdf_graph = Graph()
        rdf_graph.parse(data=rdf_data, format=guess_format(rdf_data))
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail=f"Could not parse graph data file - probably could not guess format from URL string: {str(e)}",
        ) from e
    try:
        conforms, g, _ = validate(
            rdf_graph,
            shacl_graph=shapes_graph,
            ont_graph=None,  # can use a Web URL for a graph containing extra ontological information
            inference="none",
            abort_on_first=False,
            allow_infos=False,
            allow_warnings=False,
            meta_shacl=False,
            advanced=False,
            js=False,
            debug=False,
        )
        return conforms, g

    except Exception as e:
        logging.error(f"SHACL validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


class StartForm(StarletteForm):
    mapping_url = URLField(
        "URL Field Mapping",
        # validators=[WTFOptional()],
        description="Paste URL to a field mapping",
        render_kw={
            "class": "form-control",
            "placeholder": "https://github.com/Mat-O-Lab/MapToMethod/raw/main/examples/example-map.yaml",
        },
    )
    opt_data_csvw_url = URLField(
        "Optional: URL CSVW Json-LD",
        validators=[WTFOptional()],
        render_kw={"class": "form-control"},
        description="Paste URL to a CSVW Json-LD",
    )
    shacl_url = URLField(
        "URL SHACL Shape Repository",
        validators=[WTFOptional()],
        render_kw={"class": "form-control"},
        description="Paste URL to a SHACL Shape Repository",
    )
    opt_shacl_shape_url = URLField(
        "Optional: URL SHACL Shape",
        validators=[WTFOptional()],
        render_kw={"class": "form-control"},
        description="Paste URL to a SHACL Shape",
    )


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def index(request: Request):
    start_form = await StartForm.from_formdata(request)
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "start_form": start_form,
            "mapping_form": "",
            "result": "",
            "setting": setting,
        },
    )


@app.post("/convert", response_class=HTMLResponse, include_in_schema=False)
async def convert(request: Request):
    start_form = await StartForm.from_formdata(request)
    logging.info("start conversion")
    if await start_form.validate_on_submit():
        if not start_form.mapping_url.data:
            start_form.mapping_url.data = start_form.mapping_url.render_kw[
                "placeholder"
            ]
            flash(
                request,
                "URL Mapping File empty: using placeholder value for demonstration",
                "info",
            )
        mapping_url = start_form.mapping_url.data
        request.session["mapping_url"] = mapping_url

        opt_data_csvw_url = start_form.opt_data_csvw_url.data
        opt_shacl_shape_url = start_form.opt_shacl_shape_url.data

        try:
            filename, out, count_rules, count_rules_applied = apply_mapping(
                mapping_url, opt_data_csvw_url
            )

        except Exception as err:
            flash(request, err, "error")
            result = None
            payload = None
            filename = ""
        else:
            logging.info(f"POST /api/createrdf: {count_rules=}, {count_rules_applied=}")
            api_result = {
                "graph": out,
                "num_mappings_applied": count_rules_applied,
                "num_mappings_skipped": count_rules - count_rules_applied,
            }
            result = api_result["graph"]

            if start_form.opt_shacl_shape_url.data:
                conforms, graph = shacl_validate(opt_shacl_shape_url, out)
            b64 = base64.b64encode(result.encode())
            payload = b64.decode()

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "start_form": start_form,
            "filename": filename,
            "payload": payload,
            "result": result,
            "setting": setting,
        },
    )


class ReasonRequest(BaseModel):
    url: AnyUrl = Field("", title="Graph Url", description="Url to graph data to use.")

    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://kupferdigital.gitlab.io/process-graphs/vickers-hardness-test-fem/index.ttl"
            }
        }


class RMLRequest(BaseModel):
    mapping_url: AnyUrl = Field(
        "", title="Graph Url", description="Url to data metadata to use."
    )

    class Config:
        json_schema_extra = {
            "example": {
                "mapping_url": "https://github.com/Mat-O-Lab/MapToMethod/raw/main/examples/example-map.yaml"
            }
        }


class RDFRequest(BaseModel):
    mapping_url: AnyUrl = Field(
        "", title="Graph Url", description="Url to data metadata to use."
    )
    data_url: Optional[AnyUrl] = Field(
        "",
        title="Url Data Target",
        description="If given replaces the data target (csvw json-ld) url of the provided mapping.",
        omit_default=True,
    )

    class Config:
        json_schema_extra = {
            "example": {
                "mapping_url": "https://github.com/Mat-O-Lab/MapToMethod/raw/main/examples/example-map.yaml",
                "data_url": "https://raw.githubusercontent.com/Mat-O-Lab/CSVToCSVW/main/examples/example-metadata.json",
            }
        }


class RDFResponse(BaseModel):
    filename: str = Field(
        "data-joined.ttl",
        title="Resulting File Name",
        description="Suggested filename of the generated rdf in turtle format",
    )
    graph: str = Field(
        title="Graph data", description="The output gaph data in turtle format."
    )
    num_mappings_applied: int = Field(
        title="Number Rules Applied",
        description="The total number of rules that were applied from the mapping.",
    )
    num_mappings_skipped: int = Field(
        title="Number Rules Skipped",
        description="The total number of rules not applied once.",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "filename": "data-joined.ttl",
                "graph": "graph data in turtle format as string",
                "num_mappings_applied": 6,
                "num_mappings_skipped": 0,
            }
        }


class CheckResponse(BaseModel):
    rules_applicable: int = Field(
        title="Number Rules Applied",
        description="The total number of rules that were applied from the mapping.",
    )
    rules_skipped: int = Field(
        title="Number Rules Skipped",
        description="The total number of rules not applied once.",
    )

    # data_covered: float = Field(
    #     title="Percent Covered",
    #     description="Percent of data covered by rules.",
    # )
    class Config:
        json_schema_extra = {
            "example": {
                "rules_applicable": 6,
                "rules_skipped": 0,
            }
        }


class ValidateRequest(BaseModel):
    shapes_url: AnyUrl = Field(
        "", title="Shacle Shapes Url", description="Url to shacle shapes data to use."
    )
    rdf_url: AnyUrl = Field(
        "", title="RDF Url", description="Url to graph data to validate."
    )


class ValidateResponse(BaseModel):
    valid: str = Field(
        title="Shacle Report", description="Report resulting of shacle testing"
    )
    graph: str = Field(
        title="Graph data", description="The output gaph data in turtle format."
    )


class TurtleResponse(StreamingResponse):
    media_type = "text/turtle"


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(content={"message": exc.detail}, status_code=exc.status_code)


@app.post("/api/yarrrmltorml", response_class=TurtleResponse)
async def yarrrmltorml(request: RMLRequest) -> TurtleResponse:
    logging.info(f"POST /api/yarrrmltorml {request.mapping_url}")
    filedata, filename = open_file(str(request.mapping_url))

    rules = requests.post(YARRRML_URL, data={"yarrrml": filedata}).text
    data_bytes = BytesIO(rules.encode())
    filename = filename.rsplit(".yaml", 1)[0] + "-rml.ttl"
    headers = {
        "Content-Disposition": "attachment; filename={}".format(filename),
        "Access-Control-Expose-Headers": "Content-Disposition",
    }
    return TurtleResponse(content=data_bytes, headers=headers)


@app.post("/api/createrdf", response_model=RDFResponse)
def create_rdf(
    request: RDFRequest, req: Request, return_type: ReturnType = ReturnType.turtle
):
    authorization = req.headers.get("Authorization", None)
    
    # Get full API URL from request (same approach as CSVToCSVW)
    api_url = req.url._url
    
    logging.info(f"POST /api/createrdf {request.mapping_url}")
    filename, out, count_rules, count_rules_applied = apply_mapping(
        str(request.mapping_url), str(request.data_url), authorization, api_url
    )
    logging.info(f"POST /api/createrdf: {count_rules=}, {count_rules_applied=}")
    return {
        "filename": filename,
        "graph": out,
        "num_mappings_applied": count_rules_applied,
        "num_mappings_skipped": count_rules - count_rules_applied,
    }


@app.post("/api/checkmapping", response_model=CheckResponse)
async def checkmapping(request: RDFRequest, req: Request):
    logging.info(f"POST /api/checkmapping {request.mapping_url,request.data_url}")
    authorization = req.headers.get("Authorization", None)
    return check_mapping(request.mapping_url, request.data_url, authorization)


@app.post("/api/rdfvalidator", response_model=ValidateResponse)
def validate_rdf(request: ValidateRequest):
    conforms, graph = shacl_validate(str(request.shapes_url), str(request.rdf_url))
    logging.info(f"POST /api/rdfvalidator: {conforms=}")
    return {"valid": conforms, "graph": graph.serialize(format="ttl")}


@app.get("/info", response_model=settings.Setting)
async def info() -> dict:
    return setting


class RuleStatistics(BaseModel):
    rule_name: str = Field(title="Rule Name", description="Name of the mapping rule from YARRRML")
    predicate: Optional[str] = Field(None, title="Predicate", description="Main predicate URI used by this rule")
    triples_generated: int = Field(title="Triples Generated", description="Number of triples generated by this rule")
    subjects_affected: int = Field(title="Subjects Affected", description="Number of unique subjects this rule applied to")
    output: Optional[str] = Field(None, title="Rule Output", description="The RDF triples generated by this rule in Turtle format")


class TestMappingResult(BaseModel):
    success: bool = Field(
        title="Test Success",
        description="Whether the mapping test succeeded"
    )
    mapping_url: str = Field(
        title="Mapping URL",
        description="The URL of the mapping file tested"
    )
    data_url: Optional[str] = Field(
        None,
        title="Data URL",
        description="The URL of the data file used (if overridden)"
    )
    filename: Optional[str] = Field(
        None,
        title="Output Filename",
        description="The suggested filename for the output"
    )
    num_rules_total: int = Field(
        title="Total Rules",
        description="Total number of mapping rules defined"
    )
    num_rules_applied: int = Field(
        title="Rules Applied",
        description="Number of rules that successfully generated triples"
    )
    num_rules_skipped: int = Field(
        title="Rules Skipped",
        description="Number of rules that did not generate triples"
    )
    num_triples_generated: int = Field(
        title="Triples Generated",
        description="Total number of RDF triples generated"
    )
    rule_statistics: List[RuleStatistics] = Field(
        default_factory=list,
        title="Per-Rule Statistics",
        description="Detailed statistics for each mapping rule"
    )
    output_preview: Optional[str] = Field(
        None,
        title="Output Preview",
        description="First 1000 characters of the generated RDF output"
    )
    error: Optional[str] = Field(
        None,
        title="Error Message",
        description="Error message if the test failed"
    )
    logs: List[str] = Field(
        default_factory=list,
        title="Processing Logs",
        description="Log messages from the mapping process"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "mapping_url": "https://raw.githubusercontent.com/Mat-O-Lab/MapToMethod/refs/heads/main/examples/example-map.yaml",
                "data_url": None,
                "filename": "example-joined.ttl",
                "num_rules_total": 7,
                "num_rules_applied": 7,
                "num_rules_skipped": 0,
                "num_triples_generated": 42,
                "rule_statistics": [
                    {
                        "rule_name": "map_SpecimenID",
                        "predicate": "http://purl.obolibrary.org/obo/RO_0010002",
                        "triples_generated": 1,
                        "subjects_affected": 1
                    }
                ],
                "output_preview": "@prefix obo: <http://purl.obolibrary.org/obo/> ...",
                "error": None,
                "logs": [
                    "use_template_rowwise: false",
                    "Data is RDF, normalizing to JSON-LD",
                    "number of rules: 7, applied: 7"
                ]
            }
        }


@app.api_route("/api/test", methods=["POST"], response_model=TestMappingResult, tags=["transform"])
async def test_mapping(
    mapping_url: Optional[str] = None,
    data_url: Optional[str] = None
):
    """
    Test a mapping by executing it and returning detailed results
    
    This endpoint tests an RDF mapping by executing it and providing detailed
    statistics. You need to provide a mapping_url.
    
    Args:
        mapping_url: URL to the YARRRML mapping file to test
        data_url: Optional URL to override the data source specified in the mapping
    
    Returns:
        TestMappingResult: Detailed test results including statistics and logs
        
    Example:
        POST with mapping_url:
        {"mapping_url": "https://example.com/mapping.yaml"}
        
    """
    
    if not mapping_url:
        mapping_url = "https://raw.githubusercontent.com/Mat-O-Lab/MapToMethod/refs/heads/main/examples/example-map.yaml"
    
    # Capture logs
    log_capture = []
    
    class LogCapture(logging.Handler):
        def emit(self, record):
            try:
                msg = self.format(record)
                log_capture.append(msg)
            except Exception:
                pass
    
    # Add log capture handler with formatter
    log_handler = LogCapture()
    log_handler.setLevel(logging.DEBUG)  # Capture all levels
    formatter = logging.Formatter('%(levelname)s - %(name)s - %(message)s')
    log_handler.setFormatter(formatter)
    
    # Add to root logger to catch everything
    root_logger = logging.getLogger()
    original_level = root_logger.level
    root_logger.setLevel(logging.DEBUG)  # Temporarily lower threshold
    root_logger.addHandler(log_handler)
    
    try:
        # Load mapping data
        mapping_data, _ = open_file(mapping_url, None)
        mapping_source = mapping_url
            
        mapping_dict = yaml.safe_load(mapping_data)
        logging.info(f"Testing mapping from: {mapping_source}")
        
        # Execute the mapping via create_rdf since we have YAML content
        # We need to save it temporarily or use the apply_mapping function differently
        # For now, just execute via createrdf API
        
        # Get data URL from mapping or override
        sources = mapping_dict.get("sources", {})
        if sources:
            first_source_name = next(iter(sources))
            rml_data_url = sources[first_source_name]["access"].strip("/")
        else:
            raise HTTPException(status_code=422, detail="No sources found in mapping")
        
        test_data_url = data_url if data_url else rml_data_url
        
        # Use apply_mapping() to get properly post-processed results
        try:
            filename, output, num_rules, num_applied = apply_mapping(
                mapping_url, data_url, None, None
            )
            logging.info(f"Mapping executed: {num_rules} rules, {num_applied} triples generated")
            
        except Exception as e:
            logging.error(f"Error executing mapping: {str(e)}")
            raise
        
        # Parse the output to count total triples
        num_triples = 0
        try:
            result_graph = Graph()
            result_graph.parse(data=output, format="turtle")
            num_triples = len(result_graph)
        except Exception as e:
            logging.error(f"Error parsing result graph: {str(e)}")
        
        # Extract per-rule statistics from COMBINED output
        # This works because each rule creates triples with unique object URIs
        rule_stats = []
        mappings = mapping_dict.get("mappings", {})
        
        logging.info(f"Extracting per-rule statistics from combined output")
        
        try:
            # Parse combined output
            combined_graph = Graph()
            combined_graph.parse(data=output, format="turtle")
            
            # Analyze each rule
            for rule_name, rule_def in mappings.items():
                # Extract target object from rule definition
                po_list = rule_def.get("po", [])
                
                if not po_list:
                    logging.warning(f"Rule {rule_name}: No predicates/objects defined")
                    rule_stats.append({
                        "rule_name": rule_name,
                        "predicate": None,
                        "triples_generated": 0,
                        "subjects_affected": 0,
                        "output": None
                    })
                    continue
                
                # Handle both YARRRML formats:
                # 1. List format: [predicate, object]
                # 2. Dict format: {p: predicate, o: object}
                first_po = po_list[0]
                
                if isinstance(first_po, dict):
                    # Dict format
                    predicate_str = str(first_po.get('p', ''))
                    object_str = str(first_po.get('o', ''))
                elif isinstance(first_po, list) and len(first_po) >= 2:
                    # List format
                    predicate_str = str(first_po[0])
                    object_str = str(first_po[1])
                else:
                    logging.warning(f"Rule {rule_name}: Unknown po format: {first_po}")
                    rule_stats.append({
                        "rule_name": rule_name,
                        "predicate": None,
                        "triples_generated": 0,
                        "subjects_affected": 0,
                        "output": None
                    })
                    continue
                
                # Handle 'a' shorthand for rdf:type
                if predicate_str == 'a':
                    predicate_str = 'rdf:type'
                
                # Resolve predicate to full URI
                if ":" in predicate_str and not predicate_str.startswith("http"):
                    prefix, local = predicate_str.split(":", 1)
                    prefix_url = mapping_dict.get("prefixes", {}).get(prefix, "")
                    predicate_uri = prefix_url + local if prefix_url else predicate_str
                else:
                    predicate_uri = predicate_str
                
                # Resolve object to full URI (this is what makes each rule unique!)
                # The object is like "method:SpecimenID~iri"
                if ":" in object_str:
                    # Remove ~iri suffix if present
                    object_str_clean = object_str.split("~")[0]
                    if not object_str_clean.startswith("http"):
                        prefix, local = object_str_clean.split(":", 1)
                        prefix_url = mapping_dict.get("prefixes", {}).get(prefix, "")
                        object_uri = prefix_url + local if prefix_url else object_str_clean
                    else:
                        object_uri = object_str_clean
                else:
                    object_uri = object_str
                
                # The object becomes a RELATIVE URI like #SpecimenID in the output
                # So we need to match against that
                object_local = object_uri.split("/")[-1].split("#")[-1]
                
                logging.debug(f"Rule {rule_name}: Looking for object matching '{object_local}'")
                
                # Find triples in combined output where object ends with this local part
                matching_triples = []
                for s, p, o in combined_graph:
                    if isinstance(o, URIRef):
                        o_str = str(o)
                        # Check if object ends with the local part (handles both #SpecimenID and full URIs)
                        if o_str.endswith(object_local) or o_str.endswith("#" + object_local):
                            matching_triples.append((s, p, o))
                            logging.debug(f"  Matched triple: {s} -> {o}")
                
                triples_count = len(matching_triples)
                unique_subjects = len(set([s for s, p, o in matching_triples]))
                
                logging.info(f"Rule {rule_name}: {triples_count} triples, {unique_subjects} subjects (from combined output)")
                
                # Extract just these triples for the output
                if matching_triples:
                    rule_graph = Graph()
                    for triple in matching_triples:
                        rule_graph.add(triple)
                    rule_output = rule_graph.serialize(format="turtle")
                else:
                    rule_output = None
                
                rule_stats.append({
                    "rule_name": rule_name,
                    "predicate": predicate_uri,
                    "triples_generated": triples_count,
                    "subjects_affected": unique_subjects,
                    "output": rule_output
                })
                
        except Exception as e:
            logging.error(f"Error extracting per-rule statistics: {str(e)}")
            import traceback
            logging.error(traceback.format_exc())
            # Fallback: create empty stats
            for rule_name in mappings.keys():
                rule_stats.append({
                    "rule_name": rule_name,
                    "predicate": None,
                    "triples_generated": 0,
                    "subjects_affected": 0,
                    "output": None
                })
        
        # Remove the log handler and restore level
        root_logger.removeHandler(log_handler)
        root_logger.setLevel(original_level)
        
        # Calculate correct statistics from per-rule data
        num_rules_with_triples = sum(1 for rule in rule_stats if rule["triples_generated"] > 0)
        num_rules_without_triples = len(rule_stats) - num_rules_with_triples
        
        return {
            "success": True,
            "mapping_url": mapping_url,
            "data_url": data_url,
            "filename": filename,
            "num_rules_total": len(rule_stats),  # Total YARRRML mappings
            "num_rules_applied": num_rules_with_triples,  # Rules that generated triples
            "num_rules_skipped": num_rules_without_triples,  # Rules that didn't generate triples
            "num_triples_generated": num_triples,
            "rule_statistics": rule_stats,
            "output_preview": output[:1000] if output else None,
            "error": None,
            "logs": log_capture  # Return all captured logs
        }
        
    except HTTPException as e:
        root_logger.removeHandler(log_handler)
        root_logger.setLevel(original_level)
        return {
            "success": False,
            "mapping_url": mapping_url,
            "data_url": data_url,
            "filename": None,
            "num_rules_total": 0,
            "num_rules_applied": 0,
            "num_rules_skipped": 0,
            "num_triples_generated": 0,
            "output_preview": None,
            "error": f"{e.status_code}: {e.detail}",
            "logs": log_capture
        }
    except Exception as e:
        root_logger.removeHandler(log_handler)
        root_logger.setLevel(original_level)
        import traceback
        return {
            "success": False,
            "mapping_url": mapping_url,
            "data_url": data_url,
            "filename": None,
            "num_rules_total": 0,
            "num_rules_applied": 0,
            "num_rules_skipped": 0,
            "num_triples_generated": 0,
            "output_preview": None,
            "error": f"Error: {str(e)}\n{traceback.format_exc()}",
            "logs": log_capture
        }


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app_mode = os.environ.get("APP_MODE") or "production"
    with open("log_config.yml") as f:
        config = yaml.load(f, Loader=yaml.Loader)
        logging.config.dictConfig(config)
    if app_mode == "development":
        reload = True
        access_log = True
        config["root"]["level"] = "DEBUG"
    else:
        reload = False
        access_log = False
        config["root"]["level"] = "ERROR"
    logging.info("Log Level Set To {}".format(config["root"]["level"]))
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=port,
        reload=reload,
        access_log=access_log,
        log_config=config,
    )


def check_mapping(mapping_url, data_url, authorization=None):
    map_data, map_name = open_file(str(mapping_url), authorization)

    rules = yaml.safe_load(map_data)["mappings"]
    parameters = [rules[rule]["condition"]["parameters"] for rule in rules]
    use_template_rowwise = eval(
        yaml.safe_load(map_data).get("use_template_rowwise", "false").capitalize()
    )
    if use_template_rowwise:
        logging.debug("row wise temaplate duplicatin is set")
    lookups = [[item[0][1].strip("$()"), Literal(item[1][1])] for item in parameters]
    for item in lookups:
        if item[0] == "label":
            item[0] = RDFS.label
        elif item[0] == "name":
            item[0] = CSVW.name
    logging.debug(lookups)
    format = guess_format(str(data_url))
    if not format:
        raise HTTPException(
            status_code=400,
            detail="couldnt guess format of data from url {}".format(data_url),
        )

    data_str, filename = open_file(str(data_url), authorization)

    # logging.debug(data_str)
    data_graph = Graph()
    data_graph.parse(data=data_str, format=format)
    if use_template_rowwise:
        row_data_present = next(data_graph.subjects(RDF.type, CSVW.Row), None)
        if not row_data_present:
            # return zero rules applicable
            return {
                "rules_applicable": 0,
                "rules_skipped": 0,
            }
    found = 0
    for item in lookups:
        lookup = len(list(data_graph.subjects(item[0], item[1])))
        if lookup:
            found += 1
        else:
            print("lookup for rule {} unsuccessful".format(item))

    logging.info(
        "number of rules to test: {} rules with match: {}".format(len(lookups), found)
    )

    return {
        "rules_applicable": len(lookups),
        "rules_skipped": len(lookups) - found,
    }
