FROM node:17-alpine

# from timbru31/node-alpine-git
RUN apk -U upgrade \
  && apk add --no-cache \
    git \
    openssh

WORKDIR app

COPY ./yarrrml-parser/src/ ./src/
COPY ./yarrrml-parser/package.json ./yarrrml-parser/yarn.lock ./yarrrml-parser/tsconfig.json ./

RUN yarn install && yarn build

CMD ["yarn", "start"]
