package com.bam.servlet;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.net.URL;
import java.util.List;

import com.google.gson.Gson;

import jakarta.servlet.ServletException;
import jakarta.servlet.annotation.WebServlet;
import jakarta.servlet.http.HttpServlet;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;

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

				String rdfYarrrml = generateRDFyaml(readUrl(conf.yarrrml));
				String ttlChowlk = readUrl(conf.chowlk);
				String shacl = readUrl(conf.shacl);
				
				String resultShacl = validateRDF(rdfYarrrml, shacl);
				if(!resultShacl.startsWith("valid")) {
					response.getWriter().append(resultShacl);
				} else {
					String resultIncludeTriples = includeTripleStore(rdfYarrrml, ttlChowlk); 
					if(resultIncludeTriples.startsWith("fail")) {
						response.getWriter().append(resultIncludeTriples);
					}
				}
			} catch (Exception e) {
				// TODO Auto-generated catch block
				e.printStackTrace();
			}

			
		}
	}

	private String includeTripleStore(String rdfYarrrml, String ttlChowlk){
		
		return null;
	}

	private String validateRDF(String rdf, String shaclShapes) {
		// TODO Auto-generated method stub
		return null;
	}

	private String generateRDFyaml(String yarrrml) {
		
		return null;
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
