import importlib.util
import pathlib
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch


spec = importlib.util.spec_from_file_location("vozes", pathlib.Path(__file__).parents[1] / "scripts" / "vozes.py")
vozes = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vozes)


class DestinosDeVozTest(unittest.TestCase):
    def test_remoto_em_http_e_credenciais_na_url_sao_recusados_antes_da_rede(self):
        with patch.object(vozes.urllib.request, "build_opener") as opener:
            for url in ("http://example.com/v1", "https://user:password@example.com/v1", "file:///tmp/x"):
                with self.subTest(url=url), self.assertRaises(ValueError):
                    vozes._req(url, headers={"Authorization": "Bearer teste"})
            opener.assert_not_called()

    def test_https_remoto_e_http_loopback_sao_aceitos(self):
        for url in ("https://example.com/v1", "http://127.0.0.1:3900/v1", "http://[::1]:3900/v1", "http://localhost:3900/v1"):
            with self.subTest(url=url):
                vozes._validar_destino(url)

    def test_redirecionamento_nao_reenvia_requisicao(self):
        recebidas = []

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                recebidas.append(self.path)
                self.send_response(302 if self.path == "/origem" else 200)
                if self.path == "/origem":
                    self.send_header("Location", "/destino")
                self.end_headers()

            def log_message(self, *args):
                pass

        servidor = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=servidor.serve_forever, daemon=True)
        thread.start()
        try:
            with self.assertRaises(vozes.urllib.error.HTTPError):
                vozes._req(f"http://127.0.0.1:{servidor.server_port}/origem", headers={"Authorization": "Bearer teste"})
            self.assertEqual(recebidas, ["/origem"])
        finally:
            servidor.shutdown()
            servidor.server_close()
            thread.join()


if __name__ == "__main__":
    unittest.main()
