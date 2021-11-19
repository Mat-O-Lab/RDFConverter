package com.relod.servlet;

import java.io.IOException;
import java.io.InputStream;
import java.net.MalformedURLException;
import java.net.URL;

import org.eclipse.rdf4j.RDF4JException;
import org.eclipse.rdf4j.model.Model;
import org.eclipse.rdf4j.model.Statement;
import org.eclipse.rdf4j.model.impl.LinkedHashModel;
import org.eclipse.rdf4j.query.GraphQueryResult;
import org.eclipse.rdf4j.query.QueryResults;
import org.eclipse.rdf4j.rio.RDFFormat;
import org.eclipse.rdf4j.rio.RDFHandlerException;
import org.eclipse.rdf4j.rio.RDFParseException;
import org.eclipse.rdf4j.rio.RDFParser;
import org.eclipse.rdf4j.rio.Rio;
import org.eclipse.rdf4j.rio.helpers.StatementCollector;

public class Testrdf4j {

	public static void main(String[] args) throws IOException {
		System.out.println(GenericSparqlServlet.getFinalURL(new URL("https://rest.matportal.org/ontologies/EMMO/submissions/1/download?apikey\\u003d66c82e77-ce0d-4385-8056-a95898e47ebb")));
	}

	public static void test1() throws IOException {
		java.net.URL documentUrl = new URL("http://141.57.11.86:8082/dirHDTLaundromat/decompressed/76/7682278f9dd608f09c4c073a915e58a1/7682278f9dd608f09c4c073a915e58a1.hdt");
		//URL documentUrl = new URL("https://www.w3.org/2001/sw/DataAccess/df1/tests/rdf-schema.ttl");
		InputStream inputStream = documentUrl.openStream();
		
		RDFFormat format = Rio.getParserFormatForFileName(documentUrl.toString()).orElse(RDFFormat.RDFXML);
		RDFParser rdfParser = Rio.createParser(format);
		
		Model model = new LinkedHashModel();
		rdfParser.setRDFHandler(new StatementCollector(model));
		try {
			rdfParser.parse(inputStream, documentUrl.toString());
			String baseURI = "http://www.w3.org/2000/01/rdf-schema-more";
			try (GraphQueryResult res = QueryResults.parseGraphBackground(inputStream, baseURI , format)) {
			  while (res.hasNext()) {
			    Statement st = res.next();
			    System.out.println("st: " + st.toString());
			  }
			}
			catch (RDF4JException e) {
			  e.printStackTrace();
			}
			finally {
			  inputStream.close();
			}
			
		} catch (IOException e) {
			e.printStackTrace();
		} catch (RDFParseException e) {
			e.printStackTrace();
		} catch (RDFHandlerException e) {
			e.printStackTrace();
		} finally {
			inputStream.close();
		}
		
	}
}
