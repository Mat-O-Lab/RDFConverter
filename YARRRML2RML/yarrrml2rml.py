# dependencies related to rml conversion

import pretty_yarrrml2rml as yarrrml2rml
import yaml

# dependencies related to api
import json
from flask import Flask, request

app = Flask(__name__)


# we used pretty-yarrrml2rml lib, but since it has some errors
# in validation part, so we overridden this method to resolve
# the problem

@app.route('/rmlconversion', methods=['POST'])
def translate():
    print("------------------------START TRANSLATING YARRRML TO RML-------------------------------")

    yarrrml_data = yaml.safe_load(request.values['test'])

    print("yarrrm: ", yarrrml_data)

    list_initial_sources = yarrrml2rml.source_mod.get_initial_sources(yarrrml_data)
    rml_mapping = [yarrrml2rml.mapping_mod.add_prefix(yarrrml_data)]
    try:
        for mapping in yarrrml_data.get(yarrrml2rml.constants.YARRRML_MAPPINGS):
            #print('mapping: ', mapping )
            subject_list = yarrrml2rml.subject_mod.add_subject(yarrrml_data, mapping)
            source_list = yarrrml2rml.source_mod.add_source(yarrrml_data, mapping, list_initial_sources)
            pred = yarrrml2rml.predicate_object_mod.add_predicate_object_maps(yarrrml_data, mapping)
            it = 0
            for source in source_list:
                for subject in subject_list:
                    map_aux = yarrrml2rml.mapping_mod.add_mapping(mapping, it)
                    if type(source) is list:
                        rml_mapping.append(map_aux + source[0] + subject + pred + source[1])
                    else:
                        rml_mapping.append(map_aux + source + subject + pred)
                    rml_mapping[len(rml_mapping) - 1] = rml_mapping[len(rml_mapping) - 1][:-2]
                    rml_mapping.append(".\n\n\n")
                    it = it + 1

        #print("RML content successfully created!\n Starting the validation with RDFLib....")
        #print(rml_mapping)
        rml_mapping_string = "".join(rml_mapping)
        
    except Exception as e:
        #print("------------------------ERROR-------------------------------")
        #print("RML content not generated: " + str(e))
        return "Error Occured!", 500

    print("------------------------END TRANSLATION-------------------------------")

    return rml_mapping_string

#print(translate(yaml.safe_load(open("mapping.yml"))))
app.run()