import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

class ExternalDownloadHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith('/add'):
            query = urlparse(self.path).query
            params = parse_qs(query)
            url = params.get('url', [None])[0]
            if url and hasattr(self.server, 'manager'):
                # Use root.after to safely trigger UI from another thread
                manager = self.server.manager
                manager.root.after(0, lambda: manager.handle_external_request(url))
                self.send_response(200)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(b"OK")
                return
        self.send_response(404)
        self.end_headers()
    
    def log_message(self, format, *args):
        pass # Silencing logs to keep terminal clean

class SilentHTTPServer(HTTPServer):
    def __init__(self, server_address, RequestHandlerClass, manager):
        self.manager = manager
        super().__init__(server_address, RequestHandlerClass)

    def handle_error(self, request, client_address):
        # Suppress the messy traceback for ConnectionResetError [WinError 10054]
        pass

def start_server(manager):
    def run_server():
        try:
            server = SilentHTTPServer(('127.0.0.1', 5555), ExternalDownloadHandler, manager)
            server.serve_forever()
        except Exception: 
            pass

    threading.Thread(target=run_server, daemon=True).start()
