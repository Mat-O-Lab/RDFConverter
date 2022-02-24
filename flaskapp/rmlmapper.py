from rdflib import Graph, Namespace, RDF, URIRef
import requests
import json

RR = Namespace('http://www.w3.org/ns/r2rml#')
RML = Namespace('http://semweb.mmlab.be/ns/rml#')
RDFS = Namespace('http://www.w3.org/2000/01/rdf-schema#')
FNML = Namespace('http://semweb.mmlab.be/ns/fnml#')

def map_graph(map_str: str, data_source: str = None) -> Graph:
	g = Graph()
	g.parse(data=map_str)

	if data_source is None:
		data_source = find_data_source(g)

	join_graph = Graph()
	
	for triples_map in g.subjects(RDF.type, RR.TriplesMap):
		try:
			mapping = get_mapping(g, data_source, triples_map)
			join_graph.add(mapping)
		except ValueError:
			continue
	
	return join_graph

def find_data_source(graph: Graph):
	source_node = graph.value(predicate=RDF.type, object=RML.LogicalSource)
	return graph.value(source_node, RML.source)

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


small_ttl = """
@prefix rr: <http://www.w3.org/ns/r2rml#>.
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>.
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#>.
@prefix fnml: <http://semweb.mmlab.be/ns/fnml#>.
@prefix fno: <https://w3id.org/function/ontology#>.
@prefix d2rq: <http://www.wiwiss.fu-berlin.de/suhl/bizer/D2RQ/0.1#>.
@prefix void: <http://rdfs.org/ns/void#>.
@prefix dc: <http://purl.org/dc/terms/>.
@prefix foaf: <http://xmlns.com/foaf/0.1/>.
@prefix rml: <http://semweb.mmlab.be/ns/rml#>.
@prefix ql: <http://semweb.mmlab.be/ns/ql#>.
@prefix : <http://purl.matolab.org/mseo/mappings/>.
@prefix data: <https://raw.githubusercontent.com/Mat-O-Lab/resources/main/mechanics/data/polymer_tensile/Zugversuch_eng_ETFE-Ref%2BGroesseneffekt2-metadata.json/>.
@prefix method: <https://raw.githubusercontent.com/Mat-O-Lab/MSEO/main/methods/DIN_EN_ISO_527-3.drawio.ttl/>.
@prefix obo: <http://purl.obolibrary.org/obo/>.

<http://mapping.example.com/rules_000> a void:Dataset.
:source_000 a rml:LogicalSource;
    rdfs:label "data_columns";
    rml:source "https://raw.githubusercontent.com/Mat-O-Lab/resources/main/mechanics/data/polymer_tensile/Zugversuch_eng_ETFE-Ref%2BGroesseneffekt2-metadata.json";
    rml:iterator "$.tableSchema.columns[*]";
    rml:referenceFormulation ql:JSONPath.
:source_001 a rml:LogicalSource;
    rdfs:label "data_notes";
    rml:source "https://raw.githubusercontent.com/Mat-O-Lab/resources/main/mechanics/data/polymer_tensile/Zugversuch_eng_ETFE-Ref%2BGroesseneffekt2-metadata.json";
    rml:iterator "$.notes[*]";
    rml:referenceFormulation ql:JSONPath.
<http://mapping.example.com/rules_000> void:exampleResource :map_WidthMeasurementInformation_000.
:map_WidthMeasurementInformation_000 rml:logicalSource :source_001;
    a rr:TriplesMap;
    rdfs:label "WidthMeasurementInformation".
:s_000 a rr:SubjectMap.
:map_WidthMeasurementInformation_000 rr:subjectMap :s_000.
:s_000 a fnml:FunctionTermMap;
    rr:termType rr:IRI;
    fnml:functionValue :fn_000.
:fn_000 rml:logicalSource :source_001;
    rr:predicateObjectMap :pomexec_000.
:pomexec_000 rr:predicateMap :pmexec_000.
:pmexec_000 rr:constant fno:executes.
:pomexec_000 rr:objectMap :omexec_000.
:omexec_000 rr:constant "http://example.com/idlab/function/trueCondition";
    rr:termType rr:IRI.
:fn_000 rr:predicateObjectMap :pom_000.
:pom_000 a rr:PredicateObjectMap;
    rr:predicateMap :pm_000.
:pm_000 a rr:PredicateMap;
    rr:constant <http://example.com/idlab/function/strBoolean>.
:pom_000 rr:objectMap :om_000.
:om_000 a rr:ObjectMap, fnml:FunctionTermMap;
    fnml:functionValue :fn_001.
:fn_001 rml:logicalSource :source_001;
    rr:predicateObjectMap :pomexec_001.
:pomexec_001 rr:predicateMap :pmexec_001.
:pmexec_001 rr:constant fno:executes.
:pomexec_001 rr:objectMap :omexec_001.
:omexec_001 rr:constant "http://example.com/idlab/function/equal";
    rr:termType rr:IRI.
:fn_001 rr:predicateObjectMap :pom_001.
:pom_001 a rr:PredicateObjectMap;
    rr:predicateMap :pm_001.
:pm_001 a rr:PredicateMap;
    rr:constant <http://users.ugent.be/~bjdmeest/function/grel.ttl#valueParameter>.
:pom_001 rr:objectMap :om_001.
:om_001 a rr:ObjectMap;
    rml:reference "label";
    rr:termType rr:Literal.
:fn_001 rr:predicateObjectMap :pom_002.
:pom_002 a rr:PredicateObjectMap;
    rr:predicateMap :pm_002.
:pm_002 a rr:PredicateMap;
    rr:constant <http://users.ugent.be/~bjdmeest/function/grel.ttl#valueParameter2>.
:pom_002 rr:objectMap :om_002.
:om_002 a rr:ObjectMap;
    rr:constant "Probenbreite b0";
    rr:termType rr:Literal.
:fn_000 rr:predicateObjectMap :pom_003.
:pom_003 a rr:PredicateObjectMap;
    rr:predicateMap :pm_003.
:pm_003 a rr:PredicateMap;
    rr:constant <http://example.com/idlab/function/str>.
:pom_003 rr:objectMap :om_003.
:om_003 a rr:ObjectMap;
    rr:template "https://raw.githubusercontent.com/Mat-O-Lab/resources/main/mechanics/data/polymer_tensile/Zugversuch_eng_ETFE-Ref%2BGroesseneffekt2-metadata.json/{@id}";
    rr:termType rr:IRI.
:pom_004 a rr:PredicateObjectMap.
:map_WidthMeasurementInformation_000 rr:predicateObjectMap :pom_004.
:pm_004 a rr:PredicateMap.
:pom_004 rr:predicateMap :pm_004.
:pm_004 rr:constant <http://purl.obolibrary.org/obo/0010002>.
:pom_004 rr:objectMap :om_004.
:om_004 a rr:ObjectMap;
    rr:constant "https://raw.githubusercontent.com/Mat-O-Lab/MSEO/main/methods/DIN_EN_ISO_527-3.drawio.ttl/SpecimenName";
    rr:termType rr:Literal.
<http://mapping.example.com/rules_000> void:exampleResource :map_WidthMeasurementInformation_001.
:map_WidthMeasurementInformation_001 rml:logicalSource :source_000;
    a rr:TriplesMap;
    rdfs:label "WidthMeasurementInformation".
:s_001 a rr:SubjectMap.
:map_WidthMeasurementInformation_001 rr:subjectMap :s_001.
:s_001 a fnml:FunctionTermMap;
    rr:termType rr:IRI;
    fnml:functionValue :fn_002.
:fn_002 rml:logicalSource :source_000;
    rr:predicateObjectMap :pomexec_002.
:pomexec_002 rr:predicateMap :pmexec_002.
:pmexec_002 rr:constant fno:executes.
:pomexec_002 rr:objectMap :omexec_002.
:omexec_002 rr:constant "http://example.com/idlab/function/trueCondition";
    rr:termType rr:IRI.
:fn_002 rr:predicateObjectMap :pom_005.
:pom_005 a rr:PredicateObjectMap;
    rr:predicateMap :pm_005.
:pm_005 a rr:PredicateMap;
    rr:constant <http://example.com/idlab/function/strBoolean>.
:pom_005 rr:objectMap :om_005.
:om_005 a rr:ObjectMap, fnml:FunctionTermMap;
    fnml:functionValue :fn_003.
:fn_003 rml:logicalSource :source_000;
    rr:predicateObjectMap :pomexec_003.
:pomexec_003 rr:predicateMap :pmexec_003.
:pmexec_003 rr:constant fno:executes.
:pomexec_003 rr:objectMap :omexec_003.
:omexec_003 rr:constant "http://example.com/idlab/function/equal";
    rr:termType rr:IRI.
:fn_003 rr:predicateObjectMap :pom_006.
:pom_006 a rr:PredicateObjectMap;
    rr:predicateMap :pm_006.
:pm_006 a rr:PredicateMap;
    rr:constant <http://users.ugent.be/~bjdmeest/function/grel.ttl#valueParameter>.
:pom_006 rr:objectMap :om_006.
:om_006 a rr:ObjectMap;
    rml:reference "label";
    rr:termType rr:Literal.
:fn_003 rr:predicateObjectMap :pom_007.
:pom_007 a rr:PredicateObjectMap;
    rr:predicateMap :pm_007.
:pm_007 a rr:PredicateMap;
    rr:constant <http://users.ugent.be/~bjdmeest/function/grel.ttl#valueParameter2>.
:pom_007 rr:objectMap :om_007.
:om_007 a rr:ObjectMap;
    rr:constant "Probenbreite b0";
    rr:termType rr:Literal.
:fn_002 rr:predicateObjectMap :pom_008.
:pom_008 a rr:PredicateObjectMap;
    rr:predicateMap :pm_008.
:pm_008 a rr:PredicateMap;
    rr:constant <http://example.com/idlab/function/str>.
:pom_008 rr:objectMap :om_008.
:om_008 a rr:ObjectMap;
    rr:template "https://raw.githubusercontent.com/Mat-O-Lab/resources/main/mechanics/data/polymer_tensile/Zugversuch_eng_ETFE-Ref%2BGroesseneffekt2-metadata.json/{@id}";
    rr:termType rr:IRI.
:pom_009 a rr:PredicateObjectMap.
:map_WidthMeasurementInformation_001 rr:predicateObjectMap :pom_009.
:pm_009 a rr:PredicateMap.
:pom_009 rr:predicateMap :pm_009.
:pm_009 rr:constant <http://purl.obolibrary.org/obo/0010002>.
:pom_009 rr:objectMap :om_009.
:om_009 a rr:ObjectMap;
    rr:constant "https://raw.githubusercontent.com/Mat-O-Lab/MSEO/main/methods/DIN_EN_ISO_527-3.drawio.ttl/SpecimenName";
    rr:termType rr:Literal.
"""

with open('large.ttl', 'r') as f:
	print(map_graph(f.read()).serialize(format='ttl'))