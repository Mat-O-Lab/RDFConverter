<%@ page language="java" contentType="text/html; charset=UTF-8"
    pageEncoding="UTF-8"%>
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Insert title here</title>
</head>
<body>
<h1>Generic Sparql Query RDF Dataset</h1>
<h4>SPARQL endpoint, HDT file, RDF dump file, Ontology, etc...All you need is the URL of your datasets</h4>
<form action="SimilarityServlet">
  <label for="fname">IRI Dataset:</label>
  <input type="text" id="dataset" name="dataset" value="https://dbpedia.org/sparql"><br>
  if the IRI does not work you can upload a dataset/ontology here:
            <a title="Add Dataset" href="uploadHDT.jsp"> <span
			style="background-color: #2b2301; color: #fff; display: inline-block; padding: 3px 10px; font-weight: bold; border-radius: 5px;">Add
				Dataset</span>
		</a> <br><br>
  <label for="lname">SPARQL query:</label>
  <textarea id="query" name="query" rows="4" cols="50">select distinct ?Concept where {[] a ?Concept} LIMIT 100</textarea><br><br>
  <input type="submit" value="Submit">
  <br/><a href="index.jsp">Back to Dataset similarity...</a>
  <br/><a href="http://w3id.org/relod">Go to ReLOD, the Dataset
				Similarity index</a>
</form>
</body>
</html>