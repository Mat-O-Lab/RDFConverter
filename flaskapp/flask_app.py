
import os
import base64

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
"""
app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)
separators = ["auto", ";", ",", "\\t", "\\t+",
              "|", "\s+", "\s+|\\t+|\s+\\t+|\\t+\s+"]
encodings = ['auto', 'ISO-8859-1', 'UTF-8', 'ascii', 'latin-1', 'cp273']
"""
"""
class StartForm(FlaskForm):
    data_url = URLField(
        'URL Meta Data',
        validators=[DataRequired()],
        description='Paste URL to a data file, e.g. csv, TRA'
    )
    separator_sel = SelectField(
        'Choose Separator, default: auto detect',
        choices=separators,
        description='select a separator for your data manually',
        default='auto'
        )
    encoding_sel = SelectField(
        'Choose Encoding, default: auto detect',
        choices=encodings,
        description='select an encoding for your data manually',
        default='auto'
        )
"""

@app.route('/', methods=['GET', 'POST'])
def index():
    logo = './static/resources/MatOLab-Logo.svg'
    concept = './static/resources/RDFConverter_Concept.drawio.svg'
    #start_form = StartForm()
    message = ''
    result = ''
    return render_template(
        "index.html",
        logo=logo,
        concept=concept,
        #start_form=start_form,
        message=message,
        result=result
        )

"""
@app.route('/create_annotator', methods=['POST'])
def create_annotator():
    logo = './static/resources/MatOLab-Logo.svg'
    start_form = StartForm()
    message = ''
    result = ''

    if start_form.validate_on_submit():
        annotator = CSV_Annotator(
            separator=start_form.separator_sel.data,
            encoding=start_form.encoding_sel.data
        )

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
    return render_template(
        "index.html",
        logo=logo,
        start_form=start_form,
        message=message,
        result=result
    )
"""

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