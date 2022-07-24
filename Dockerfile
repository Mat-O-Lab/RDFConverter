FROM python:3.8

WORKDIR /app

RUN git clone https://github.com/Mat-O-Lab/RDFConverter.git /app
RUN pip install -r /app/requirements.txt
WORKDIR /app

CMD ["gunicorn", "-b", "0.0.0.0:5000", "wsgi:app", "--workers=3"]
