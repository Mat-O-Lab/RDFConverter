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
from fastapi.responses import HTMLResponse, StreamingResponse
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
from wtforms import BooleanField, URLField
from wtforms.validators import Optional as WTFOptional

from rmlmapper import count_rules_str, replace_data_source, strip_namespace

parser_port = os.environ.get("PARSER_PORT")
mapper_port = os.environ.get("MAPPER_PORT")


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
    #contact={"name": setting.contact_name, "url": setting.org_site, "email": setting.admin_email},
    license_info={
        "name": "Apache 2.0",
        "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
    },
    openapi_url=setting.openapi_url,
    openapi_tags=tags_metadata,
    docs_url=setting.docs_url,
    redoc_url=None,
    swagger_ui_parameters= {'syntaxHighlight': False},
    #swagger_favicon_url="/static/resources/favicon.svg",
    middleware=middleware

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


def replace_between(
    text: str, begin: str = "", end: str = "", alternative: str = ""
) -> str:
    if not (begin and end):
        raise ValueError
    return re.sub(
        r"{}.*?{}".format(re.escape(begin), re.escape(end)), alternative, text
    )


def open_file(uri: AnyUrl) -> Tuple[str, str]:
    try:
        uri_parsed = urlparse(uri)
        # print(uri_parsed)

    except:
        flash(uri + " is not an uri - if local file add file:// as prefix", "error")
        return None, None
    else:
        filename = unquote(uri_parsed.path).rsplit("/download/upload")[0].split("/")[-1]
        if uri_parsed.scheme in ["https", "http"]:
            # r = urlopen(uri)
            r = requests.get(uri, allow_redirects=True)
            filedata = r.content
            # charset=r.info().get_content_charset()
            # if not charset:
            #     charset='utf-8'
            # filedata = r.read().decode(charset)
        elif uri_parsed.scheme == "file":
            filedata = open(unquote(uri_parsed.path), "rb").read()
        else:
            flash("unknown scheme {}".format(uri_parsed.scheme), "error")
            return None, None
        return filedata, filename

from datetime import datetime

def add_prov(graph: Graph, api_url: str, data_url: str, used: list = []) -> Graph:
    """ Add prov-o information to output graph

    Args:
        graph (Graph): Graph to add prov information to
        api_url (str): the api url 
        data_url (str): the url to the rdf file that was used

    Returns:
        Graph: Input Graph with prov metadata of the api call 
    """
    graph.bind('prov',PROV)
    
    root=BNode()
    api_node=URIRef(api_url)
    graph.add((root,PROV.wasGeneratedBy,api_node))
    graph.add((api_node,RDF.type,PROV.Activity))
    software_node=URIRef(setting.source+"/releases/tag/"+setting.version)
    graph.add((api_node,PROV.wasAssociatedWith,software_node))
    graph.add((software_node,RDF.type,PROV.SoftwareAgent))
    graph.add((software_node,RDFS.label,Literal( setting.name+setting.version)))
    graph.add((software_node,PROV.hadPrimarySource,URIRef(setting.source)))
    graph.add((root,PROV.generatedAtTime,Literal(str(datetime.now().isoformat()),datatype=XSD.dateTime)))
    entity=URIRef(str(data_url))
    graph.add((entity,RDF.type,PROV.Entity))
    derivation=BNode()
    graph.add((derivation,RDF.type,PROV.Derivation))
    graph.add((derivation,PROV.entity,entity))
    graph.add((derivation,PROV.hadActivity,api_node))
    graph.add((root,PROV.qualifiedDerivation,derivation))
    graph.add((root,PROV.wasDerivedFrom,entity))
    if used:
        [graph.add((api_node,PROV.wasInformedBy,URIRef(entry))) for entry in used]
    return graph


def apply_mapping(
    mapping_url: AnyUrl,
    opt_data_url: AnyUrl = None,
) -> Tuple[str, int, int]:
    mapping_data, mapping_filename = open_file(mapping_url)
    if not mapping_data:
        raise Exception("could not read mapping file - cant download file from url")
    try:
        mapping_dict = yaml.safe_load(mapping_data)
    except:
        raise Exception("could not read mapping file - cant readin yaml")
    duplicate_for_table=mapping_dict.get('use_template_rowwise',False)
    logging.info('use_template_rowwise: {}'.format(duplicate_for_table))
    rml_rules = requests.post(
        "http://yarrrml-parser" + ":" + parser_port, data={"yarrrml": mapping_data}
    ).text
    rml_graph = Graph()
    rml_graph.parse(data=rml_rules, format="ttl")
    # rml_graph.serialize('rml.ttl')

    #mapping_dict = yaml.safe_load(mapping_data)
    rml_data_url = mapping_dict["sources"]["data_entities"]["access"].strip("/")
    method_url = mapping_dict["prefixes"]["method"].strip("/")

    # replace rml source from mappingfile with local file
    # because rmlmapper webapi does not work with remote sources
    logging.debug("replace data_source {} with {}".format(rml_graph, "source.json"))
    replace_data_source(rml_graph, "source.json")
    rml_rules_new = rml_graph.serialize(format="ttl")

    # replace data_url with specified override
    if opt_data_url:
        data_url = opt_data_url
    else:
        data_url = rml_data_url
    data_content, data_filename = open_file(data_url)
    filename = data_filename.rsplit(".", 1)[0].rsplit("-", 1)[0] + "-joined.ttl"
    data_graph = Graph()
    logging.debug(
        "loading {} as data graph in {} format".format(data_url, guess_format(data_url))
    )
    # normalizing data to rdflib json-ld wih maon vocab csvw
    # data_graph.parse(data=data_content,format=guess_format(data_url))
    data_graph.parse(data_url, format=guess_format(data_url))
    context = {
        "@vocab": str(CSVW),
        "rdf": str(RDF),
        "qudt": str(QUDT),
        "qunit": str(QUNIT),
        "label": "http://www.w3.org/2000/01/rdf-schema#label",
        # "data1": data_url+'/',
        # "data2": rml_data_url+'/'
    }
    # data_graph.serialize('data.ttl')
    # data_graph.serialize('data.json',format='json-ld', context=context)
    data_content = data_graph.serialize(format="json-ld", context=context)
    # need to replace iris because they are changed to the document id

    if not data_content:
        raise Exception("could not read data meta file - cant download file from url")

    # if opt_data_url:
    # logging.debug('opt_data_url: replacing {} with {}'.format(rml_data_url,opt_data_url))
    # rml_rules_new = rml_rules_new.replace(rml_data_url, opt_data_url)

    d = {
        "rml": rml_rules_new,
        "sources": {"source.json": data_content},
        "serialization": "turtle",
    }
    # r = requests.post('http://rmlmapper'+':'+mapper_port+'/execute', json=d)
    # print(r.json())
    try:
        # call rmlmapper webapi
        r = requests.post("http://rmlmapper" + ":" + mapper_port + "/execute", json=d)

        if r.status_code != 200:
            app.logger.error(r.text)
            return r.text, 400
        res = r.json()["output"]
    except:
        raise Exception("could not execute mapping with rmlmapper")

    try:
        mapping_graph = Graph()
        mapping_graph.parse(data=res, format="ttl")
    except:
        raise Exception("could not pass mapping results to result graph")
    # mapping_graph.serialize('mapping_result.ttl')

    num_mappings_applied = len(mapping_graph)
    num_mappings_possible = count_rules_str(rml_rules)
    logging.info(
        "number of rules: {}, applied: {}".format(
            num_mappings_possible, num_mappings_applied
        )
    )
    joined_graph = Graph()
    # set prefixes
    joined_graph.namespace_manager.bind("obo", OBO, override=True, replace=True)
    joined_graph.namespace_manager.bind("csvw", CSVW)
    joined_graph.namespace_manager.bind("oa", OA)
    joined_graph.namespace_manager.bind("qudt", QUDT)
    joined_graph.namespace_manager.bind("qunit", QUNIT)
    joined_graph.namespace_manager.bind("iof", IOF)
    joined_graph.namespace_manager.bind("data", data_url + "/")

    # replace base url with place holder, should reference the now storage position of the resulting file
    rdf_filename = "example.rdf"
    new_base_url = ""

    ##add ontology entieties for reasoning
    # joined_graph.parse(CCO_URL, format='turtle')
    # joined_graph.parse(str(MSEO), format='xml')

    # app.logger.info(f'POST /api/createrdf: {data_url}')
    # load and copy method graph and give it a new base namespace
    logging.debug("loading method knowledge at {}".format(method_url))
    # print('method_url: '+method_url)
    templatedata, methodname = open_file(method_url)
    template_graph = Graph()
    # parse template and add mapping results
    template_graph.parse(data=templatedata, format="turtle")
    if not templatedata:
        raise Exception("could not read method graph - cant download file from url")
    try:
        template_graph.parse(data=templatedata, format="ttl")
    except:
        raise Exception("could not parse method graph to result graph")

    # remove the base iri or empty prefix if any
    template_namespace = "http://template_base/"
    base_namespace = None
    for ns_prefix, namespace in template_graph.namespaces():
        # print(ns_prefix,type(ns_prefix),len(ns_prefix))
        if ns_prefix in ["base", ""]:
            base_namespace = namespace
    if base_namespace:
        logging.debug(
            "found the following base or empty prefix namespace {}".format(
                base_namespace
            )
        )
        template_content = template_graph.serialize().replace(
            base_namespace, template_namespace
        )
        template_graph = Graph()
        template_graph.parse(data=template_content)
        template_graph.bind("data", data_url + "/")
    else:
        template_content = template_graph.serialize()

    # for subject in template_graph.subjects():
    #     # replace the subject URI with your new template URI
    #     new_iri=URIRef(str(subject).rsplit("/", 1)[-1].rsplit("#", 1)[-1])
    #     replace_iris(subject,new_iri,template_graph)
    #template_graph.serialize('template.ttl')

    # duplicate template if needed
    rows = list(data_graph[: RDF.type : CSVW.Row])

    # join and prepare for output
    joined_graph.namespace_manager.bind(
        "base", Namespace(new_base_url), override=True, replace=True
    )
    # copy data entieties into joined graph
    joined_graph += data_graph
    # joined_graph += mapping_graph

    # use template to create new idivituals for every
    if duplicate_for_table and rows:
        # map_content=mapping_graph.serialize()
        #mapping_graph.serialize('map_graph.ttl')
        tablegroup = next(data_graph[: RDF.type : CSVW.TableGroup])
        column_maps = {
            column: {
                "po": list(mapping_graph.predicate_objects(subject=column)),
                "propertyUrl": tablegroup + "/" + data_graph.value(column, CSVW.name),
            }
            for column in data_graph[: RDF.type : CSVW.Column]
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
        for column, data in column_maps.items():
            print(column,data)
            property = data["propertyUrl"]
            for predicate, object in data["po"]:
                for_row_to_set.append(
                    (property, predicate, strip_namespace(str(object)))
                )
        print(for_row_to_set)
        
        # adding tripples for notes
        for_copy_to_set = list()
        for note, data in note_maps.items():
            for predicate, object in data["po"]:
                for_copy_to_set.append((note, predicate, strip_namespace(str(object))))

        #print(for_copy_to_set)
        logging.info("dublicating template graph for {} rows".format(len(rows)))
        for row in rows:
            data_node = data_graph.value(row, CSVW.describes)
            joined_graph.parse(
                data=template_content.replace(template_namespace, data_node + "/")
            )
            row_ns = Namespace(data_node + "/")
            joined_graph.bind("row" + str(data_node).rsplit("-", 1)[-1], row_ns)
            # set mapping realtions on each individual row
            for property, predicate, object in for_row_to_set:
                subject = next(joined_graph.objects(data_node, property))
                joined_graph.add((subject, predicate, row_ns[object]))
            for subject, predicate, object in for_copy_to_set:
                joined_graph.add((subject, predicate, row_ns[object]))

    else:
        joined_graph += template_graph
        joined_graph += mapping_graph

    # joined_graph.serialize('joined.ttl')

    out = joined_graph.serialize(format="turtle")
    out = out.replace("file:///src", data_url)
    return filename, out, num_mappings_possible, num_mappings_applied


def shacl_validate(shapes_url: AnyUrl, rdf_url: AnyUrl) -> Tuple[str, Graph]:
    if not len(urlparse(shapes_url)) == 6:  # not a regular url might be data string
        shapes_data = shapes_url
    else:
        shapes_data, filename = open_file(shapes_url)
    if not len(urlparse(rdf_url)) == 6:  # not a regular url might be data string
        rdf_data = rdf_url
    else:
        rdf_data, filename = open_file(rdf_url)
    # readin graphs
    try:
        shapes_graph = Graph()
        shapes_graph.parse(data=shapes_data, format=guess_format(shapes_data))
        rdf_graph = Graph()
        rdf_graph.parse(data=rdf_data, format=guess_format(rdf_data))
    except Exception as e:
        app.logger.error(e)
        return "Could not read rdf data!", 400
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
        app.logger.error(e)
        return str(e), 400


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
            "setting": setting
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

        
        # out, count_rules, count_rules_applied=apply_mapping(mapping_url,opt_data_csvw_url,duplicate_for_table)
        try:
            filename, out, count_rules, count_rules_applied = apply_mapping(
                mapping_url, opt_data_csvw_url
            )

        except Exception as err:
            flash(request, err, "error")
            result = None
            payload = None
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
            "setting": setting
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
                "mapping_url": "https://github.com/Mat-O-Lab/MapToMethod/raw/main/examples/example-map.yaml"
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


@app.post("/api/yarrrmltorml", response_class=TurtleResponse)
async def yarrrmltorml(request: RMLRequest) -> TurtleResponse:
    logging.info(f"POST /api/yarrrmltorml {request.mapping_url}")
    filedata, filename = open_file(str(request.mapping_url))
    rules = requests.post(
        "http://yarrrml-parser" + ":" + parser_port, data={"yarrrml": filedata}
    ).text
    data_bytes = BytesIO(rules.encode())
    filename = filename.rsplit(".yaml", 1)[0] + "-rml.ttl"
    headers = {
        "Content-Disposition": "attachment; filename={}".format(filename),
        "Access-Control-Expose-Headers": "Content-Disposition",
    }
    return TurtleResponse(content=data_bytes, headers=headers)


@app.post("/api/createrdf", response_model=RDFResponse)
def create_rdf(request: RDFRequest):
    logging.info(f"POST /api/yarrrmltorml {request.mapping_url}")
    filename, out, count_rules, count_rules_applied = apply_mapping(
        str(request.mapping_url), str(request.data_url)
    )
    # try:
    #     out, count_rules, count_rules_applied=apply_mapping(request.mapping_url)
    # except Exception as err:
    #     raise HTTPException(status_code=500, detail=str(err))

    logging.info(f"POST /api/createrdf: {count_rules=}, {count_rules_applied=}")
    return {
        "filename": filename,
        "graph": out,
        "num_mappings_applied": count_rules_applied,
        "num_mappings_skipped": count_rules - count_rules_applied,
    }


@app.post("/api/rdfvalidator", response_model=ValidateResponse)
def validate_rdf(request: ValidateRequest):
    conforms, graph = shacl_validate(str(request.shapes_url), str(request.rdf_url))
    logging.info(f"POST /api/rdfvalidator: {conforms=}")
    return {"valid": conforms, "graph": graph.serialize(format="ttl")}


@app.get("/info", response_model=settings.Setting)
async def info() -> dict:
    return setting


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
