import unittest
import urllib

import requests
import yaml
from rdflib import Graph
from rdflib.compare import graph_diff, to_isomorphic

with open("./resources/config.yml", "r") as f:
    CFG = yaml.safe_load(f)

ENDPOINT = (
    CFG["rdfconverter"]["unittest"]["location"]["host"]
    + ":"
    + CFG["rdfconverter"]["unittest"]["location"]["port"]
    + "/"
)


class test_StartForm(unittest.TestCase):
    def test_translate(self):
        payload = {
            "url": CFG["rdfconverter"]["unittest"]["yarrrml2rml"]["data"]["input"]
        }
        rml_output = requests.post(
            ENDPOINT + CFG["rdfconverter"]["unittest"]["yarrrml2rml"]["contextroot"],
            json=payload,
        )
        with open(
            CFG["rdfconverter"]["unittest"]["yarrrml2rml"]["data"]["expectedOutput"],
            "r",
        ) as f:
            expected_output = f.read()
        g_gen = Graph()
        g_expect = Graph()
        g_gen.parse(data=rml_output.text)
        g_expect.parse(data=expected_output)

        iso1 = to_isomorphic(g_gen)
        iso2 = to_isomorphic(g_expect)

        _, in_first, in_second = graph_diff(iso1, iso2)
        self.assertEqual([len(in_first), len(in_second)], [0, 0])

    def test_joindata(self):
        payload = {
            "rml_url": CFG["rdfconverter"]["unittest"]["joindata"]["data"]["test1"][
                "input"
            ],
            "minimal": True,
        }
        res = requests.post(
            ENDPOINT + CFG["rdfconverter"]["unittest"]["joindata"]["contextroot"],
            json=payload,
        )
        res_graph = Graph()
        res_graph.parse(data=res.json()["graph"], format="ttl")

        expectation = requests.get(
            CFG["rdfconverter"]["unittest"]["joindata"]["data"]["test1"][
                "expectedOutput"
            ]
        )
        expect_graph = Graph()
        expect_graph.parse(data=expectation.text, format="ttl")

        # canonicalize both graphs
        iso1 = to_isomorphic(res_graph)
        iso2 = to_isomorphic(expect_graph)

        _, in_first, in_second = graph_diff(iso1, iso2)

        # all nodes of the second graph are included in both graphs
        self.assertEqual(len(in_second), 0)

    def test_joindata_with_data_url(self):
        payload = {
            "rml_url": CFG["rdfconverter"]["unittest"]["joindata"]["data"]["test2"][
                "input1"
            ],
            "data_url": CFG["rdfconverter"]["unittest"]["joindata"]["data"]["test2"][
                "input2"
            ],
            "minimal": True,
        }
        res = requests.post(
            ENDPOINT + CFG["rdfconverter"]["unittest"]["joindata"]["contextroot"],
            json=payload,
        )
        res_graph = Graph()
        res_graph.parse(data=res.json()["graph"], format="ttl")

        expectation = requests.get(
            CFG["rdfconverter"]["unittest"]["joindata"]["data"]["test2"][
                "expectedOutput"
            ]
        )
        expect_graph = Graph()
        expect_graph.parse(data=expectation.text, format="ttl")

        # canonicalize both graphs
        iso1 = to_isomorphic(res_graph)
        iso2 = to_isomorphic(expect_graph)

        _, _, in_second = graph_diff(iso1, iso2)

        # all nodes of the second graph are included in both graphs
        self.assertEqual(len(in_second), 0)

    def test_validate_conforms(self):
        payload = {
            "rdf_url": CFG["rdfconverter"]["unittest"]["validation"]["data"]["test1"][
                "rdf"
            ],
            "shapes_url": CFG["rdfconverter"]["unittest"]["validation"]["data"][
                "test1"
            ]["shacl"],
        }
        res = requests.post(
            ENDPOINT + CFG["rdfconverter"]["unittest"]["validation"]["contextroot"],
            json=payload,
        )
        self.assertTrue(res.json()["valid"])

    def test_validate_does_not_conform(self):
        payload = {
            "rdf_url": CFG["rdfconverter"]["unittest"]["validation"]["data"]["test2"][
                "rdf"
            ],
            "shapes_url": CFG["rdfconverter"]["unittest"]["validation"]["data"][
                "test2"
            ]["shacl"],
        }
        res = requests.post(
            ENDPOINT + CFG["rdfconverter"]["unittest"]["validation"]["contextroot"],
            json=payload,
        )
        self.assertFalse(res.json()["valid"])


if __name__ == "__main__":
    unittest.main()
