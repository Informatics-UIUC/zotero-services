import cherrypy
from cherrypy import expose
import socket
import tempfile
import subprocess
import os

# IP address and port to bind to (0.0.0.0 = bind to all)
hostname = "0.0.0.0"
servicePort = 9999

# The path to Java executable
java = "java"

# Options to pass to Java
javaopts = "-Xmx1g"

# The path to the Meandre runtime executor to use
zzre = "zzre-1.4.12.jar"

# The port range that can be used to allocate to running jobs
ports = range(10000, 20000)

class ZoteroService(object):
	def error(self, msg, ex=None):
		print "Error: %s\nException: %s" % (msg, ex)
		return "<!DOCTYPE html>\n<html>\n<head><title>Error</title></head>\n<body>Error: %s</body>\n</html>\n" % msg

	@expose
	def submit(self, zoterordf=None, flow=None):
		global ports

		if flow is None:
			return self.error("Incorrect SEASR configuration - missing flow information")

		if zoterordf is None:
			return self.error("Missing Zotero RDF data from request!")

		flowFile = "%s.mau" % flow

		if not os.path.exists(flowFile):
			return self.error("The requested flow does not exist on the server: %s" % flow)

		print "Executing flow: %s" % flowFile

		rdfFile = tempfile.NamedTemporaryFile(suffix = ".rdf")
		rdfFile.write(zoterordf.encode("utf-8"))
		rdfFile.flush()

		flow_stdout = tempfile.NamedTemporaryFile(suffix = ".out")
		flow_stderr = tempfile.NamedTemporaryFile(suffix = ".err")

		outFile = tempfile.mktemp(suffix = ".html")
		try:
			port = ports.pop()
		except KeyError as ex:
			return self.error("Job queue is full. Please try again later.")

		print "Using RDF file: %s" % rdfFile.name
		print "Using outfile: %s" % outFile
		print "Using port: %d" % port

		cmd = [
			java, javaopts,
			"-jar", zzre,
			flowFile,
			"--port", "%d" % port,
			"--param", "rdf=file://%s" % rdfFile.name,
			"--param", "output=file://%s" % outFile
		]

		try:
			subprocess.check_call(cmd, stdout = flow_stdout, stderr = flow_stderr)
		except subprocess.CalledProcessError as ex:
			return self.error("Flow execution error", ex)
		finally:
			ports.append(port)

		print "stdout: %s" % flow_stdout.name
		print "stderr: %s" % flow_stderr.name

		resultFile = open(outFile, "r")
		try:
			return resultFile.read()
		finally:
			resultFile.close()
			os.remove(outFile)

cherrypy.config.update({'server.socket_host': hostname, 'server.socket_port': servicePort, })
cherrypy.quickstart(ZoteroService())
