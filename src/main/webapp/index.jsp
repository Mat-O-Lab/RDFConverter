<%@ page language="java" contentType="text/html; charset=UTF-8"
	pageEncoding="UTF-8"%>
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Insert title here</title>
</head>
<body>
	<h1>Which properties and classes the RDF datasets have in common?</h1>
	<h4>SPARQL endpoint, HDT file, RDF dump file, Ontology, etc...All you need is the URL of your datasets</h4>
	
	<form action="SimilarityServlet">
		<fieldset style="border: none">
			<label for="fname">Datasets</label>
			<textarea id="datasets" name="datasets" rows="4" cols="80">http://pt.dbpedia.org/sparql, https://dbpedia.org/sparql</textarea>
			<br/>
			<input type="radio" id="exact" name="opt" value="exact"/> Exact Matches
			<br/>
			<input type="radio" id="dsim" name="opt" value="dsim"/> Similar Matches
			<input type="text" id="simlevel" name="simlevel" value="0.9" /> Similarity level (0.0-1.0)
			<br/>
			<input type="checkbox" id="rdf" name="rdf" value="rdf"/> Results in RDF
			<br> <br> <input type="submit" value="Submit">
		</fieldset>
	</form>
	<br>
	<h3>Or</h3>
	<ol style="margin-top: 0px">
		<li><a href="genericEndPointQuery.jsp">Query your prefered
				dataset</a></li>
		<li><a href="http://w3id.org/relod">Go to ReLOD, the Dataset
				Similarity index</a></li>
	</ol>
</body>
</html>