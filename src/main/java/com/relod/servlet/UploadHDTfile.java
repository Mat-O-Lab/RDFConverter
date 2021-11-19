package com.relod.servlet;


import java.io.File;
import java.io.IOException;
import java.util.List;

import org.apache.tomcat.util.http.fileupload.FileItem;
import org.apache.tomcat.util.http.fileupload.FileItemFactory;
import org.apache.tomcat.util.http.fileupload.FileUploadException;
import org.apache.tomcat.util.http.fileupload.disk.DiskFileItemFactory;
import org.apache.tomcat.util.http.fileupload.servlet.ServletFileUpload;
import org.apache.tomcat.util.http.fileupload.servlet.ServletRequestContext;

import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServlet;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;

/**
 * Servlet implementation class UploadHDTfile
 */
public class UploadHDTfile extends HttpServlet {
	private static final long serialVersionUID = 1L;

	/**
	 * @see HttpServlet#HttpServlet()
	 */
	public UploadHDTfile() {
		super();
		// TODO Auto-generated constructor stub
	}

	/**
	 * @see HttpServlet#doGet(HttpServletRequest request, HttpServletResponse
	 *      response)
	 */
	protected void doGet(HttpServletRequest request, HttpServletResponse response)
			throws ServletException, IOException {
		// TODO Auto-generated method stub
		response.getWriter().append("Served at: ").append(request.getContextPath());
	}

	/**
	 * @see HttpServlet#doPost(HttpServletRequest request, HttpServletResponse
	 *      response)
	 */
	protected void doPost(HttpServletRequest request, HttpServletResponse response)
			throws ServletException, IOException {
		boolean isMultipart = ServletFileUpload.isMultipartContent(request);
		
		if (isMultipart) {
			// Create a factory for disk-based file items
			FileItemFactory factory = new DiskFileItemFactory();

			// Create a new file upload handler
			ServletFileUpload upload = new ServletFileUpload(factory);

			try {
				// Parse the request
				List<FileItem> items = upload.parseRequest(new ServletRequestContext(request));
				for (FileItem item : items) {
					if (!item.isFormField()) {
						String fileName = item.getName();
						if(!fileName.endsWith(".hdt")) continue;
						//String root = getServletContext().getRealPath("/");
						
						String dirHDT = System.getProperty("user.home") + "/hdtDatasets";
						//String dirHDT = "/media/andre/Seagate/personalDatasets";
						if(request.getSession().getAttribute("dirHDT") != null){
							dirHDT = request.getSession().getAttribute("dirHDT").toString();
						}
						File path = new File(dirHDT);
//						String root = System.getProperty("user.home");
//						File path = new File(root + "/hdtDatasets");
						if (!path.exists()) {
							boolean status = path.mkdirs();
						}
						File uploadedFile = new File(path + "/" + fileName);
						System.out.println(uploadedFile.getAbsolutePath());
						item.write(uploadedFile);
						response.getOutputStream().println(uploadedFile.getAbsolutePath());
					}
				}
			} catch (FileUploadException e) {
				e.printStackTrace();
			} catch (Exception e) {
				e.printStackTrace();
			}
		}
	}

}

