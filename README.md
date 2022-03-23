# RDFConverter
[![Build](https://github.com/Mat-O-Lab/RDFConverter/actions/workflows/build.yml/badge.svg)](https://github.com/Mat-O-Lab/RDFConverter/actions/workflows/build.yml)  
It is a service for converting and validating YARRRML and Chowlk files to RDF, which is applied to Material Sciences Methods, for example, on Cement MSE experiments.
![RDFConverter_Concept drawio](https://user-images.githubusercontent.com/9248325/158355253-41fecd06-2487-449c-b91c-115182af9794.png)

## Input: A json file containing two URLs: 
-	yarrrml file (https://github.com/Mat-O-Lab/resources/blob/main/mappings/Zugversuch_eng_ETFE-Ref%252BGroesseneffekt2-map.yaml)
-	SHACL shapes (Optional)

An example of this json file is available [here](https://raw.githubusercontent.com/Mat-O-Lab/rdfconverter/main/resources/conf.json)
 
## Output: A string answering if the triples are successfully included on the triple store or not.

The RDF content is validated according to the constraints defined on the SHACL Shapes (If provided).
The validation will not occur on the RDF content from CHOWLk, because it does not contain instances to be validated.

Example of how to use the API/service on the web:

# Run flask app

```bash
docker-compose up
```

Go to http://localhost:5000/api/docs
