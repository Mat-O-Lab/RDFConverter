from rdflib import Graph, Namespace, RDF, URIRef
import requests
import json
import re

RR = Namespace('http://www.w3.org/ns/r2rml#')
RML = Namespace('http://semweb.mmlab.be/ns/rml#')
RDFS = Namespace('http://www.w3.org/2000/01/rdf-schema#')
FNML = Namespace('http://semweb.mmlab.be/ns/fnml#')

def map_graph(g: Graph, data_source: str) -> Graph:
	join_graph = Graph()
	
	for triples_map in g.subjects(RDF.type, RR.TriplesMap):
		try:
			mapping = get_mapping(g, data_source, triples_map)
			join_graph.add(mapping)
		except ValueError:
			continue
	
	return join_graph

def find_data_source(rules: str):
	source = re.findall(r'\@prefix\ data\:\ <(.+)>', rules).pop()
	return source[:-1] if source[-1] == '/' else source

def find_method_graph(rules: str):
	source = re.findall(r'\@prefix\ method\:\ <(.+)>', rules).pop()
	return source[:-1] if source[-1] == '/' else source


# find the subject of a specified TriplesMap
def find_subject_label(graph: Graph, triples_node):
	sm_node = graph.value(triples_node, RR.subjectMap, any=False)
	fn_node = graph.value(sm_node, FNML.functionValue, any=False)
	pom_node = None

	# find PredicateObjectMap that has strBoolean as the predicate
	for pom in graph.objects(fn_node, RR.predicateObjectMap):
		pm = graph.value(pom, RR.predicateMap, any=False)
		if (pm, RR.constant, URIRef("http://example.com/idlab/function/strBoolean")) in graph:
			pom_node = pom
	om_node = graph.value(pom_node, RR.objectMap, any=False)
	fn2_node = graph.value(om_node, FNML.functionValue, any=False)

	# find ObjectMap with constant
	for pom in graph.objects(fn2_node, RR.predicateObjectMap):
		if (pom, RDF.type, RR.PredicateObjectMap) in graph:
			for om in graph.objects(pom, RR.objectMap):
				try:
					return next(graph.objects(om, RR.constant))
				except Exception:
					continue
	
# TODO: currently only searching in notes, id might also be found in columns
def find_subject_id(data_source, label):
	data_json = json.loads(requests.get(data_source).text)
	for elem in data_json['notes']:
		if label.strip() == elem['label'].strip():
			return elem['@id']
	raise ValueError('Cant find matching label or column in data!')

def get_subject_node(data_source, subject_id):
	return data_source + subject_id[1:]

# find the predicate of a specified TriplesMap
def find_predicate(graph: Graph, triples_node):
	pom_node = graph.value(triples_node, RR.predicateObjectMap, any=False)
	pm_node = graph.value(pom_node, RR.predicateMap, any=False)
	return graph.value(pm_node, RR.constant, any=False)

# find the object of a specified TriplesMap
def find_object(graph: Graph, triples_node):
	pom_node = graph.value(triples_node, RR.predicateObjectMap, any=False)
	om_node = graph.value(pom_node, RR.objectMap, any=False)
	return graph.value(om_node, RR.constant, any=False)

def get_mapping(graph: Graph, data_source: str, triples_node):
	subject_label = find_subject_label(graph, triples_node)
	subject_id = find_subject_id(data_source, subject_label)
	subject_node = URIRef(get_subject_node(data_source, subject_id))
	predicate_node = find_predicate(graph, triples_node)
	object_node = find_object(graph, triples_node)
	
	return (subject_node, predicate_node, object_node)
