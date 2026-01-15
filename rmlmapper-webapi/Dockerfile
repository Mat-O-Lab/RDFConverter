FROM node:22-alpine
RUN apk update && apk add curl python3 openjdk21-jre git jq openssh
RUN rm -rf /var/cache/apk/*


RUN git clone https://github.com/RMLio/rmlmapper-webapi-js

WORKDIR /rmlmapper-webapi-js
#RUN npm install
RUN npm install --omit=dev
RUN wget https://github.com/RMLio/rmlmapper-java/releases/download/v8.1.0/rmlmapper-8.1.0-r380-all.jar -O /rmlmapper.jar
COPY config.json ./

COPY entrypoint.sh ./
RUN ["chmod", "+x", "./entrypoint.sh"]
ENTRYPOINT ["./entrypoint.sh"]
