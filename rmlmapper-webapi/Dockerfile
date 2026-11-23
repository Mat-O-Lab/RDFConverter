FROM docker.io/node:22-alpine AS build
RUN apk add --no-cache git

# pinned: rmlmapper-webapi-js v2.3.7
ARG WEBAPI_REF=671288e
RUN git clone https://github.com/RMLio/rmlmapper-webapi-js /rmlmapper-webapi-js \
    && git -C /rmlmapper-webapi-js checkout ${WEBAPI_REF}
WORKDIR /rmlmapper-webapi-js
# uuid is only used as v4() without a buffer by the java wrapper; override the vulnerable 9.x
RUN npm pkg set overrides.uuid='^11.1.1' \
    && npm install --omit=dev --ignore-scripts \
    && (npm audit fix --omit=dev || true) \
    && rm -rf .git

# pinned and verified: rmlmapper-java v8.1.0
ARG RMLMAPPER_SHA256=819371d49ca47d8ffddae0f34e95f38e8eaaf588ee023e3c2c7527a14d302f58
RUN wget -q https://github.com/RMLio/rmlmapper-java/releases/download/v8.1.0/rmlmapper-8.1.0-r380-all.jar -O /rmlmapper.jar \
    && echo "${RMLMAPPER_SHA256}  /rmlmapper.jar" | sha256sum -c -

FROM docker.io/node:22-alpine
# patch OS packages; npm/yarn/corepack are not needed at runtime and carry their own CVEs
RUN apk upgrade --no-cache \
    && apk add --no-cache openjdk21-jre-headless jq \
    && rm -rf /usr/local/lib/node_modules /usr/local/bin/npm /usr/local/bin/npx \
              /usr/local/bin/corepack /usr/local/bin/yarn /usr/local/bin/yarnpkg /opt/yarn-*

COPY --from=build /rmlmapper-webapi-js /rmlmapper-webapi-js
COPY --from=build /rmlmapper.jar /rmlmapper.jar
WORKDIR /rmlmapper-webapi-js
COPY config.json entrypoint.sh ./
# entrypoint rewrites config.json, so the runtime user must own it
RUN chmod +x ./entrypoint.sh && chown -R node:node /rmlmapper-webapi-js
USER node
ENTRYPOINT ["./entrypoint.sh"]
