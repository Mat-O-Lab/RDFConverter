FROM docker.io/python:3.13-alpine

RUN apk upgrade --no-cache && apk add --no-cache curl

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip "urllib3>=2.8.0" -r requirements.txt \
    && pip uninstall -y setuptools wheel \
    && python -m pip uninstall -y pip


ADD . /src
WORKDIR /src

ENV PYTHONDONTWRITEBYTECODE 1
# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED 1
ENTRYPOINT ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5000", "--workers", "6","--proxy-headers"]