#!/bin/sh
# add port form env to config.json
echo $(cat config.json | jq '."baseURL" = "http://localhost:"+env.PORT') > config.json
cat ./config.json
./bin/cli.js