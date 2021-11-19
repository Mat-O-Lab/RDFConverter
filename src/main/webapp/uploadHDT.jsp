<%@ page language="java" contentType="text/html; charset=UTF-8"
    pageEncoding="UTF-8"%>
<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
<title>Upload HDT files</title>
</head>
<body>
	<p>At the moment is only possible to add <a href="http://www.rdfhdt.org/" target="_blank" rel="noopener">HDT</a> files with a maximum size of 5 MB.</p>
	<p>Contact Andre Valdestilhas. Email: <a href="mailto:fimao@gmail.com">fimao@gmail.com</a></p>
    <form action="UploadHDTfile" method="post" enctype="multipart/form-data">
        <ul>
            <h3>File Upload:</h3>
            Select a file to upload: <br>
            <input type="file" name="file" size="50" accept=".hdt"  multiple> <br>
            <input type="submit" value="Upload File" />
        </ul>
    </form>
</body>
</html>