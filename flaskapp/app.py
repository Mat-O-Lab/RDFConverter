
import imp
import os
import base64
from rdflib import Graph
import requests

from flask import Flask, flash, request, jsonify, render_template
from flask_swagger_ui import get_swaggerui_blueprint
from flask_wtf import FlaskForm
from flask_bootstrap import Bootstrap

from wtforms import URLField, SelectField
from wtforms.validators import DataRequired

from config import config

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


# old APi CSVToCSVW
"""
@app.route("/api", methods=["GET", "POST"])
def api():
    if request.method == "POST":
        content = request.get_json()
        annotator = CSV_Annotator(
            encoding=content['encoding'], separator=content['separator'])
        filename, file_data = annotator.process(content['data_url'])
    return jsonify({"filename": filename, "filedata": file_data})
"""

@app.route('/api/join_data', methods=['POST'])
def join_data():

    rdf_string = request.form['rdf']
    g = Graph()
    g.parse(data=rdf_string)

    source_query = """
    PREFIX rml: <http://semweb.mmlab.be/ns/rml#>
    SELECT DISTINCT ?source
    WHERE {
        ?mapSource rml:source ?source
    }"""
    res = g.query(source_query)

    # TODO: Give error if not exactly 2 rows returned

    source_1, source_2 = [row.source for row in g.query(source_query)]

    graph_from = Graph()
    graph_from.parse(data=requests.get(source_1).text, format='json-ld')

    graph_to = Graph()
    graph_to.parse(data=requests.get(source_2).text, format='json-ld')

    g += graph_from
    g += graph_to

    return g.serialize(format='ttl')
