"""Exercise the real HTTP entry point; MAX transport is mocked, never contacted."""
import io
import json
import re
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from http.server import ThreadingHTTPServer

from server import App, CONSENT_VERSION, RETENTION, handler_for


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.app = App(str(Path(self.temp.name) / 'db.sqlite'), 'https://saydent.test', 'secret', '-123')
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), handler_for(self.app))
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.start()
        self.url = f'http://127.0.0.1:{self.server.server_port}'
        self.payload = dict(name='Анна', phone='+7 (999) 123-45-67', consent=True,
                            consent_version=CONSENT_VERSION, request_id='12345678-1234-1234-1234-123456789abc')

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temp.cleanup()

    def post(self, payload=None, origin='https://saydent.test', raw=None):
        request = Request(self.url + '/api/appointments',
                          data=raw if raw is not None else json.dumps(payload or self.payload).encode(),
                          headers={'Content-Type': 'application/json', 'Origin': origin})
        try:
            return urlopen(request)
        except HTTPError as error:
            return error

    def test_accept_duplicate_restart_and_retry_delivery(self):
        self.payload['name'] = 'Анна <А>'
        self.assertEqual(self.post().status, 200)
        self.assertEqual(self.post().status, 200)
        with self.app.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM appointments').fetchone()[0], 1)
        with patch('server.urlopen', side_effect=TimeoutError):
            self.app.notify_one()
        with self.app.connect() as db:
            self.assertEqual(db.execute('SELECT sent, attempts FROM appointments').fetchone(), (None, 1))
            db.execute('UPDATE appointments SET retry_at = 0')
        restarted = App(self.app.database, self.app.origin, self.app.token, self.app.chat_id)
        response = io.BytesIO(b'{"message":{"body":{"mid":"msg-1"}}}')
        with patch('server.urlopen', return_value=response) as send:
            restarted.notify_one()
            request = send.call_args.args[0]
            self.assertEqual(request.full_url, 'https://platform-api2.max.ru/messages?chat_id=-123')
            self.assertEqual(request.get_header('Authorization'), 'secret')
            message = json.loads(request.data)
            self.assertEqual(message['format'], 'html')
            self.assertIn('Имя: Анна &lt;А&gt;', message['text'])
            self.assertIn('Телефон: <a href="tel:+79991234567">+79991234567</a>', message['text'])
            restarted.notify_one()
            self.assertEqual(send.call_count, 1)

    def test_form_and_consent_publish_version_accepted_by_server(self):
        with urlopen(self.url + '/script.js') as response:
            script = response.read().decode()
        self.assertEqual(re.search(r"consent_version: '([^']+)'", script)[1], CONSENT_VERSION)
        with urlopen(self.url + '/consent.html') as response:
            self.assertIn(f'datetime="{CONSENT_VERSION}"', response.read().decode())

    def test_reject_invalid_requests_and_rate_limit(self):
        for field, value in [('consent', False), ('consent', 1), ('consent_version', 'old'),
                             ('name', 'Анна2'), ('phone', '123'), ('request_id', 'bad')]:
            with self.subTest(field=field, value=value):
                self.assertEqual(self.post({**self.payload, field: value}).status, 400)
        self.assertEqual(self.post(origin='https://evil.test').status, 403)
        self.assertEqual(self.post(raw=b'[').status, 400)
        self.assertEqual(self.post(raw=b' ' * 4097).status, 413)
        self.assertEqual(self.post().status, 200)
        self.assertEqual(self.post({**self.payload, 'request_id': '22345678-1234-1234-1234-123456789abc'}).status, 429)
        self.assertEqual(self.post({**self.payload, 'name': 'Борис'}).status, 400)

    def test_max_error_body_is_not_delivery_and_retention(self):
        self.app.accept(self.payload)
        with patch('server.urlopen', return_value=io.BytesIO(b'{"success":false,"message":"failed"}')):
            self.app.notify_one()
        with self.app.connect() as db:
            self.assertIsNone(db.execute('SELECT sent FROM appointments').fetchone()[0])
            db.execute('UPDATE appointments SET created = ?', (time.time() - RETENTION - 1,))
        self.app.notify_one()
        with self.app.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM appointments').fetchone()[0], 0)

    def test_only_public_files_are_served(self):
        for path in ['/', '/script.js', '/consent.html', '/saydent-license.pdf', '/images/smile.webp']:
            with urlopen(self.url + path) as response:
                self.assertEqual(response.status, 200)
                response.read()
        for path in ['/.git/config', '/server.py', '/data/appointments.sqlite3', '/README.md', '/.env', '/deploy/consents/2026-11-17.html',
                     '/tests/test_server.py', '/images/../server.py', '/%2e%2e/server.py', '/images/']:
            with self.subTest(path=path), self.assertRaises(HTTPError) as error:
                urlopen(self.url + path)
            self.assertEqual(error.exception.code, 404)


if __name__ == '__main__':
    unittest.main()
