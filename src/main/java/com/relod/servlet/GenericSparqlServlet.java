package com.relod.servlet;

import java.io.FileNotFoundException;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.UnsupportedEncodingException;
import java.lang.reflect.Type;
import java.net.HttpURLConnection;
import java.net.MalformedURLException;
import java.net.URI;
import java.net.URISyntaxException;
import java.net.URL;
import java.net.URLEncoder;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.Map;
import java.util.Set;

import org.apache.commons.io.IOUtils;
import org.apache.commons.text.similarity.JaccardSimilarity;
import org.eclipse.rdf4j.model.IRI;
import org.eclipse.rdf4j.model.util.Values;
import org.eclipse.rdf4j.query.QueryLanguage;
import org.eclipse.rdf4j.query.TupleQuery;
import org.eclipse.rdf4j.query.TupleQueryResult;
import org.eclipse.rdf4j.repository.RepositoryConnection;
import org.eclipse.rdf4j.repository.sparql.SPARQLRepository;

import com.google.gson.Gson;
import com.google.gson.reflect.TypeToken;

import jakarta.servlet.ServletException;
import jakarta.servlet.annotation.WebServlet;
import jakarta.servlet.http.HttpServlet;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;

/**
 * Servlet implementation class SimilarityServlet
 */
@WebServlet("/SimilarityServlet")
public class GenericSparqlServlet extends HttpServlet {
	private static final long serialVersionUID = 1L;

	/**
	 * Default constructor.
	 */
	public GenericSparqlServlet() {

	}

	/**
	 * @see HttpServlet#doGet(HttpServletRequest request, HttpServletResponse
	 *      response)
	 */
	protected void doGet(HttpServletRequest request, HttpServletResponse response)
			throws ServletException, IOException {
		boolean bRdf = (request.getParameter("rdf") != null);
		
		if (request.getParameter("dataset") != null) {
			Map<String, Set<String>> ret = new HashMap<String, Set<String>>();
			String endPoint = request.getParameter("dataset");
			String query = request.getParameter("query");
			ret.put(endPoint, execSparql(query, endPoint));
			String outStr = null;
			if (bRdf) {
				outStr = convRDF((HashMap) ret, 1.0);
			} else {
				outStr = convJSON((HashMap) ret);
			}
			response.getWriter().append(outStr);
		} else if ((request.getParameter("opt") != null) && (request.getParameter("opt").equals("exact"))) {
			Map<String, Set<String>> ret = null;
			String datasets = request.getParameter("datasets");
			String str[] = datasets.split(",");
			if (str.length > 1) {
				Set<String> setDs = new LinkedHashSet<String>();
				for (String p : str) {
					setDs.add(p.trim());
				}
				try {
					ret = generateDatasetSimilarity(setDs);
					String outStr = null;
					if (bRdf) {
						outStr = convRDF((HashMap) ret, 1.0);
					} else {
						outStr = convJSON((HashMap) ret);
					}
					response.getWriter().append(outStr);
					updateRelod(ret);
				} catch (Exception e) {
					e.printStackTrace();
				}
			}
		} else if ((request.getParameter("opt") != null) && (request.getParameter("opt").equals("dsim"))) {
			Map<String, Map<String, String>> ret = null;
			String datasets = request.getParameter("datasets");
			double simLevel = Double.parseDouble(request.getParameter("simlevel"));
			String str[] = datasets.split(",");
			if (str.length > 1) {
				Set<String> setDs = new LinkedHashSet<String>();
				for (String p : str) {
					setDs.add(p.trim());
				}
				try {
					ret = generateDatasetSimilarity(setDs, true, simLevel);
					String outStr = null;
					if (bRdf) {
						outStr = convRDF((HashMap) ret, simLevel);
					} else {
						outStr = convJSON((HashMap) ret);
					}
					response.getWriter().append(outStr);
					updateRelod(ret, simLevel);
				} catch (Exception e) {
					e.printStackTrace();
				}
			}
		}
	}

	/*
	 * Update the TSV file with current values from the new comparison.
	 * - Transform data to relational data.
	 * - SQL Update where the data is found.
	 * - Transform the data to TSV again.
	 */
	private void updateRelod(Map<String, Map<String, String>> ret, double simLevel) {
		// TODO Auto-generated method stub
		
	}
	
	/*
	 * Update the TSV file with current values from the new comparison.
	 */
	private void updateRelod(Map<String, Set<String>> ret) {
		// TODO Auto-generated method stub
		
	}

	private static IRI makeValidIRI(String iri) {
		URI uri = null;
		try {
	      URL url = new URL(iri);
	      String nullFragment = null;
	      uri = new URI(url.getProtocol(), url.getHost(), url.getPath(), url.getQuery(), nullFragment);
	      System.out.println("URI " + uri.toString() + " is OK");
	    } catch (MalformedURLException e) {
	      System.out.println("URL " + iri + " is a malformed URL");
	    } catch (URISyntaxException e) {
	      System.out.println("URI " + iri + " is a malformed URL");
	    }
		return Values.iri(uri.toString());
	}
	
	private String convRDF(HashMap map, double simLevel) {
		String rdfOut = "";
		if(map.toString().contains("---")) { //similar
			Map<String, Map<String, String>> ret = map;
			for (Map.Entry<String, Map<String, String>> entry : ret.entrySet()) {
				String graph = "<" + makeValidIRI("http://relod.org/DatasetPair#" + entry.getKey()) + ">";
				for (Map.Entry<String, String> trip : entry.getValue().entrySet()) {
					if(trip.getKey().toString().contains("CittÃ")) {
						System.out.println("PARAAAAA !!!!");
					}
					String triple = "<" + makeValidIRI(trip.getKey()) + "> <http://relod.org/similar#"+ simLevel+ "> <" + makeValidIRI(trip.getValue()) + ">";
					triple += " " + graph + " .\n";
					rdfOut += triple;
				}
			}
			return rdfOut;
		}  
		// exact
		Map<String, Set<String>> ret = map;
		for (Map.Entry<String, Set<String>> entry : ret.entrySet()) {
			String d[] = entry.getKey().split(",");
			String dSource = d[0].trim().replace("[", "");
			String dTarget = d[1].trim().replace("]", "");
			for (String propClass : entry.getValue()) {
				String triple = "<" + dSource + "> <"+ propClass + "> <" + dTarget + "> .\n";
				rdfOut += triple;
			}
		}
		return rdfOut;
	}

	private String convJSON(HashMap ret) {
		Gson gson = new Gson();
		Type gsonType = new TypeToken<HashMap>() {
		}.getType();
		return gson.toJson(ret, gsonType);
	}

	/**
	 * @see HttpServlet#doPost(HttpServletRequest request, HttpServletResponse
	 *      response)
	 */
	protected void doPost(HttpServletRequest request, HttpServletResponse response)
			throws ServletException, IOException {
		doGet(request, response);
	}

	public static Map<String, Set<String>> generateDatasetSimilarity(Set<String> datasets) {
		Map<String, Set<String>> mapExactMatch = new LinkedHashMap<String, Set<String>>();
		String[] array = datasets.stream().toArray(String[]::new);
		for (int i = 0; i < array.length; i++) {
			for (int j = i; j < array.length; j++) {
				try {
					if (array[i].equalsIgnoreCase(array[j]))
						continue;
					mapExactMatch.putAll(getExactMatches(array[i], array[j]));
				} catch (Exception e) {
					e.printStackTrace();
				}
			}

		}
		if (datasets.size() > 1) {
			return getOnlyMatchProps(datasets, mapExactMatch);
		}
		return mapExactMatch;
	}

	public static Map<String, Map<String, String>> generateDatasetSimilarity(Set<String> datasets, boolean bSimilar,
			double simLevel) {
		Map<String, Set<String>> mapExactMatch = new LinkedHashMap<String, Set<String>>();
		Map<String, Map<String, String>> mapSim = new LinkedHashMap<String, Map<String, String>>();
		String[] array = datasets.stream().toArray(String[]::new);
		for (int i = 0; i < array.length; i++) {
			for (int j = i; j < array.length; j++) {
				try {
					if (array[i].equalsIgnoreCase(array[j]))
						continue;
					mapExactMatch.putAll(getExactMatches(array[i], array[j]));
					if (bSimilar) {
						mapSim.putAll(getSimMatches(array[i], array[j], simLevel, mapExactMatch));
					}
				} catch (Exception e) {
					e.printStackTrace();
				}
			}

		}
		return mapSim;
	}

	private static Map<String, Set<String>> getOnlyMatchProps(Set<String> datasets,
			Map<String, Set<String>> mapExactMatch) {
		Map<String, Set<String>> ret = new LinkedHashMap<String, Set<String>>();
		ret.put(datasets.toString(), new HashSet<String>());
		Set<String> sRetain = new HashSet<String>();
		for (Map.Entry<String, Set<String>> entry : mapExactMatch.entrySet()) {
			sRetain.addAll(entry.getValue());
			sRetain.retainAll(entry.getValue());
//			for(String s: entry.getValue()) {
//				if(!sRetain.add(s)) {
//					ret.get(datasets.toString()).add(s);
//				}
//			}
		}
		ret.get(datasets.toString()).addAll(sRetain);
		return ret;
	}

	private static Map<String, Set<String>> getExactMatches(String source, String target)
			throws FileNotFoundException, UnsupportedEncodingException {
		final Set<String> propsSource = new LinkedHashSet<String>();
		final Set<String> propsTarget = new LinkedHashSet<String>();
		final Set<String> propsMatched = new LinkedHashSet<String>();
		final Map<String, Set<String>> mapExactMatch = new LinkedHashMap<String, Set<String>>();
		String s[] = source.split("/");
		String fSource = null;
		String fTarget = null;
		if (s.length > 2) {
			fSource = s[2] + "_" + s[s.length - 1];
		} else {
			fSource = s[s.length - 1];
		}
		String t[] = target.split("/");
		if (t.length > 2) {
			fTarget = t[2] + "_" + t[t.length - 1];
		} else {
			fTarget = t[t.length - 1];
		}
		// final String fileName = OUTPUT_DIR + "/" + fSource + "---" + fTarget +
		// "_Exact.txt";
		final String fileName = fSource + "---" + fTarget;
		propsSource.addAll(getProps(source, fSource));
		propsTarget.addAll(getProps(target, fTarget));
		if ((propsSource.size() < 1) || (propsTarget.size() < 1)) {
			return mapExactMatch;
		}

		propsSource.parallelStream().forEach(pSource -> {
			propsTarget.parallelStream().forEach(pTarget -> {
				if (pSource.trim().equalsIgnoreCase(pTarget.trim())) {
					propsMatched.add(pSource);
				}
			});
		});
		mapExactMatch.put(fileName, propsMatched);
		// writer.close();
		return mapExactMatch;
	}

	private static Map<String, Map<String, String>> getSimMatches(String source, String target, double threshold,
			Map<String, Set<String>> mapExactMatch) throws FileNotFoundException, UnsupportedEncodingException {
		final Set<String> propsSource = new LinkedHashSet<String>();
		final Set<String> propsTarget = new LinkedHashSet<String>();
		final Map<String, String> propsMatched = new LinkedHashMap<String, String>();
		final Map<String, Map<String, String>> mapSim = new LinkedHashMap<String, Map<String, String>>();

		String s[] = source.split("/");
		String fSource = null;
		String fTarget = null;
		if (s.length > 2) {
			fSource = s[2] + "_" + s[s.length - 1];
		} else {
			fSource = s[s.length - 1];
		}
		String t[] = target.split("/");
		if (t.length > 2) {
			fTarget = t[2] + "_" + t[t.length - 1];
		} else {
			fTarget = t[t.length - 1];
		}
		// final String fileName = OUTPUT_DIR + "/" + fSource + "---" + fTarget +
		// "_Sim.tsv";
		final String fileName = fSource + "---" + fTarget + "_Sim.tsv";
		propsSource.addAll(getProps(source, fSource));
		propsTarget.addAll(getProps(target, fTarget));

		for (Set<String> done : mapExactMatch.values()) {
			propsSource.removeAll(done);
			propsTarget.removeAll(done);
		}

		if ((propsSource.size() < 1) || (propsTarget.size() < 1)) {
			return mapSim;
		}

		// PrintWriter writer = new PrintWriter(fileName, "UTF-8");
		JaccardSimilarity sim = new JaccardSimilarity();
		propsSource.parallelStream().forEach(pSource -> {
			// for(String pSource : propsSource) {
			propsTarget.parallelStream().forEach(pTarget -> {
				// for(String pTarget : propsTarget) {
				String p1 = getURLName(pSource);
				String p2 = getURLName(pTarget);
				double dSim = sim.apply(p1, p2);
				if (dSim >= threshold) {
					propsMatched.put(pSource, pTarget);
				}
			});
			// }
		});
		// }
		mapSim.put(fileName.replaceAll(".tsv", ""), propsMatched);
		// writer.close();
		return mapSim;
	}

	public static String getURLName(String property) {
		String name = null;
		try {
			if (property.indexOf("#") > 0) {
				String[] str = property.split("#");
				name = str[str.length - 1];
				return name.replaceAll("\"", "");
			} else {
				String[] str = property.split("/");
				name = str[str.length - 1];
			}
		} catch (Exception e) {
			System.err.println("Problem with URI: " + property);
		}
		return name.replaceAll("\"", "");
	}

	private static Set<String> getProps(String source, String fName) {
		// Put Claus approach here...
		// instead of execute the SPARQL at the Dataset, we query the Dataset Catalog
		// from Claus to obtain a list of properties and classes.
		// This should be faster then query the dataset, because there are some
		// datasets/Endpoints extremely slow, more than 3 minutes.
		// return getPropsClaus(source)
		String cSparqlP = "Select ?p where {?s ?p ?o}";
		String cSparqlC = "select distinct ?p where {[] a ?p}";
		Set<String> ret = new LinkedHashSet<String>();
		ret.addAll(execSparql(cSparqlP, source));
		ret.addAll(execSparql(cSparqlC, source));
		return ret;
	}

	private static Set<String> execSparql(String cSparql, String source) {
		final Set<String> ret = new LinkedHashSet<String>();
		try {
			if (source.indexOf("sparql") > 0) {
				SPARQLRepository repo = new SPARQLRepository(source);
				RepositoryConnection conn = repo.getConnection();
				try {
					TupleQuery tQuery = conn.prepareTupleQuery(QueryLanguage.SPARQL, cSparql);
					TupleQueryResult rs = tQuery.evaluate();
					while (rs.hasNext()) {
						ret.add(rs.next().toString().trim().replaceAll("p=", "").replace("[", "").replace("]", ""));
					}
				} finally {
					conn.close();
				}
			} else {
				// ret.addAll(Util.execQueryRDFRes(cSparql, source, -1));
				String sJson = execSparqlFile(cSparql, source);
				sJson = sJson.replaceAll("=p", "");
				Type mapType = new TypeToken<Map<String, Set<String>>>() {
				}.getType();
				Map<String, Set<String>> son = new Gson().fromJson(sJson, mapType);
				for (Map.Entry<String, Set<String>> entry : son.entrySet()) {
					for (String s : entry.getValue()) {
						ret.add(s.trim());
					}
					// ret.addAll(entry.getValue());
				}
			}
		} catch (Exception e) {
			e.printStackTrace();
		}
		return ret;
	}

	private static String execSparqlFile(String cSparql, String source) throws InterruptedException, IOException {
		String sJson = null;

		String nURI = URLEncoder.encode(cSparql, "UTF-8");

		URL urlRelod = getFinalURL(new URL("http://w3id.org/relod/"));
		URL urlSearch = new URL(urlRelod.toString() + "sparqlservlet?dataset=" + source + "&query=" + nURI);
		// URL urlSearch = new URL(
		// "http://141.57.11.86:8082/DatasetMatchingWeb/sparqlservlet?dataset=" + source
		// + "&query=" + nURI);
		// URL urlSearch = new URL(
		// "http://w3id.org/relod/sparqlservlet?dataset=" + source + "&query=" + nURI);

		InputStreamReader reader = null;
		try {
			reader = new InputStreamReader(urlSearch.openStream());
		} catch (Exception e) {
			Thread.sleep(5000);
			reader = new InputStreamReader(urlSearch.openStream());
		}
		sJson = IOUtils.toString(reader);
		return sJson;
	}

	public static URL getFinalURL(URL url) {
		try {
			HttpURLConnection con = (HttpURLConnection) url.openConnection();
			con.setInstanceFollowRedirects(false);
			con.setRequestProperty("User-Agent",
					"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36");
			con.addRequestProperty("Accept-Language", "en-US,en;q=0.8");
			con.addRequestProperty("Referer", "https://www.google.com/");
			con.connect();
			// con.getInputStream();
			int resCode = con.getResponseCode();
			if (resCode == HttpURLConnection.HTTP_SEE_OTHER || resCode == HttpURLConnection.HTTP_MOVED_PERM
					|| resCode == HttpURLConnection.HTTP_MOVED_TEMP) {
				String Location = con.getHeaderField("Location");
				if (Location.startsWith("/")) {
					Location = url.getProtocol() + "://" + url.getHost() + Location;
				}
				return getFinalURL(new URL(Location));
			}
		} catch (Exception e) {
			System.out.println(e.getMessage());
		}
		return url;
	}
}
