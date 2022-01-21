package com.bam.servlet;

import java.io.*;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.apache.http.HttpEntity;
import org.apache.http.NameValuePair;
import org.apache.http.client.entity.UrlEncodedFormEntity;
import org.apache.http.client.methods.CloseableHttpResponse;
import org.apache.http.client.methods.HttpPost;
import org.apache.http.impl.client.CloseableHttpClient;
import org.apache.http.impl.client.HttpClients;
import org.apache.http.message.BasicNameValuePair;
import org.apache.http.util.EntityUtils;
import org.eclipse.rdf4j.model.Model;
import org.eclipse.rdf4j.model.vocabulary.RDF4J;
import org.eclipse.rdf4j.query.algebra.Str;
import org.eclipse.rdf4j.repository.sail.SailRepository;
import org.eclipse.rdf4j.repository.sail.SailRepositoryConnection;
import org.eclipse.rdf4j.rio.RDFFormat;
import org.eclipse.rdf4j.rio.Rio;
import org.eclipse.rdf4j.sail.memory.MemoryStore;
import org.eclipse.rdf4j.sail.shacl.ShaclSail;
import org.eclipse.rdf4j.sail.shacl.ShaclSailValidationException;

import com.google.gson.Gson;

import be.ugent.rml.Executor;
import be.ugent.rml.Utils;
import be.ugent.rml.functions.FunctionLoader;
import be.ugent.rml.functions.lib.IDLabFunctions;
import be.ugent.rml.records.RecordsFactory;
import be.ugent.rml.store.QuadStore;
import be.ugent.rml.store.QuadStoreFactory;
import be.ugent.rml.store.RDF4JStore;
import be.ugent.rml.term.NamedNode;
import jakarta.servlet.ServletException;
import jakarta.servlet.annotation.WebServlet;
import jakarta.servlet.http.HttpServlet;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;

import static com.bam.servlet.RDFValidator.validateRDF;

/**
 * Servlet implementation class RDFConverter
 */
@WebServlet("/RDFConverter")
public class RDFConverter extends HttpServlet {
	private static final long serialVersionUID = 1L;

	/**
	 * Default constructor.
	 */
	public RDFConverter() {
		// TODO Auto-generated constructor stub
	}

	static class Conf {
		String yarrrml;
		String chowlk;
		String shacl;
	}

	/**
	 * @see HttpServlet#doGet(HttpServletRequest request, HttpServletResponse
	 *      response)
	 */
	protected void doGet(HttpServletRequest request, HttpServletResponse response)
			throws ServletException, IOException {
		if (request.getParameter("jsonfile") != null) {
			String jsonFile = request.getParameter("jsonfile");
			response.getWriter().append("Validating and uploading files to the triple store...");
			try {
				String jsonConf = readUrl(jsonFile);
				Gson gson = new Gson();
				Conf conf = gson.fromJson(jsonConf, Conf.class);

				String yamlContent = readUrl(conf.yarrrml);
				String ttlChowlk = extractTTLMethodfromYaml(yamlContent);
				String rdfYarrrml = generateRDFyaml(yamlContent);
				String shacl = null;
				if (conf.shacl != null && conf.shacl.startsWith("http")) {
					shacl = readUrl(conf.shacl);
					String resultShacl = validateRDF(rdfYarrrml, shacl);
					if (!resultShacl.startsWith("valid")) {
						response.getWriter().append(resultShacl);
					} else {
						String resultIncludeTriples = includeTripleStore(rdfYarrrml, ttlChowlk);
						if (resultIncludeTriples.startsWith("fail")) {
							response.getWriter().append(resultIncludeTriples);
						}
					}
				} else {
					String resultIncludeTriples = includeTripleStore(rdfYarrrml, ttlChowlk);
					resultIncludeTriples += "---No SHACL shapes provided---";
					// if (resultIncludeTriples.startsWith("fail")) {
					response.getWriter().append(resultIncludeTriples);
					// }
				}
			} catch (Exception e) {
				// TODO Auto-generated catch block
				e.printStackTrace();
			}

		}
	}

	private String extractTTLMethodfromYaml(String yamlContent) throws Exception {
		String ttlURL = yamlContent.substring(yamlContent.indexOf("method:") + 9, yamlContent.indexOf(".ttl")) + ".ttl";
		return readUrl(ttlURL);
	}

	private String includeTripleStore(String rdfYarrrml, String ttlChowlk) {
		String ret = "";
		// ret += DataManager.insertTriples(rdfYarrrml);
		ret += DataManager.insertTriples(ttlChowlk);
		return ret;
	}

	/*
	 * java -jar /path/to/rmlmapper.jar -m rules.rml.ttl -o /path/to/outputfile.ttl
	 * 
	 * Based on: https://github.com/RMLio/rmlmapper-java/blob/master/src/test/java/be/ugent/rml/readme/ReadmeTest.java
	 */
	private String generateRDFyaml(String yarrrml) {
		QuadStore result = null;
		try {
			// String mapPath = "./src/test/resources/argument/mapping.ttl"; // path to the
			// mapping file that needs to be
			// executed
			// File mappingFile = new File(mapPath);
			File mappingFile = generateRML(yarrrml);

			// Get the mapping string stream
			InputStream mappingStream = new FileInputStream(mappingFile);

			// Load the mapping in a QuadStore
			QuadStore rmlStore = QuadStoreFactory.read(mappingStream);

			// Set up the basepath for the records factory, i.e., the basepath for the
			// (local file) data sources
			RecordsFactory factory = new RecordsFactory(mappingFile.getParent());

			// Set up the functions used during the mapping
			Map<String, Class> libraryMap = new HashMap<>();
			libraryMap.put("IDLabFunctions", IDLabFunctions.class);

			FunctionLoader functionLoader = new FunctionLoader(null, libraryMap);

			// Set up the outputstore (needed when you want to output something else than
			// nquads
			QuadStore outputStore = new RDF4JStore();

			// Create the Executor
			Executor executor = new Executor(rmlStore, factory, functionLoader, outputStore,
					Utils.getBaseDirectiveTurtle(mappingStream));

			// Execute the mapping
			result = executor.executeV5(null).get(new NamedNode("rmlmapper://default.store"));

			// Output the result
			BufferedWriter out = new BufferedWriter(new OutputStreamWriter(System.out));
			result.write(out, "turtle");
			out.close();
		} catch (Exception e) {
			e.printStackTrace();
		}
		return result.toSortedString();
	}

	/*
	 * yarrrml-parser -i yarrrml.yml -o rules.rml.ttl
	 */
	private File generateRML(String yarrrml) throws IOException {

		// open HTTP client
		try (CloseableHttpClient httpClient = HttpClients.createDefault()) {
			HttpPost httpPost = new HttpPost("http://localhost:3000");
			List<NameValuePair> values = new ArrayList<>();
			values.add(new BasicNameValuePair("yarrrml", yarrrml));
			httpPost.setEntity(new UrlEncodedFormEntity(values));

			//make POST to yarrrm-parser service and return response string
			try (CloseableHttpResponse httpResponse = httpClient.execute(httpPost)) {
				HttpEntity response = httpResponse.getEntity();

				String rml = EntityUtils.toString(response);
				EntityUtils.consume(response);
				return null;
			}
		}
	}

	private static String readUrl(String urlString) throws Exception {
		BufferedReader reader = null;
		try {
			URL url = new URL(urlString);
			reader = new BufferedReader(new InputStreamReader(url.openStream()));
			StringBuffer buffer = new StringBuffer();
			int read;
			char[] chars = new char[1024];
			while ((read = reader.read(chars)) != -1)
				buffer.append(chars, 0, read);

			return buffer.toString();
		} finally {
			if (reader != null)
				reader.close();
		}
	}

	/**
	 * @see HttpServlet#doPost(HttpServletRequest request, HttpServletResponse
	 *      response)
	 */
	protected void doPost(HttpServletRequest request, HttpServletResponse response)
			throws ServletException, IOException {
		// TODO Auto-generated method stub
		doGet(request, response);
	}

}
