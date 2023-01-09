FROM node:17-alpine

# from timbru31/node-alpine-git
RUN apk -U upgrade \
  && apk add --no-cache \
    git \
    openssh

WORKDIR app

COPY ./src/ ./src/
COPY ./package.json ./yarn.lock ./tsconfig.json ./

RUN yarn install && yarn build

CMD ["yarn", "start"]
