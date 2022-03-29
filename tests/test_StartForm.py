import unittest
import requests
import yaml
import rdflib
from rdflib.compare import to_isomorphic, graph_diff

def generate_joined_data() -> str:
    pass

with open('./resources/config.yml', 'r') as f:
    CFG = yaml.safe_load(f)

ENDPOINT = CFG['rdfconverter']['unittest']['location']['host'] + ':' + CFG['rdfconverter']['unittest']['location']['port'] + '/'

class test_StartForm(unittest.TestCase):
    def test_translate(self):
        with open(CFG['rdfconverter']['unittest']['yarrrml2rml']['data']['input'], 'r') as f:
            yarrrml = f.read()
        payload = {'yarrrml': yarrrml}
        rml_output = requests.post(ENDPOINT + CFG['rdfconverter']['unittest']['yarrrml2rml']['contextroot'], payload)

        try:
            with open(CFG['rdfconverter']['unittest']['yarrrml2rml']['data']['expectedOutput'], 'r') as f:
                expected_output = f.read()            
            self.assertEqual(expected_output, rml_output.text)
            
        except Exception as e:
            print(str(e))
            self.assertRaises(e, msg=e.__cause__)

    def test_joindata_works(self):
        with open(CFG['rdfconverter']['unittest']['joindata']['data']['test1']['input'], 'r') as f:
            rml_input = f.read()
        payload = {'rml_url': rml}
        res = requests.post(ENDPOINT + CFG['rdfconverter']['unittest']['joindata']['contextroot'])



        

    

if __name__ == '__main__':
    unittest.main()