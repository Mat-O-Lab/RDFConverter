FROM python:3.9

WORKDIR /app

# first only copy requirements and install to optimize caching
COPY requirements.txt .

# hotfix install problems
#RUN pip3 install --no-deps pretty_yarrrml2rml
RUN pip3 install -r requirements.txt

COPY . .

CMD ["gunicorn", "-b", "0.0.0.0:5000", "wsgi:app", "--workers=3"]
