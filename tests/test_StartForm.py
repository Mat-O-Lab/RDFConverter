import unittest
import requests
import yaml

class test_StartForm(unittest.TestCase):
    def test_translate(self):
        with open("./resources/config.yml", "r") as cfg:
            cfg = yaml.safe_load(cfg)

        yarrrml = open(cfg['rdfconverter']['unittest']['yarrrml2rml']['data']['input']).read()
        payload = {'yarrrml': yarrrml}
        rml_output = requests.post(cfg['rdfconverter']['unittest']['yarrrml2rml']['address']['host'] + ':' +
        cfg['rdfconverter']['unittest']['yarrrml2rml']['address']['port'] + '/' +
        cfg['rdfconverter']['unittest']['yarrrml2rml']['address']['contextroot'], payload)

        try:
            expected_output = open(cfg['rdfconverter']['unittest']['yarrrml2rml']['data']['expectedOutput']).read()            
            self.assertEqual(expected_output, rml_output.text)
            
        except Exception as e:
            print(str(e))
            self.assertRaises(e, msg=e.__cause__)

if __name__ == '__main__':
    unittest.main()