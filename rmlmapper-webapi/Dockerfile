FROM node:lts-alpine
RUN apk update && apk add curl python3 openjdk17-jre git jq
RUN rm -rf /var/cache/apk/*

RUN git clone https://github.com/RMLio/rmlmapper-webapi-js

WORKDIR /rmlmapper-webapi-js
#RUN npm install
RUN npm install --omit=dev
RUN wget https://github.com/RMLio/rmlmapper-java/releases/download/v6.2.1/rmlmapper-6.2.1-r368-all.jar -O /rmlmapper.jar
#RUN wget https://github.com/RMLio/rmlmapper-java/releases/download/v6.1.2/rmlmapper-6.1.2-r366-all.jar -O /rmlmapper.jar
COPY config.json ./

COPY entrypoint.sh ./
RUN ["chmod", "+x", "./entrypoint.sh"]
ENTRYPOINT ["./entrypoint.sh"]
