FROM timbru31/node-alpine-git

COPY src/ app/src/
COPY package.json yarn.lock tsconfig.json app/

WORKDIR app
RUN yarn install && yarn build

CMD ["yarn", "start"]
