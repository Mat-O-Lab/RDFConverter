FROM python:3.8

WORKDIR /app

COPY . .

# from https://stackoverflow.com/a/44058196
# Install OpenJDK-8
RUN apt-get update && \
    apt-get install -y openjdk-8-jdk && \
    apt-get install -y ant && \
    apt-get clean;
    
# Fix certificate issues
RUN apt-get update && \
    apt-get install ca-certificates-java && \
    apt-get clean && \
    update-ca-certificates -f;

# Setup JAVA_HOME -- useful for docker commandline
ENV JAVA_HOME /usr/lib/jvm/java-8-openjdk-amd64/
RUN export JAVA_HOME

RUN pip3 install -r requirements.txt

CMD ["gunicorn", "-b", "0.0.0.0:5000", "wsgi:app", "--workers=3"]
