#!/bin/sh
mkdir -p reports
npx -y newman run books-api.postman_collection.json \
  -e postman/local.postman_environment.json \
  -r cli,junit --reporter-junit-export reports/junit.xml
