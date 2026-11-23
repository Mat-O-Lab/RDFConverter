FROM docker.io/node:22-alpine AS build
WORKDIR /app
COPY package.json yarn.lock tsconfig.json ./
RUN yarn install --frozen-lockfile
COPY src ./src
# compile, then drop dev dependencies for the runtime image
RUN yarn build && yarn install --frozen-lockfile --production

FROM docker.io/node:22-alpine
# patch OS packages; npm/yarn/corepack are not needed at runtime and carry their own CVEs
RUN apk upgrade --no-cache \
    && rm -rf /usr/local/lib/node_modules /usr/local/bin/npm /usr/local/bin/npx \
              /usr/local/bin/corepack /usr/local/bin/yarn /usr/local/bin/yarnpkg /opt/yarn-*
WORKDIR /app
ENV NODE_ENV=production
COPY --from=build /app/package.json ./
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/bin ./bin
USER node
CMD ["node", "./bin/app.js"]
