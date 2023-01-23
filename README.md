# RDFConverter [![Publish Docker image](https://github.com/Mat-O-Lab/RDFConverter/actions/workflows/PublishContainer.yml/badge.svg?branch=main&event=workflow_dispatch)](https://github.com/Mat-O-Lab/RDFConverter/actions/workflows/PublishContainer.yml) [![TestExamples](https://github.com/Mat-O-Lab/RDFConverter/actions/workflows/TestExamples.yml/badge.svg?branch=main)](https://github.com/Mat-O-Lab/RDFConverter/actions/workflows/TestExamples.yml)
Available online here: http://rdfconverter.matolab.org/

It is a service for converting and validating YARRRML and Chowlk files to RDF, which is applied to Material Sciences Engineering (MSE) Methods, for example, on Cement MSE experiments.

![RDFConverter_Concept drawio](https://user-images.githubusercontent.com/9248325/158355253-41fecd06-2487-449c-b91c-115182af9794.png)

## Requirements
- [Docker](https://www.docker.com/) should be running! - **IT'S MANDATORY!** 
  - Our RML parser also depends on another docker instance.

## Input: A json file containing two URLs: 
-	yarrrml file (https://github.com/Mat-O-Lab/resources/blob/main/mappings/Zugversuch_eng_ETFE-Ref%252BGroesseneffekt2-map.yaml)
-	SHACL shapes (Optional)

An example of this json file is available [here](https://raw.githubusercontent.com/Mat-O-Lab/rdfconverter/main/resources/conf.json)
 
## Output: A string answering if the triples are successfully included on the triple store or not.

The RDF content is validated according to the constraints defined on the SHACL Shapes (If provided).
The validation will not occur on the RDF content from CHOWLk, because it does not contain instances to be validated.

Example of how to use the API/service on the web:
# create a .env file with
```bash
PARSER_PORT=3001
APP_PORT=5003
MAPPER_PORT=4000
CONVERTER_PORT=6000
```

# Run flask app
```bash
docker-compose up
```

Go to http://localhost:5003/api/docs for a Simple UI

Try the api at http://localhost:5003/api/docs
