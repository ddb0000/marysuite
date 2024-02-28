from http.server import BaseHTTPRequestHandler
from urllib import parse
import json

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path
        url_components = parse.urlsplit(path)
        query_string_list = parse.parse_qsl(url_components.query)
        query_dict = dict(query_string_list)

        # Example: Retrieve herb entries logic here

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"message": "Hello from your Flask app as a serverless function!"}).encode())
