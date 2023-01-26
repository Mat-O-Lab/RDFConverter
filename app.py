from crypt import methods
from dataclasses import replace
from fileinput import filename
import os
from wsgiref.validate import validator
from rdflib import Graph, Namespace
from rdflib.util import guess_format
import requests
import yaml

from flask import Flask, flash, request, render_template, jsonify, make_response
from flask_swagger_ui import get_swaggerui_blueprint
from flask_wtf import FlaskForm
from flask_bootstrap import Bootstrap

from wtforms import URLField
from wtforms.validators import Optional
from pyshacl import validate

from config import config

from rmlmapper import replace_data_source, count_rules_str

config_name = os.environ.get("APP_MODE") or "development"
parser_port= os.environ.get('PARSER_PORT')
mapper_port= os.environ.get('MAPPER_PORT')

app = Flask(__name__)
app.config.from_object(config[config_name])

bootstrap = Bootstrap(app)

SWAGGER_URL = "/api/docs"
API_URL = "/static/swagger.json"
swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={
        "app_name": "RDFConverter"
    }
)

app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)

from urllib.request import urlopen
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

def open_file(uri=''):
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

class StartForm(FlaskForm):
    mapping_url = URLField(
        'URL Field Mapping',
        #validators=[Optional()],
        description='Paste URL to a field mapping',
        render_kw={"placeholder": "https://github.com/Mat-O-Lab/MapToMethod/raw/main/examples/example-map.yaml"}
        
    )
    opt_data_csvw_url = URLField(
        'Optional: URL CSVW Json-LD',
        validators=[Optional()],
        description='Paste URL to a CSVW Json-LD'
    )
    shacl_url = URLField(
        'URL SHACL Shape Repository',
        validators=[Optional()],
        description='Paste URL to a SHACL Shape Repository'
    )
    opt_shacl_shape_url = URLField(
        'Optional: URL SHACL Shape',
        validators=[Optional()],
        description='Paste URL to a SHACL Shape'
    )

@app.route('/', methods=['GET', 'POST'])
def index():    
    logo = './static/resources/MatOLab-Logo.svg'
    start_form = StartForm()
    message = ''
    result = ''
    conforms = None
        
    if request.method == 'POST' and start_form.validate():
        #mapping_url = request.values.get('mapping_url')
        #opt_data_csvw_url = request.values.get('opt_data_csvw_url')
        # shacl_url = request.values.get('shacl_url')
        opt_data_csvw_url=start_form.opt_data_csvw_url.data
  
        opt_shacl_shape_url = request.values.get('opt_shacl_shape_url')
        if not start_form.mapping_url.data:
            start_form.mapping_url.data=start_form.mapping_url.render_kw['placeholder']
            flash('Mapping url field empty: using placeholder value for demonstration','info')
        mapping_url=start_form.mapping_url.data

        try:
            out, count_rules, count_rules_applied=apply_mapping(mapping_url,opt_data_csvw_url)
        except Exception as err:
            flash(err,'error')
            result=None
        else:
            app.logger.info(f'POST /api/createrdf: {count_rules=}, {count_rules_applied=}')
            api_result = {'graph': out, 'num_mappings_applied': count_rules_applied, 'num_mappings_skipped': count_rules-count_rules_applied}
            result=api_result['graph']

            if start_form.opt_shacl_shape_url.data:
                conforms, graph = shacl_validate(opt_shacl_shape_url,out)


    return render_template(
        "index.html",
        logo=logo,
        start_form=start_form,
        message=message,
        result=result,
        conforms=conforms
        )

@app.route('/api/yarrrmltorml', methods=['POST'])
def translate():
    content = request.get_json()
    app.logger.info(f"POST /api/yarrrmltorml {content['url']}")
    filedata, filename = open_file(content['url'])
    rules = requests.post('http://yarrrml-parser'+':'+parser_port, data={'yarrrml': filedata}).text
    return rules

def apply_mapping(mapping_url,opt_data_url=None):
    mapping_data, mapping_filename = open_file(mapping_url)
    if not mapping_data:
            raise Exception('could not read mapping file - cant download file from url')
 
    try:
        mapping_dict = yaml.safe_load(mapping_data)
    except:
        raise Exception('could not read mapping file - cant readin yaml')
    try:
        rml_rules = requests.post('http://yarrrml-parser'+':'+parser_port, data={'yarrrml': mapping_data}).text
        rml_graph = Graph()
        rml_graph.parse(data=rml_rules, format='ttl')
    except:
        raise Exception('could not process rml')
    
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
    ##add ontology entieties for reasoning
    #joined_graph.parse(CCO_URL, format='turtle')
    #joined_graph.parse(str(MSEO), format='xml')
    
    #app.logger.info(f'POST /api/createrdf: {data_url}')
    #load and copy method graph and give it a new base namespace
    #app.logger.info(method_url)
    templatedata, methodname=open_file(method_url)
    if not templatedata:
            raise Exception('could not read method graph - cant download file from url')
    # replace base url with place holder, should reference the now storage position of the resulting file
    rdf_filename='example.rdf'
    new_base_url="https://your_filestorage_location/"+rdf_filename+'#'
    templatedata=templatedata.replace(method_url,new_base_url)
    res=res.replace(method_url,new_base_url)

    try:
        joined_graph.parse(data=templatedata, format='ttl')
    except:
        raise Exception('could not parse method graph to result graph')
    try:
        joined_graph.parse(data=res, format='ttl')
    except:
        raise Exception('could not join mapping results to result graph')
    
    #copy data entieties into joined graph
    data_graph=Graph()
    data_graph.namespace_manager.bind('data', Namespace('file:///app/'))
    
    try:
        data_graph.parse(data=data_content, format='json-ld')
        temp=data_graph.serialize(format="turtle")
        temp=temp.replace('file:///app/',data_url)
        data_graph=Graph()
        data_graph.parse(data=temp, format='turtle')
        joined_graph += data_graph
    except:
        raise Exception('could not join data entities to result graph')
    
    out=joined_graph.serialize(format="turtle")
    return out, num_mappings_possible, num_mappings_applied

@app.route('/api/createrdf', methods=['POST'])
def create_rdf():
    content = request.get_json()
    app.logger.info(f"POST /api/yarrrmltorml {content['mapping_url']}")
    try:
        out, count_rules, count_rules_applied=apply_mapping(content['mapping_url'])
    except Exception as err:
        return make_response(jsonify(str(err)), 400)
    app.logger.info(f'POST /api/createrdf: {count_rules=}, {count_rules_applied=}')
    return {'graph': out, 'num_mappings_applied': count_rules_applied, 'num_mappings_skipped': count_rules-count_rules_applied}

def shacl_validate(shapes_url,rdf_url):
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


@app.route('/api/rdfvalidator', methods=['POST'])
def validate_rdf():

    content = request.get_json()
    conforms, graph = shacl_validate(content['shapes_url'],content['rdf_url'])
    app.logger.info(f'POST /api/rdfvalidator: {conforms=}')
    return {'valid': conforms, 'graph': graph.serialize(format='ttl')}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=app.config["DEBUG"])
