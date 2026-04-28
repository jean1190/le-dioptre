from http.server import BaseHTTPRequestHandler
import json


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps(
            {
                "status": "retired",
                "resource": "public_article_archive",
                "replacement": "/.well-known/namilele-interface.json",
                "archive_public": False,
            },
            ensure_ascii=False,
        ).encode("utf-8")
        self.send_response(410)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
