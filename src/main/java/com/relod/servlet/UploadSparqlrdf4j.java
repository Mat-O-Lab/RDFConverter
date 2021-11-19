package com.relod.servlet;

import java.io.File;
import java.net.URL;

import org.eclipse.rdf4j.model.IRI;
import org.eclipse.rdf4j.model.ValueFactory;
import org.eclipse.rdf4j.repository.Repository;
import org.eclipse.rdf4j.repository.RepositoryConnection;
import org.eclipse.rdf4j.repository.http.HTTPRepository;
import org.eclipse.rdf4j.rio.RDFFormat;

public class UploadSparqlrdf4j {
	public static void main(String[] args) throws Exception {

		String rdf4jServer = "http://localhost:8080/rdf4j-server/";
		String repositoryID = "test1relod";
		Repository rep = new HTTPRepository(rdf4jServer, repositoryID);
		//Repository rep = new HTTPRepository("http://localhost:8080/rdf4j-workbench/repositories/test1relod/");
		ValueFactory vf = rep.getValueFactory();
		IRI graph = vf.createIRI("file:////media/andre/DATA/eclipse2021/dSimilarity/src/main/java/com/relod/servlet/example.nq");
		try (RepositoryConnection conn = rep.getConnection()) {
			//URL data = UploadSparqlrdf4j.class.getResource("/example-data-artists.ttl");
			//URL data = UploadSparqlrdf4j.class.getResource("/media/andre/DATA/eclipse2021/dSimilarity/src/main/java/com/relod/servlet/fuseki_example.ttl");
			File f = new File("/media/andre/DATA/eclipse2021/dSimilarity/src/main/java/com/relod/servlet/example.nq");
			URL data = f.toURI().toURL();
			conn.add(data.openStream(), data.toExternalForm(), RDFFormat.NQUADS, graph);
		} finally {
			rep.shutDown();
		}
	}
}
