#!/usr/bin/env python3
"""
Retro Vault — Serveur local avec proxy CORS pour Archive.org.
Lance avec : python3 server.py
"""

import http.server
import urllib.request
import urllib.parse
import urllib.error
import os
import sys

PORT = 8236
CHUNK_SIZE = 64 * 1024  # 64 KB

ALLOWED_DOMAINS = [
    'archive.org',
    'cdn.emulatorjs.org',
    'thumbnails.libretro.com',
]


class RetroVaultHandler(http.server.SimpleHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path.startswith('/proxy'):
            self._handle_proxy(parsed.query)
        else:
            # Marquer les pages HTML pour injecter COOP/COEP
            path = parsed.path.rstrip('/')
            if not path or path.endswith('.html'):
                self._inject_isolation = True
            super().do_GET()

    def end_headers(self):
        if getattr(self, '_inject_isolation', False):
            self.send_header('Cross-Origin-Opener-Policy', 'same-origin')
            self.send_header('Cross-Origin-Embedder-Policy', 'credentialless')
            self._inject_isolation = False
        super().end_headers()

    def do_HEAD(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path.startswith('/proxy'):
            self._handle_proxy(parsed.query, head_only=True)
        else:
            path = parsed.path.rstrip('/')
            if not path or path.endswith('.html'):
                self._inject_isolation = True
            super().do_HEAD()

    def _cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, HEAD, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Range, Content-Type, Accept')
        self.send_header('Access-Control-Expose-Headers', 'Content-Length, Content-Range, Content-Type')

    def _handle_proxy(self, query_string, head_only=False):
        params = urllib.parse.parse_qs(query_string)
        target = params.get('url', [None])[0]

        if not target:
            self.send_error(400, 'Missing url parameter')
            return

        # Sécurité : uniquement les domaines autorisés
        parsed_target = urllib.parse.urlparse(target)
        host = parsed_target.netloc.lower()
        if not any(domain in host for domain in ALLOWED_DOMAINS):
            self.send_error(403, f'Domain not allowed: {host}')
            return

        # Normalise le path : decode d'abord (évite la double-encodage) puis re-encode
        # parse_qs décode %2520 → %20 ; on doit alors decoder %20 → espace puis re-encoder proprement
        safe_path = urllib.parse.quote(urllib.parse.unquote(parsed_target.path), safe='/:@!$&\'()*+,;=-._~')
        target = parsed_target._replace(path=safe_path).geturl()

        try:
            req = urllib.request.Request(
                target,
                headers={
                    'User-Agent': (
                        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                        'AppleWebKit/537.36 (KHTML, like Gecko) '
                        'Chrome/120.0.0.0 Safari/537.36'
                    ),
                    'Accept': '*/*',
                    'Accept-Encoding': 'identity',
                }
            )

            # Passe le Range header si présent (pour les requêtes partielles)
            if 'Range' in self.headers:
                req.add_header('Range', self.headers['Range'])

            response = urllib.request.urlopen(req, timeout=60)

            status = response.status
            content_type = response.headers.get('Content-Type', 'application/octet-stream')
            content_length = response.headers.get('Content-Length')
            content_range = response.headers.get('Content-Range')

            self.send_response(status)
            self.send_header('Content-Type', content_type)
            if content_length:
                self.send_header('Content-Length', content_length)
            if content_range:
                self.send_header('Content-Range', content_range)
            self.send_header('Cache-Control', 'public, max-age=86400')
            self._cors_headers()
            self.end_headers()

            if not head_only:
                while True:
                    chunk = response.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    try:
                        self.wfile.write(chunk)
                    except BrokenPipeError:
                        break

        except urllib.error.HTTPError as e:
            self.send_error(e.code, f'Upstream: {e.reason}')
        except urllib.error.URLError as e:
            self.send_error(502, f'Cannot reach upstream: {e.reason}')
        except Exception as e:
            self.send_error(500, str(e))

    def log_message(self, fmt, *args):
        # N'affiche que les requêtes proxy et les erreurs (pas tout le bruit static)
        msg = fmt % args
        if '/proxy' in self.path or (args and str(args[1]) not in ('200', '304')):
            sys.stderr.write(f'[RetroVault] {self.address_string()} - {msg}\n')


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    server_class = http.server.ThreadingHTTPServer
    handler = RetroVaultHandler

    httpd = server_class(('', PORT), handler)
    print(f'')
    print(f'  ██████╗ ███████╗████████╗██████╗  ██████╗      ██╗   ██╗ █████╗ ██╗   ██╗██╗  ████████╗')
    print(f'  ██╔══██╗██╔════╝╚══██╔══╝██╔══██╗██╔═══██╗     ██║   ██║██╔══██╗██║   ██║██║  ╚══██╔══╝')
    print(f'  ██████╔╝█████╗     ██║   ██████╔╝██║   ██║     ██║   ██║███████║██║   ██║██║     ██║   ')
    print(f'  ██╔══██╗██╔══╝     ██║   ██╔══██╗██║   ██║     ╚██╗ ██╔╝██╔══██║██║   ██║██║     ██║   ')
    print(f'  ██║  ██║███████╗   ██║   ██║  ██║╚██████╔╝      ╚████╔╝ ██║  ██║╚██████╔╝███████╗██║   ')
    print(f'  ╚═╝  ╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝ ╚═════╝        ╚═══╝  ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝   ')
    print(f'')
    print(f'  Serveur local    →  http://localhost:{PORT}')
    print(f'  Proxy CORS actif →  Archive.org + libretro thumbnails')
    print(f'  Arrêt            →  Ctrl+C')
    print(f'')

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print('\n  Serveur arrêté.')
        httpd.server_close()


if __name__ == '__main__':
    main()
