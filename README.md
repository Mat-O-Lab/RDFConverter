# RDFConverter [![Publish Docker image](https://github.com/Mat-O-Lab/RDFConverter/actions/workflows/PublishContainer.yml/badge.svg?branch=main&event=workflow_dispatch)](https://github.com/Mat-O-Lab/RDFConverter/actions/workflows/PublishContainer.yml) [![TestExamples](https://github.com/Mat-O-Lab/RDFConverter/actions/workflows/TestExamples.yml/badge.svg?branch=main)](https://github.com/Mat-O-Lab/RDFConverter/actions/workflows/TestExamples.yml)
Available online here: http://rdfconverter.matolab.org/

A service for joining and converting meta data documents based on YARRRML mapping files to RDF, optionally a validiation can be conducted using SHACL Shapes..

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
MAPPER_PORT=4000
YARRRML_URL=http://yarrrml-parser:${PARSER_PORT}
MAPPER_URL=http://rmlmapper:${MAPPER_PORT}
CONVERTER_PORT=6000
APP_PORT=5003
SSL_VERIFY=<True or False> #default is True
```

# Run flask app
```bash
docker-compose up
```

Go to http://localhost:5003/api/docs for a Simple UI

Try the api at http://localhost:5003/api/docs

# Acknowledgments
The authors would like to thank the Federal Government and the Heads of Government of the Länder for their funding and support within the framework of the [Platform Material Digital](https://www.materialdigital.de) consortium. Funded by the German [Federal Ministry of Education and Research (BMBF)](https://www.bmbf.de/bmbf/en/) through the [MaterialDigital](https://www.bmbf.de/SharedDocs/Publikationen/de/bmbf/5/31701_MaterialDigital.pdf?__blob=publicationFile&v=5) Call in Project [KupferDigital](https://www.materialdigital.de/project/1) - project id 13XP5119.
