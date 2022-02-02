## validate-rdf.yml

This action runs on each commit that changes .ttl files in validate/rdf or validate/shacl.  
If any files were changed or have been edited two steps are executed:

1. The docker-compose target 'app' is built, which contains the RDFConverter Servlet but does not also build the yarrrml-parser microservice.
2. For each file in validate/rdf and validate/shacl they are validated against each other. This is done via curl by POSTing both files to the validation endpoint of the servlet. 

If the validation of any two files produces an error the whole workflow immediately fails and returns the validation error as the output of the failed step.