FROM python:3.9

COPY requirements.txt .
RUN buildDeps='apt-utils gcc g++' \
    && set -x \
    && apt-get update && apt-get install -y $buildDeps --no-install-recommends \
    && rm -rf /var/lib/apt/lists/* \
    && python - m pip install – upgrade pip \
    && pip3 install -r requirements.txt \
    && apt-get purge -y --auto-remove $buildDeps

ADD . /src
WORKDIR /src

ENV PYTHONDONTWRITEBYTECODE 1
# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED 1
ENTRYPOINT ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5000", "--workers", "6","--proxy-headers"]
