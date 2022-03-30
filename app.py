
from re import sub
import subprocess
import imp
import os
import base64
from html5lib import serialize
from rdflib import Graph
from rdflib.util import guess_format
import requests

from flask import Flask, flash, request, jsonify, render_template
from flask_swagger_ui import get_swaggerui_blueprint
from flask_wtf import FlaskForm
from flask_bootstrap import Bootstrap

from wtforms import URLField, SelectField
from wtforms.validators import DataRequired, Optional
from pyshacl import validate


from config import config

# dependencies related to rml conversion
import pretty_yarrrml2rml as yarrrml2rml
import yaml

from rmlmapper import find_data_source, find_method_graph, count_rules_str

config_name = os.environ.get("APP_MODE") or "development"

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

class StartForm(FlaskForm):
    data_url = URLField(
        'URL Field Mapping',
        validators=[Optional()],
        description='Paste URL to a field mapping'
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
    
    if request.method == 'POST' and start_form.validate():
        data_url = bool(request.values.get('data_url'))
        opt_data_csvw_url = bool(request.values.get('opt_data_csvw_url'))
        shacl_url = bool(request.values.get('shacl_url'))
        opt_shacl_shape_url = bool(request.values.get('opt_shacl_shape_url'))
        if ((data_url ^ opt_data_csvw_url) and (shacl_url ^ opt_shacl_shape_url)) or ((data_url ^ opt_data_csvw_url) and not shacl_url and not opt_shacl_shape_url):
            result = "Result"
        else:
            if not data_url ^ opt_data_csvw_url:
                msg = 'One Mapping URL field must be set'
                flash(msg)
            if shacl_url and opt_shacl_shape_url:
                msg = 'Only one SHACL URL field can be set'
                flash(msg)

    return render_template(
        "index.html",
        logo=logo,
        start_form=start_form,
        message=message,
        result=result
        )

@app.route('/api/yarrrmltorml', methods=['POST'])
def translate():
    print("------------------------START TRANSLATING YARRRML TO RML-------------------------------")

    yarrrml_data = yaml.safe_load(request.values['yarrrml'])

    list_initial_sources = yarrrml2rml.source_mod.get_initial_sources(yarrrml_data)
    rml_mapping = [yarrrml2rml.mapping_mod.add_prefix(yarrrml_data)]
    try:
        for mapping in yarrrml_data.get(yarrrml2rml.constants.YARRRML_MAPPINGS):
            subject_list = yarrrml2rml.subject_mod.add_subject(yarrrml_data, mapping)
            source_list = yarrrml2rml.source_mod.add_source(yarrrml_data, mapping, list_initial_sources)
            pred = yarrrml2rml.predicate_object_mod.add_predicate_object_maps(yarrrml_data, mapping)
            it = 0
            for source in source_list:
                for subject in subject_list:
                    map_aux = yarrrml2rml.mapping_mod.add_mapping(mapping, it)
                    if type(source) is list:
                        rml_mapping.append(map_aux + source[0] + subject + pred + source[1])
                    else:
                        rml_mapping.append(map_aux + source + subject + pred)
                    rml_mapping[len(rml_mapping) - 1] = rml_mapping[len(rml_mapping) - 1][:-2]
                    rml_mapping.append(".\n\n\n")
                    it = it + 1

        print("RML content successfully created!")
        print(rml_mapping)
        rml_mapping_string = "".join(rml_mapping)
        
    except Exception as e:
        print("------------------------ERROR-------------------------------")
        print("RML content not generated: " + str(e))
        return "Error Occured!", 500

    print("------------------------END TRANSLATION-------------------------------")

    return rml_mapping_string

@app.route('/api/joindata', methods=['POST'])
def join_data():

    rml_url = request.form.get('rml_url', None)
    rml_rules: str = requests.get(rml_url).text if rml_url else request.form['rml_data']
    
    data_url = find_data_source(rml_rules)
    method_url = find_method_graph(rml_rules)

    # replace all urls in data with new spec
    if 'data_url' in request.form.keys():
        rml_rules = rml_rules.replace(data_url, request.form['data_url'])
        data_url = request.form['data_url']

    # replace rml source from mappingfile with local file 
    # because rmlmapper webapi does not work with remote sources
    rml_rules = rml_rules.replace(f'rml:source "{data_url}"', 'rml:source "source.json"')

    # call rmlmapper webapi
    d = {'rml': rml_rules, 'sources': {'source.json': requests.get(data_url).text}, 'serialization': 'turtle'}
    r = requests.post('http://rmlmapper:4000/execute', json=d)

    if r.status_code != 200:
        print(r.text)
        return r.text, 400
    res = r.json()['output']
    
    data_graph = Graph()
    data_graph.parse(data_url, format=guess_format(data_url))
    method_graph = Graph()
    method_graph.parse(method_url, format=guess_format(method_url))

    mapping_graph = Graph()
    mapping_graph.parse(data=res, format='ttl')

    num_mappings_applied = len(mapping_graph)
    num_mappings_possible = count_rules_str(rml_rules)

    mapping_graph += data_graph
    mapping_graph += method_graph

    return {'graph': mapping_graph.serialize(format='ttl'), 'num_mappings_applied': num_mappings_applied, 'num_mappings_skipped': num_mappings_possible-num_mappings_applied}

@app.route('/api/rdfvalidator', methods=['POST'])
def validate_rdf():

    try:
        shapes_url = request.form.get('shapes_url', None)
        shapes_data = requests.get(shapes_url).text if shapes_url else request.form['shapes_data']
        rdf_url = request.form.get('rdf_url', None)
        rdf_data = requests.get(rdf_url).text if rdf_url else request.form['rdf_data']

        shapes_graph = Graph()
        shapes_graph.parse(data=shapes_data, format=guess_format(shapes_url) if shapes_url else 'ttl')
        rdf_graph = Graph()
        rdf_graph.parse(data=rdf_data, format=guess_format(rdf_url) if rdf_url else 'ttl')
    except:
        return "Could not read graph!", 400

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

    except Exception as e:
        return str(e), 400

    return {'valid': conforms, 'graph': g.serialize(format='ttl')}
