package com.bam.servlet;

import jakarta.servlet.ServletException;
import jakarta.servlet.annotation.MultipartConfig;
import jakarta.servlet.annotation.WebServlet;
import jakarta.servlet.http.HttpServlet;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.servlet.http.Part;
import org.apache.commons.io.IOUtils;
import org.eclipse.rdf4j.model.Model;
import org.eclipse.rdf4j.model.vocabulary.RDF4J;
import org.eclipse.rdf4j.repository.sail.SailRepository;
import org.eclipse.rdf4j.repository.sail.SailRepositoryConnection;
import org.eclipse.rdf4j.rio.RDFFormat;
import org.eclipse.rdf4j.rio.Rio;
import org.eclipse.rdf4j.sail.memory.MemoryStore;
import org.eclipse.rdf4j.sail.shacl.ShaclSail;
import org.eclipse.rdf4j.sail.shacl.ShaclSailValidationException;

import java.io.*;
import java.nio.charset.StandardCharsets;

@WebServlet("/RDFValidator")
@MultipartConfig
public class RDFValidator extends HttpServlet {

    protected void doPost(HttpServletRequest request, HttpServletResponse response) throws IOException, ServletException {
        Part rdfPart = request.getPart("rdf");
        InputStream rdfStream = rdfPart.getInputStream();
        Part shapePart = request.getPart("shaclShape");
        InputStream shapeStream = shapePart.getInputStream();

        String rdf = IOUtils.toString(rdfStream, StandardCharsets.UTF_8);
        String shaclShape = IOUtils.toString(shapeStream, StandardCharsets.UTF_8);

        PrintWriter writer = response.getWriter();

        writer.append(validateRDF(rdf, shaclShape));
    }

    protected static String validateRDF(String rdf, String shaclShapes) throws UnsupportedEncodingException {
        String ret = null;
        boolean bValid = true;
        ShaclSail shaclSail = new ShaclSail(new MemoryStore());

        SailRepository sailRepository = new SailRepository(shaclSail);
        sailRepository.init();
        try {
            SailRepositoryConnection connection = sailRepository.getConnection();
            connection.begin();
            StringReader shaclRules = new StringReader(shaclShapes);
            connection.add(shaclRules, "", RDFFormat.TURTLE, RDF4J.SHACL_SHAPE_GRAPH);
            connection.commit();
            connection.begin();
            StringReader rdfData = new StringReader(rdf);
            connection.add(rdfData, "", RDFFormat.TURTLE);
            connection.commit();
        } catch (Exception exception) {
            Throwable cause = exception.getCause();
            bValid = false;
            if (cause instanceof ShaclSailValidationException) {
                Model validationReportModel = ((ShaclSailValidationException) cause).validationReportAsModel();
                ByteArrayOutputStream baos = new ByteArrayOutputStream();
                Rio.write(validationReportModel, baos, RDFFormat.TURTLE);
                ret = baos.toString(String.valueOf(StandardCharsets.UTF_8));
            }
            if (cause == null) {
                ret = "fail: " + exception.getMessage();
            } else {
                ret = "fail: " + ret;
            }
        }
        if (bValid) {
            ret = "VALID";
        }

        return ret;
    }
}
