FROM docker.io/python:3.11.1-slim

RUN buildDeps='locales curl default-jre' \
    && set -x \
    && apt-get update && apt-get install -y $buildDeps --no-install-recommends \
    && sed -i 's/^# en_US.UTF-8 UTF-8$/en_US.UTF-8 UTF-8/g' /etc/locale.gen \
    && sed -i 's/^# de_DE.UTF-8 UTF-8$/de_DE.UTF-8 UTF-8/g' /etc/locale.gen \
    && locale-gen en_US.UTF-8 de_DE.UTF-8 \
    && update-locale LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt

ADD . /src
WORKDIR /src

ENV PYTHONDONTWRITEBYTECODE 1
# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED 1
ENTRYPOINT ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5000", "--workers", "6","--proxy-headers"]