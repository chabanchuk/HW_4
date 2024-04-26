import mimetypes
import json
import logging
import socket
import threading
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler

BASE_DIR = Path()
STORAGE_DIR = BASE_DIR / 'storage'
BUFFER_SIZE = 1024
HTTP_PORT = 3000
SOCKET_PORT = 5000
HTTP_HOST = '0.0.0.0'
SOCKET_HOST = '127.0.0.1'

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(threadName)s - %(message)s')


class GetRequestHandler:
    def __init__(self, request):
        self.request = request

    def handle(self):
        route = urlparse(self.request.path)
        match route.path:
            case '/':
                self.send_response('index.html')
            case '/message':
                self.send_response('message.html')
            case _:
                file = BASE_DIR / route.path[1:]
                if file.exists():
                    self.send_static(file)
                else:
                    self.send_response('error.html', status_code=404)

    def send_response(self, filename, status_code=200):
        self.request.send_response(status_code)
        if isinstance(filename, Path):
            filename_str = str(filename)
        else:
            filename_str = filename
        if filename_str.endswith('.html'):
            self.request.send_header('Content-Type', 'text/html')
        else:
            mime_type, _ = mimetypes.guess_type(filename_str)
            if mime_type:
                self.request.send_header('Content-Type', mime_type)
            else:
                self.request.send_header('Content-Type', 'application/octet-stream')
        self.request.end_headers()
        with open(filename_str, 'rb') as file:
            self.request.wfile.write(file.read())

    def send_static(self, filename):
        self.send_response(filename)

class PostRequestHandler:
    def __init__(self, request):
        self.request = request

    def handle(self):
        content_length = int(self.request.headers['Content-Length'])
        post_data = self.request.rfile.read(content_length)
        self.forward_form_data(post_data)

        self.request.send_response(303)
        self.request.send_header('Location', '/message')
        self.request.end_headers()

    def forward_form_data(self, post_data):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        server_address = (SOCKET_HOST, SOCKET_PORT)
        sock.sendto(post_data, server_address)
        sock.close()


class HomeWork_4Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        handler = GetRequestHandler(self)
        handler.handle()

    def do_POST(self):
        handler = PostRequestHandler(self)
        handler.handle()


def run_html_server():
    address = (HTTP_HOST, HTTP_PORT)
    http_server = HTTPServer(address, HomeWork_4Handler)
    try:
        http_server.serve_forever()
        logging.info('Run http_server')
    except KeyboardInterrupt:
        pass
    finally:
        http_server.server_close()
        
def start_socket_server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_address = (SOCKET_HOST, SOCKET_PORT)
    sock.bind(server_address)

    while True:
        data, _ = sock.recvfrom(BUFFER_SIZE)
        if not data:
            break
        form_data = parse_qs(data.decode())
        save_to_json(form_data)
        logging.info('Received data and saved to JSON')
        
def save_to_json(form_data):
    message_data = {
        'username': form_data.get('username', [''])[0],
        'message': form_data.get('message', [''])[0]
    }
    
    current_time = datetime.now().isoformat()
    
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    file_path = STORAGE_DIR / 'data.json'
    
    if file_path.exists():
        with open(file_path, 'r') as file:
            try:
                existing_data = json.load(file)
            except json.JSONDecodeError:
                existing_data = {}
    else:
        existing_data = {}

    existing_data[current_time] = message_data
    with open(file_path, 'w') as file:
        json.dump(existing_data, file, indent=4)
        logging.info('Data written to data.json')


def main():
    http_thread = threading.Thread(target=run_html_server)
    socket_thread = threading.Thread(target=start_socket_server)

    http_thread.start()
    socket_thread.start()

    http_thread.join()
    socket_thread.join()

if __name__ == '__main__':
    main()