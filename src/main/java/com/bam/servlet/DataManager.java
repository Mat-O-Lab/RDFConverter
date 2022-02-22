package com.bam.servlet;

import org.apache.http.auth.AuthScope;
import org.apache.http.auth.UsernamePasswordCredentials;
import org.apache.http.client.CredentialsProvider;
import org.apache.http.client.protocol.ClientContext;
import org.apache.http.impl.client.BasicCredentialsProvider;
import org.apache.http.protocol.BasicHttpContext;

import org.apache.jena.sparql.modify.UpdateProcessRemote;
import org.apache.jena.update.UpdateExecutionFactory;
import org.apache.jena.update.UpdateFactory;
import org.apache.jena.update.UpdateProcessor;
import org.apache.jena.update.UpdateRequest;

public class DataManager {

	public static void main(String[] args) {
		String sTriples = "<http://pt.dbpedia.org/sparql> <http://dbpedia.org/ontology/Reptile> <https://dbpedia.org/sparql> .\r\n"
				+ "<http://pt.dbpedia.org/sparql> <http://schema.org/CollegeOrUniversity> <https://dbpedia.org/sparql> .";
		if (insertTriples(sTriples)) {
			System.out.println("yes INSERTED");
		}
	}

	public static boolean insertTriples(String triples) {
		boolean bRes = false;
		try {
			BasicHttpContext httpContext = new BasicHttpContext();
			CredentialsProvider provider = new BasicCredentialsProvider();
			provider.setCredentials(new AuthScope(AuthScope.ANY_HOST,
			    AuthScope.ANY_PORT), new UsernamePasswordCredentials("admin", "NtUb4Mv4vx9040X6"));
			httpContext.setAttribute(ClientContext.CREDS_PROVIDER, provider);

			UpdateRequest update = UpdateFactory.create("INSERT DATA { graph <http://graph/bam> { " + triples + "}}");
			UpdateProcessor processor = UpdateExecutionFactory.createRemote(update, "https://fuseki.matolab.org/SecondaryData/update");
			((UpdateProcessRemote)processor).setHttpContext(httpContext);
			processor.execute();
			bRes = true;
		} catch (Exception ex) {
			ex.printStackTrace();
		}

		return bRes;
	}
}
