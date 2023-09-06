import json
import logging
from re import split as re_split
from urllib.parse import unquote, urlparse
from urllib.request import urlopen

import requests
from rdflib import RDF, Graph, Literal, Namespace, URIRef
from rdflib.plugins.sparql import prepareQuery
from rdflib.util import guess_format
#from reasonable import PyReasoner

RR = Namespace("http://www.w3.org/ns/r2rml#")
RML = Namespace("http://semweb.mmlab.be/ns/rml#")
RDFS = Namespace("http://www.w3.org/2000/01/rdf-schema#")
FNML = Namespace("http://semweb.mmlab.be/ns/fnml#")


def parse_graph(url: str, graph: Graph = Graph(), format: str = "") -> Graph:
    """Parse a Graph from web url to rdflib graph object
    Args:
        url (AnyUrl): Url to an web ressource
        graph (Graph): Existing Rdflib Graph object to parse data to.
    Returns:
        Graph: Rdflib graph Object
    """
    logging.debug("parsing graph from {}".format(url))
    parsed_url = urlparse(url)
    META = Namespace(url + "/")
    if not format:
        format = guess_format(parsed_url.path)
    if parsed_url.scheme in ["https", "http"]:
        graph.parse(urlopen(parsed_url.geturl()).read(), format=format)
    elif parsed_url.scheme == "file":
        graph.parse(parsed_url.path, format=format)
    graph.bind("meta", META)
    return graph


def strip_namespace(term: URIRef) -> str:
    """Strip the namespace from full URI

    Args:
        term (URIRef): A RDFlib Term

    Returns:
        str: short IRI
    """
    return re_split(r"/|#|:", term[::-1], maxsplit=1)[0][::-1]


def map_graph(g: Graph, data_source: str) -> Graph:
    join_graph = Graph()

    for triples_map in g.subjects(RDF.type, RR.TriplesMap):
        try:
            mapping = get_mapping(g, data_source, triples_map)
            join_graph.add(mapping)
        except ValueError:
            continue

    return join_graph


def find_data_source(rules: Graph):
    # any source triple is ok, they have the same literal values
    return next(rules[: RML.source :])[1].value


def replace_data_source(rules: Graph, new_source: str):
    data_source_origin = find_data_source(rules)
    if data_source_origin:
        sources = list(rules.subjects(RML.source, Literal(data_source_origin)))
        for source in sources:
            print("setting source {} with {}".format(source, new_source))
            rules.set((source, RML.source, Literal(new_source)))


def find_method_graph(rules: Graph):
    pass


def count_rules(graph: Graph):
    src = graph.value(predicate=RDF.type, object=RML.LogicalSource)
    maps = graph.subjects(RML.logicalSource, src)
    # return the number of TriplesMaps of any source
    return len([elem for elem in maps if (elem, RDF.type, RR.TriplesMap) in graph])


def count_rules_str(graph_str: str):
    graph = Graph()
    graph.parse(data=graph_str, format="ttl")
    return count_rules(graph)


# find the subject of a specified TriplesMap
def find_subject_label(graph: Graph, triples_node):
    sm_node = graph.value(triples_node, RR.subjectMap, any=False)
    fn_node = graph.value(sm_node, FNML.functionValue, any=False)
    pom_node = None

    # find PredicateObjectMap that has strBoolean as the predicate
    for pom in graph.objects(fn_node, RR.predicateObjectMap):
        pm = graph.value(pom, RR.predicateMap, any=False)
        if (
            pm,
            RR.constant,
            URIRef("http://example.com/idlab/function/strBoolean"),
        ) in graph:
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
    for elem in data_json["notes"]:
        if label.strip() == elem["label"].strip():
            return elem["@id"]
    raise ValueError("Cant find matching label or column in data!")


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


def replace_iris(old: URIRef, new: URIRef, graph: Graph):
    # replaces all iri of all triple in a graph with the value of relation
    old_triples = list(graph[old:None:None])
    for triple in old_triples:
        graph.remove((old, triple[0], triple[1]))
        graph.add((new, triple[0], triple[1]))
    old_triples = list(graph[None:None:old])
    for triple in old_triples:
        graph.remove((triple[0], triple[1], old))
        graph.add((triple[0], triple[1], new))
    old_triples = list(graph[None:old:None])
    for triple in old_triples:
        graph.remove((triple[0], old, triple[1]))
        graph.add((triple[0], new, triple[1]))

#FILTER ( !(?p=rdf:type && isBlank(?o)))
filterBlankTypesAndClasses = prepareQuery(
    """
    SELECT ?s ?p ?o WHERE 
    {
        ?s ?p ?o. FILTER ( !isBlank(?o))
    }
    """
)

deleteClassesAndProperties = prepareQuery(
    """
    SELECT ?s ?p ?o WHERE 
    {
        ?s rdf:type ?t ;
            ?p ?o. 
        FILTER ( ?t=owl:Class || ?t=owl:ObjectProperty)
    }
    """,
    initNs = { "rdf": RDF}
)


def getUsedNamespaces(g: Graph):
    """Remove unused prefix in the graph and remove it from the graph"""
    usedNamespaces = []  # List of namespace
    for (
        namespace
    ) in (
        g.namespaces()
    ):  # Iterate for all the namespace in the document check if the namespace is present
        queryCheck = (
            """
            PREFIX """
            + namespace[0]
            + """: <"""
            + str(namespace[1])
            + """>
            select ?x where {
                {
                    ?x ?z ?v.
                    filter(strstarts(str(?x), str("""
            + namespace[0]
            + """:)))
                }
                union
                {
                    ?z ?x ?v.
                    filter(strstarts(str(?x), str("""
            + namespace[0]
            + """:)))
                }
                union
                {
                    ?v ?z ?x.
                    filter(strstarts(str(?x), str("""
            + namespace[0]
            + """:)))
                }

            }"""
        )  # Query to find the places where namespaces are used
        if len(g.query(queryCheck)) >= 1:  # If the namespace is not used anywhere
            usedNamespaces += [namespace]
    return usedNamespaces

def import_ontologies_from_prefixes(g: Graph()):
    namespaces = getUsedNamespaces(g)
    for prefix, namespace in namespaces:
        if prefix=='owl' or str(namespace) == "http://www.w3.org/2002/07/owl":
            continue
        elif str(namespace) == "http://purl.obolibrary.org/obo/":
            g.parse(
                "https://raw.githubusercontent.com/BFO-ontology/BFO-2020/master/21838-2/owl/bfo-2020.owl",
                format="xml",
            )
            logging.info("loaded bfo-2020 {}".format(namespace))
        elif str(namespace) == "https://purl.matolab.org/mseo/mid/":
            g.parse(
                "https://github.com/Mat-O-Lab/MSEO/raw/main/MSEO_mid.ttl",
                format="turtle",
            )
            logging.info("loaded mseo {}".format(namespace))
        else:
            req = requests.get(namespace, allow_redirects=True)
            # print(req.headers['Content-Type'])
            return_type = req.headers["Content-Type"].split(";")[0].rsplit("/")[-1]
            if "xml" in return_type:
                return_type = "xml"
            elif "plain" in return_type:
                return_type = "turtle"
            if req.status_code != 200 or req.headers["Content-Type"].startswith(
                "text/html"
            ):
                logging.info("failed to load ontology {}".format(namespace))
            else:
                fname = req.url.rstrip("/").rsplit("/", 1)[-1]
                if "." not in fname:
                    format = return_type
                else:
                    format = guess_format(fname)
            try:
                g.parse(data=req.text, format=format)
                logging.info("loaded ontology {} at {}".format(namespace, req.url))
            except:
                logging.info("failed to pasing to graph {}".format(namespace, req.url))
    return g


#using owlready2
import owlready2
import os
def reason_graph(g: Graph = Graph()):
    #print(list(namespaces))
    namespaces = getUsedNamespaces(g)
    #remove all additional Class and ObjectProperty definitions ade by chowl, leaving only Individuals
    toremove=g.query(deleteClassesAndProperties)
    [g.remove(triple) for triple in toremove]
    g.serialize('input.ttl',format='turtle')
    subjects = list(g.subjects())
    len_input=len(g)
    g=import_ontologies_from_prefixes(g)
    g.serialize('toreason.owl',format='xml')
    graph=owlready2.get_ontology("file:///src/toreason.owl").load()
    #iof=owlready2.get_ontology("https://github.com/iofoundry/ontology/blob/master/core/Core.rdf").load()
    bfo=owlready2.get_ontology("https://raw.githubusercontent.com/BFO-ontology/BFO-2020/master/21838-2/owl/bfo-2020.owl").load()
    #mutil=owlready2.get_ontology("https://github.com/Mat-O-Lab/MSEO/raw/main/domain/util/readable_bfo_iris.ttl").load()
    #print(graph.imported_ontologies)
    
    with graph:
        owlready2.sync_reasoner(infer_property_values = True)
        #owlready2.sync_reasoner_hermit(infer_property_values = True)
        owlready2.close_world(graph.entity)
    graph.save(file = 'reasoned.owl', format = "rdfxml")
    res = Graph()
    temp = Graph()
    temp.parse('reasoned.owl',format='xml')
    os.remove('toreason.owl')
    os.remove('reasoned.owl')
    # res.namespace_manager=namespace_manager
    [res.bind(prefix, namespace) for prefix, namespace in namespaces]
    qres = list()
    [
        qres.extend(temp.query(filterBlankTypesAndClasses, initBindings={"s": subject}))
        for subject in subjects
    ]
    [res.add(triple) for triple in qres]
    len_result=len(qres)
    logging.info('Infered {} for named Individuals of input.'.format(len_result-len_input))
    res.serialize('output.ttl')
    return res

# #not giving expected results
# def reason_graph2(g: Graph = Graph()):
#     namespaces = getUsedNamespaces(g)
#     #print(list(namespaces))
#     #remove all additional Class and ObjectProperty definitions ade by chowl, leaving only Individuals
#     toremove=g.query(deleteClassesAndProperties)
#     [g.remove(triple) for triple in toremove]
#     subjects = list(g.subjects())
#     g.serialize('input.ttl')
#     for prefix, namespace in namespaces:
#         if str(namespace) == "http://purl.obolibrary.org/obo/":
#             g.parse(
#                 "https://raw.githubusercontent.com/BFO-ontology/BFO-2020/master/21838-2/owl/bfo-2020.owl",
#                 format="xml",
#             )
#             logging.info("loaded bfo-2020 {}".format(namespace))
#         elif str(namespace) == "https://purl.matolab.org/mseo/mid/":
#             g.parse(
#                 "https://github.com/Mat-O-Lab/MSEO/raw/main/MSEO_mid.ttl",
#                 format="turtle",
#             )
#             logging.info("loaded mseo {}".format(namespace))
#         else:
#             req = requests.get(namespace, allow_redirects=True)
#             # print(req.headers['Content-Type'])
#             return_type = req.headers["Content-Type"].split(";")[0].rsplit("/")[-1]
#             if "xml" in return_type:
#                 return_type = "xml"
#             elif "plain" in return_type:
#                 return_type = "turtle"
#             if req.status_code != 200 or req.headers["Content-Type"].startswith(
#                 "text/html"
#             ):
#                 logging.info("failed to load ontology {}".format(namespace))
#             else:
#                 fname = req.url.rstrip("/").rsplit("/", 1)[-1]
#                 if "." not in fname:
#                     format = return_type
#                 else:
#                     format = guess_format(fname)
#             try:
#                 g.parse(data=req.text, format=format)
#                 logging.info("loaded ontology {} at {}".format(namespace, req.url))
#             except:
#                 logging.info("failed to pasing to graph {}".format(namespace, req.url))
#     g.serialize("input_with_ontologies.ttl")
#     r = PyReasoner()
#     r.from_graph(g)
#     triples = r.reason()
#     temp = Graph()
#     [temp.add(triple) for triple in triples]
#     qres = list()
#     [
#         qres.extend(temp.query(filterBlankTypesAndClasses, initBindings={"s": subject}))
#         for subject in subjects
#     ]
#     # print(qres[:10])
#     res = Graph()
#     # res.namespace_manager=namespace_manager
#     [res.bind(prefix, namespace) for prefix, namespace in namespaces]
#     [res.add(triple) for triple in qres]
#     res.serialize('reasoned.ttl')
#     return res
