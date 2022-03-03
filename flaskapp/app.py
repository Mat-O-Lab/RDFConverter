
from re import sub
import subprocess
import imp
import os
import base64
from rdflib import Graph
from rdflib.util import guess_format
import requests

from flask import Flask, flash, request, jsonify, render_template
from flask_swagger_ui import get_swaggerui_blueprint
from flask_wtf import FlaskForm
from flask_bootstrap import Bootstrap

from wtforms import URLField, SelectField
from wtforms.validators import DataRequired

from config import config

# dependencies related to rml conversion
import pretty_yarrrml2rml as yarrrml2rml
import yaml

from rmlmapper import find_data_source, find_method_graph, count_rules_str

config_name = os.environ.get("APP_MODE") or "development"

app = Flask(__name__)
app.config.from_object(config[config_name])

bootstrap = Bootstrap(app)

"""
SWAGGER_URL = "/api/docs"
API_URL = "/static/swagger.json"
swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={
        "app_name": "RDFConverter"
    }
)
"""

# app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)

class StartForm(FlaskForm):
    data_url = URLField(
        'URL Field Mapping',
        validators=[DataRequired()],
        description='Paste URL to a field mapping'
    )
    shacl_url = URLField(
        'URL SHACL Shape Repository',
        validators=[DataRequired()],
        description='Paste URL to a SHACL Shape Repository'
    )

@app.route('/', methods=['GET', 'POST'])
def index():
    logo = './static/resources/MatOLab-Logo.svg'
    concept = './static/resources/RDFConverter_Concept.drawio.svg'
    start_form = StartForm()
    message = ''
    result = ''
    return render_template(
        "index.html",
        logo=logo,
        concept=concept,
        start_form=start_form,
        message=message,
        result=result
        )


@app.route('/create_annotator', methods=['POST'])
def create_annotator():
    logo = './static/resources/MatOLab-Logo.svg'
    concept = './static/resources/RDFConverter_Concept.drawio.svg'
    start_form = StartForm()
    message = ''
    result = ''
    """
    if start_form.validate_on_submit():
        annotator = CSV_Annotator(
            separator=start_form.separator_sel.data,
            encoding=start_form.encoding_sel.data
        )
    """
    """
        try:
            meta_file_name, result = annotator.process(
                start_form.data_url.data)
        except (ValueError, TypeError) as error:
            flash(str(error))
        else:
            b64 = base64.b64encode(result.encode())
            payload = b64.decode()

            return render_template(
                "index.html",
                logo=logo,
                start_form=start_form,
                message=message,
                result=result,
                payload=payload,
                filename=meta_file_name
            )
    """
    return render_template(
        "index.html",
        logo=logo,
        concept=concept,
        start_form=start_form,
        message="message",
        result="seodprihgneropfdihgrs9ß<üpfhjgpdjfryig"
    )


@app.route('/api/yarrrmltorml', methods=['POST'])
def translate():
    print("------------------------START TRANSLATING YARRRML TO RML-------------------------------")

    yarrrml_data = yaml.safe_load(request.values['test'])

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

        print("RML content successfully created!\n Starting the validation with RDFLib....")
        print(rml_mapping)
        rml_mapping_string = "".join(rml_mapping)
        
    except Exception as e:
        print("------------------------ERROR-------------------------------")
        print("RML content not generated: " + str(e))
        return None

    print("------------------------END TRANSLATION-------------------------------")

    return rml_mapping_string

@app.route('/api/join_data', methods=['POST'])
def join_data():

    rml_url = request.form['rml_url']
    rml_rules = requests.get(rml_url).text
    
    data_url = find_data_source(rml_rules)
    method_url = find_method_graph(rml_rules)

    # replace data url from mappingfile with new data url specified in request
    if 'data_url' in request.form.keys():
        rml_rules.replace(data_url, request.form['data_url'])
        data_url = request.form['data_url']

    # call rmlmapper.jar to map rml to rdf
    sub_res = subprocess.run(
        ['java', '-jar', 'rmlmapper-4.15.0-r361-all.jar', '-m', rml_rules],
        text=True,
        capture_output=True,
        timeout=5
        )

    if sub_res.stderr:
        print(sub_res.stderr)
        return "Could not map rml to rdf!", 400

    data_graph = Graph()
    data_graph.parse(data_url, format=guess_format(data_url))
    method_graph = Graph()
    method_graph.parse(method_url, format=guess_format(method_url))

    mapping_graph = Graph()
    mapping_graph.parse(data=sub_res.stdout, format='ttl')

    num_mappings_applied = len(mapping_graph)
    num_mappings_possible = count_rules_str(rml_rules)

    mapping_graph += data_graph
    mapping_graph += method_graph

    return {'graph': mapping_graph.serialize(format='ttl'), 'num_mappings_applied': num_mappings_applied, 'num_mappings_skipped': num_mappings_possible-num_mappings_applied}
