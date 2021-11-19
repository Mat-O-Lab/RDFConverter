package com.relod.servlet;

import org.eclipse.rdf4j.RDF4JException;
import org.eclipse.rdf4j.repository.Repository;
import org.eclipse.rdf4j.repository.RepositoryConnection;
import org.eclipse.rdf4j.repository.http.HTTPRepository;
import org.eclipse.rdf4j.rio.RDFFormat;
import java.io.File;
import java.net.URL;

public class Upload2 {
	public static void main(String[] args) throws Exception {
		File file = new File("/media/andre/DATA/eclipse2021/dSimilarity/src/main/java/com/relod/servlet/example.nq");
		String baseURI = "http://example.org/example/local";
		try {
			String rdf4jServer = "http://localhost:8080/rdf4j-server/";
			String repositoryID = "test1relod";
			Repository repo = new HTTPRepository(rdf4jServer, repositoryID);
			RepositoryConnection con = repo.getConnection();
			try {
				con.add(file, baseURI, RDFFormat.NQUADS);
				URL url = new URL("http://141.57.11.86:8082/AMOntology-vFinal1.owl");
				con.add(url, url.toString(), RDFFormat.RDFXML);
			} finally {
				con.close();
			}
		} catch (RDF4JException e) {
			e.printStackTrace();
		} catch (java.io.IOException e) {
			e.printStackTrace();
		}
	}
}
