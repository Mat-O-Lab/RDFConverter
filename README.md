# RDFConverter
Conversion and validation of YARRRML and Chowlk files to RDF

## Input: A json file containing two URLs: 
-	yarrrml file (https://github.com/Mat-O-Lab/resources/blob/main/mappings/Zugversuch_eng_ETFE-Ref%252BGroesseneffekt2-map.yaml)
-	SHACL shapes (Optional)

An example of this json file is available [here](https://raw.githubusercontent.com/Mat-O-Lab/rdfconverter/main/resources/conf.json)
 
## Output: A string answering if the triples are successfully included on the triple store or not.

The RDF content is validated according to the constraints defined on the SHACL Shapes (If provided).
The validation will not occur on the RDF content from CHOWLk, because it does not contain instances to be validated.

It is a java service on the web to be deployed with tom-cat or another java servlet container.

Example of how to use the API/service on the web:

http://localhost:8080/rdfconv/conv?jsonfile=https://raw.githubusercontent.com/Mat-O-Lab/rdfconverter/main/resources/conf.json

# Flask app

```bash
cd flaskapp
```
```bash
docker-compose up
```

Go to http://localhost:5000
