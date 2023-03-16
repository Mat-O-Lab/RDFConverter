import os, re
from xmlrpc.client import Boolean
from rdflib import Graph, Namespace
from rdflib.util import guess_format
import yaml

import base64
import logging
import requests

import uvicorn
from pydantic import BaseSettings, BaseModel, AnyUrl, Field
from fastapi.middleware.cors import CORSMiddleware
from typing import Any, List, Optional, Tuple
from fastapi import Request, FastAPI, Body, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse


from starlette_wtf import StarletteForm
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware


from wtforms import URLField, BooleanField
from wtforms.validators import Optional as WTFOptional
from pyshacl import validate

from rmlmapper import replace_data_source, count_rules_str

parser_port= os.environ.get('PARSER_PORT')
mapper_port= os.environ.get('MAPPER_PORT')


class Settings(BaseSettings):
    app_name: str = "RDFConverter"
    admin_email: str = os.environ.get("ADMIN_MAIL") or "rdfconverter@matolab.org"
    items_per_user: int = 50
    version: str = "v1.0.3"
    config_name: str = os.environ.get("APP_MODE") or "development"
    openapi_url: str ="/api/openapi.json"
    docs_url: str = "/api/docs"
settings = Settings()

config_name = os.environ.get("APP_MODE") or "development"

middleware = [Middleware(SessionMiddleware, secret_key=os.getenv("APP_SECRET", "your-secret"))]
app = FastAPI(
    title=settings.app_name,
    description="It is a service for converting and validating YARRRML and Chowlk files to RDF, which is applied to Material Sciences Engineering (MSE) Methods, for example, on Cement MSE experiments.",
    version=settings.version,
    contact={"name": "Thomas Hanke, Mat-O-Lab", "url": "https://github.com/Mat-O-Lab", "email": settings.admin_email},
    license_info={
        "name": "Apache 2.0",
        "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
    },
    openapi_url=settings.openapi_url,
    docs_url=settings.docs_url,
    redoc_url=None,    
    #to disable highlighting for large output
    #swagger_ui_parameters= {'syntaxHighlight': False},
    middleware=middleware
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allows all origins
    allow_credentials=True,
    allow_methods=["*"], # Allows all methods
    allow_headers=["*"], # Allows all headers
)
app.add_middleware(uvicorn.middleware.proxy_headers.ProxyHeadersMiddleware, trusted_hosts="*")

app.mount("/static/", StaticFiles(directory='static', html=True), name="static")
templates= Jinja2Templates(directory="templates")


#flash integration flike flask flash
def flash(request: Request, message: Any, category: str = "info") -> None:
    if "_messages" not in request.session:
        request.session["_messages"] = []
    request.session["_messages"].append({"message": message, "category": category})

def get_flashed_messages(request: Request):
    return request.session.pop("_messages") if "_messages" in request.session else []

templates.env.globals['get_flashed_messages'] = get_flashed_messages


from urllib.parse import urlparse, unquote

OBO = Namespace('http://purl.obolibrary.org/obo/')
MSEO_URL = 'https://raw.githubusercontent.com/Mat-O-Lab/MSEO/main/MSEO_mid.owl'
CCO_URL = 'https://github.com/CommonCoreOntology/CommonCoreOntologies/raw/master/cco-merged/MergedAllCoreOntology-v1.3-2021-03-01.ttl'
MSEO = Namespace(MSEO_URL)
CCO = Namespace('http://www.ontologyrepository.com/CommonCoreOntologies/')
CSVW = Namespace('http://www.w3.org/ns/csvw#')
OA = Namespace('http://www.w3.org/ns/oa#')
QUDT = Namespace('http://qudt.org/schema/qudt/')
QUNIT = Namespace('http://qudt.org/vocab/unit/')

def replace_between(text: str, begin: str='', end: str='', alternative: str='') -> str:
    if not (begin and end):
        raise ValueError
    return re.sub(r'{}.*?{}'.format(re.escape(begin),re.escape(end)),alternative,text)
    
def open_file(uri: AnyUrl) -> Tuple[str,str]:
    try:
        uri_parsed = urlparse(uri)
    except:
        flash(uri+ ' is not an uri - if local file add file:// as prefix',"error")
        return None, None
    else:
        filename = unquote(uri_parsed.path).split('/')[-1]
        if uri_parsed.scheme in ['https', 'http']:
            filedata = requests.get(uri).text
        elif uri_parsed.scheme == 'file':
            filedata = open(unquote(uri_parsed.path), 'rb').read()
        else:
            flash('unknown scheme {}'.format(uri_parsed.scheme),"error")
            return None, None
        return filedata, filename

def apply_mapping(mapping_url: AnyUrl, opt_data_url: AnyUrl=None, duplicate_for_table: Boolean=False) -> Tuple[str,int,int]:
    mapping_data, mapping_filename = open_file(mapping_url)
    if not mapping_data:
            raise Exception('could not read mapping file - cant download file from url')
 
    try:
        mapping_dict = yaml.safe_load(mapping_data)
    except:
        raise Exception('could not read mapping file - cant readin yaml')
    
    rml_rules = requests.post('http://yarrrml-parser'+':'+parser_port, data={'yarrrml': mapping_data}).text
    rml_graph = Graph()
    rml_graph.parse(data=rml_rules, format='ttl')

    rml_data_url = mapping_dict['prefixes']['data']
    method_url = mapping_dict['prefixes']['method']

    # replace rml source from mappingfile with local file 
    # because rmlmapper webapi does not work with remote sources
    replace_data_source(rml_graph, 'source.json')

    rml_rules_new = rml_graph.serialize(format='ttl')

    # replace data_url with specified override

    if opt_data_url:
        rml_rules_new = rml_rules_new.replace(rml_data_url, opt_data_url)
        data_url =opt_data_url
    else:
        data_url=rml_data_url
    
    data_content, data_filename=open_file(data_url)
    if not data_content:
            raise Exception('could not read data meta file - cant download file from url')

    try:
        # call rmlmapper webapi
        d = {'rml': rml_rules_new, 'sources': {'source.json': data_content}, 'serialization': 'turtle'}
        r = requests.post('http://rmlmapper'+':'+mapper_port+'/execute', json=d)

        if r.status_code != 200:
            app.logger.error(r.text)
            return r.text, 400
        res = r.json()['output']
    except:
        raise Exception('could not execute mapping with rmlmapper')
    
    
    try:
        mapping_graph = Graph()
        mapping_graph.parse(data=res, format='ttl')
    except:
        raise Exception('could not pass mapping results to result graph')
    
    num_mappings_applied = len(mapping_graph)
    num_mappings_possible = count_rules_str(rml_rules)

    joined_graph = Graph()
    # set prefixes
    joined_graph.namespace_manager.bind('data', Namespace(data_url), override=True, replace=True)
    joined_graph.namespace_manager.bind('method', Namespace(method_url), override=True, replace=True)
    joined_graph.namespace_manager.bind('obo', OBO, override=True, replace=True)
    joined_graph.namespace_manager.bind('csvw', CSVW)
    joined_graph.namespace_manager.bind('oa', OA)
    joined_graph.namespace_manager.bind('qudt', QUDT)
    joined_graph.namespace_manager.bind('qunit', QUNIT)
    joined_graph.namespace_manager.bind('mseo', MSEO)
    joined_graph.namespace_manager.bind('cco', CCO)
    # replace base url with place holder, should reference the now storage position of the resulting file
    rdf_filename='example.rdf'
    new_base_url="https://your_filestorage_location/"+rdf_filename+'#'
    ##add ontology entieties for reasoning
    #joined_graph.parse(CCO_URL, format='turtle')
    #joined_graph.parse(str(MSEO), format='xml')
    
    #app.logger.info(f'POST /api/createrdf: {data_url}')
    #load and copy method graph and give it a new base namespace
    #app.logger.info(method_url)
    templatedata, methodname=open_file(method_url)
    if not templatedata:
            raise Exception('could not read method graph - cant download file from url')
    templatedata=templatedata.replace(method_url,new_base_url)
    print('replacing {} with {}'.format(method_url,new_base_url))
    
    #res=replace_between(res,begin=method_url,end='#',alternative=new_base_url)
    res=res.replace(method_url,new_base_url)
    try:
        joined_graph.parse(data=templatedata, format='ttl')
    except:
        raise Exception('could not parse method graph to result graph')
    try:
        joined_graph.parse(data=res, format='ttl')
    except:
        raise Exception('could not join mapping results to result graph')
    joined_graph.namespace_manager.bind('base', Namespace(new_base_url), override=True, replace=True)
    #copy data entieties into joined graph
    data_graph=Graph()
    data_graph.parse(data=data_content, format=guess_format(data_url))
    joined_graph += data_graph
    
    # data_graph=Graph()
    # data_graph.namespace_manager.bind('data', Namespace('file:///src/'))
    
    # try:
    #     data_graph.parse(data=data_content, format='json-ld')
    #     temp=data_graph.serialize(format="turtle")
    #     temp=temp.replace('file:///src/',data_url)
    #     data_graph=Graph()
    #     data_graph.parse(data=temp, format='turtle')
    #     joined_graph += data_graph
    # except:
    #     raise Exception('could not join data entities to result graph')
    
    out=joined_graph.serialize(format="turtle")
    return out, num_mappings_possible, num_mappings_applied

def shacl_validate(shapes_url: AnyUrl, rdf_url: AnyUrl) -> Tuple[str, Graph]:
    if not len(urlparse(shapes_url))==6: #not a regular url might be data string
        shapes_data=shapes_url
    else:
        shapes_data, filename = open_file(shapes_url)
    if not len(urlparse(rdf_url))==6: #not a regular url might be data string
        rdf_data=rdf_url
    else:
        rdf_data, filename = open_file(rdf_url)
    #readin graphs
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
            inference='none',
            abort_on_first=False,
            allow_infos=False,
            allow_warnings=False,
            meta_shacl=False,
            advanced=False,
            js=False,
            debug=False)
        return conforms, g

    except Exception as e:
        app.logger.error(e)
        return str(e), 400

class StartForm(StarletteForm):
    mapping_url = URLField(
        'URL Field Mapping',
        #validators=[WTFOptional()],
        description='Paste URL to a field mapping',
        render_kw={
            "class": "form-control",
            "placeholder": "https://github.com/Mat-O-Lab/MapToMethod/raw/main/examples/example-map.yaml"
            }
    )
    opt_data_csvw_url = URLField(
        'Optional: URL CSVW Json-LD',
        validators=[WTFOptional()],
        render_kw={"class":"form-control"},
        description='Paste URL to a CSVW Json-LD'
    )
    shacl_url = URLField(
        'URL SHACL Shape Repository',
        validators=[WTFOptional()],
        render_kw={"class":"form-control"},
        description='Paste URL to a SHACL Shape Repository'
    )
    opt_shacl_shape_url = URLField(
        'Optional: URL SHACL Shape',
        validators=[WTFOptional()],
        render_kw={"class":"form-control"},
        description='Paste URL to a SHACL Shape'
    )
    duplicate_for_table = BooleanField(
        'Duplicate Template for Table Data',
        render_kw={"class":"form-check form-check-input form-control-lg", "role":"switch"},
        description='If to duplicate the method template for each row in the table.',
        default=''
        )

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def index(request: Request):
    start_form = await StartForm.from_formdata(request)
    return templates.TemplateResponse("index.html",
        {"request": request,
        "start_form": start_form,
        "mapping_form": '',
        "result": ''
        }
    )

@app.post("/convert", response_class=HTMLResponse, include_in_schema=False)
async def convert(request: Request):
    start_form = await StartForm.from_formdata(request)
    logging.info('start conversion')
    if await start_form.validate_on_submit():
        if not start_form.mapping_url.data:
            start_form.mapping_url.data=start_form.mapping_url.render_kw['placeholder']
            flash(request,'URL Mapping File empty: using placeholder value for demonstration', 'info')
        mapping_url = start_form.mapping_url.data
        request.session['mapping_url']=mapping_url
        
        opt_data_csvw_url=start_form.opt_data_csvw_url.data
        opt_shacl_shape_url = start_form.opt_shacl_shape_url.data
        duplicate_for_table=start_form.duplicate_for_table.data
        try:
            out, count_rules, count_rules_applied=apply_mapping(mapping_url,opt_data_csvw_url,duplicate_for_table)
        except Exception as err:
            flash(request,err,'error')
            result=None
            payload=None
        else:
            logging.info(f'POST /api/createrdf: {count_rules=}, {count_rules_applied=}')
            api_result = {'graph': out, 'num_mappings_applied': count_rules_applied, 'num_mappings_skipped': count_rules-count_rules_applied}
            result=api_result['graph']
            
            if start_form.opt_shacl_shape_url.data:
                conforms, graph = shacl_validate(opt_shacl_shape_url,out)
            b64 = base64.b64encode(result.encode())
            payload = b64.decode()
        
        
    return templates.TemplateResponse("index.html",
        {"request": request,
        "start_form": start_form,
        "filename": "dataset.ttl",
        "payload": payload,
        "result": result
        }
    )

class RDFRequest(BaseModel):
    mapping_url: AnyUrl = Field('', title='Graph Url', description='Url to data metadata to use.')
    duplicate_for_table: Optional[bool] = Field(False, title='Duplicate Template for Table Data', description='If to duplicate the method template for each row in the table.', omit_default=True)
    

class RDFResponse(BaseModel):
    graph:  str = Field( title='Graph data', description='The output gaph data in turtle format.')
    num_mappings_applied: int = Field( title='Number Rules Applied', description='The total number of rules that were applied from the mapping.')
    num_mappings_skipped: int = Field( title='Number Rules Skipped', description='The total number of rules not applied once.')

class ValidateRequest(BaseModel):
    shapes_url: AnyUrl = Field('', title='Shacle Shapes Url', description='Url to shacle shapes data to use.')
    rdf_url: AnyUrl = Field('', title='RDF Url', description='Url to graph data to validate.')

class ValidateResponse(BaseModel):
    valid: str = Field( title='Shacle Report', description='Report resulting of shacle testing')
    graph:  str = Field( title='Graph data', description='The output gaph data in turtle format.')
    


@app.post('/api/yarrrmltorml')
def yarrrmltorml(request: RDFRequest = Body(
        examples={
            "normal": {
                "summary": "A simple yarrrmltorml example",
                "description": "Creates rml rules from yarrrml yaml.",
                "value": {
                    "mapping_url": "https://github.com/Mat-O-Lab/MapToMethod/raw/main/examples/example-map.yaml"
                    },
            },
        }
    )) -> str:
    logging.info(f"POST /api/yarrrmltorml {request.mapping_url}")
    filedata, filename = open_file(request.mapping_url)
    rules = requests.post('http://yarrrml-parser'+':'+parser_port, data={'yarrrml': filedata}).text
  
    return rules


@app.post('/api/createrdf', response_model=RDFResponse)
def create_rdf(request: RDFRequest = Body(
        examples={
            "normal": {
                "summary": "A simple yarrrmltorml example",
                "description": "Creates rml rules from yarrrml yaml.",
                "value": {
                    "mapping_url": "https://github.com/Mat-O-Lab/MapToMethod/raw/main/examples/example-map.yaml"
                    },
            },
        }
    )):
    logging.info(f"POST /api/yarrrmltorml {request.mapping_url}")
    #out, count_rules, count_rules_applied=apply_mapping(request.mapping_url)
    try:
        out, count_rules, count_rules_applied=apply_mapping(request.mapping_url)
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))
    logging.info(f'POST /api/createrdf: {count_rules=}, {count_rules_applied=}')
    return {'graph': out, 'num_mappings_applied': count_rules_applied, 'num_mappings_skipped': count_rules-count_rules_applied}


@app.post('/api/rdfvalidator', response_model=ValidateResponse)
def validate_rdf(request: ValidateRequest):
    conforms, graph = shacl_validate(request.shapes_url,request.rdf_url)
    logging.info(f'POST /api/rdfvalidator: {conforms=}')
    return {'valid': conforms, 'graph': graph.serialize(format='ttl')}

@app.get("/info", response_model=Settings)
async def info() -> dict:
    return settings

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app_mode=os.environ.get("APP_MODE") or 'production'
    with open('log_config.yml') as f:
        config = yaml.load(f,Loader=yaml.Loader)
        logging.config.dictConfig(config)
    if app_mode=='development':
        reload=True
        access_log=True
        config['root']['level']='DEBUG'
    else:
        reload=False
        access_log=False
        config['root']['level']='ERROR'
    print('Log Level Set To {}'.format(config['root']['level']))
    uvicorn.run("app:app",host="0.0.0.0",port=port, reload=reload, access_log=access_log,log_config=config)