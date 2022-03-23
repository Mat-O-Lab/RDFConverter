FROM python:3.8

WORKDIR /app

COPY . .

RUN pip3 install -r requirements.txt

CMD ["gunicorn", "-b", "0.0.0.0:5000", "wsgi:app", "--workers=3"]
