import http.server
import socketserver
import os

PORT = int(os.environ.get('STATUS_PORT', '9090'))
STATUS_FILE = os.environ.get('BACKUP_STATUS_FILE', '/backups/backup-status.json')

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path in ('/', '/status'):
            if os.path.exists(STATUS_FILE):
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                with open(STATUS_FILE, 'rb') as fh:
                    self.wfile.write(fh.read())
                return
            else:
                self.send_response(404)
                self.end_headers()
                return
        return super().do_GET()

if __name__ == '__main__':
    with socketserver.TCPServer(('', PORT), Handler) as httpd:
        print(f'serve-status: serving {STATUS_FILE} on port {PORT}')
        httpd.serve_forever()
