"""SayDent form receiver and durable MAX notification queue (Python 3.10+)."""
import json
import logging
import os
from pathlib import Path
import re
import sqlite3
import ssl
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from html import escape
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
CONSENT_VERSION = '2026-11-18'
RETENTION = 30 * 86400


class App:
    def __init__(self, database, origin, token, chat_id):
        self.database = database
        self.origin = origin.rstrip('/')
        self.token = token
        self.chat_id = chat_id
        self.max_tls = ssl.create_default_context()
        self.max_tls.load_verify_locations(cafile=str(ROOT / 'deploy' / 'russian-trusted-root-ca.pem'))
        with self.connect() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS appointments (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, phone TEXT NOT NULL,
                consent_version TEXT NOT NULL, created REAL NOT NULL,
                sent REAL, attempts INTEGER NOT NULL DEFAULT 0, retry_at REAL NOT NULL DEFAULT 0)''')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.database, timeout=10)
        try:
            db.execute('PRAGMA secure_delete = ON')
            with db:
                yield db
        finally:
            db.close()

    def accept(self, data):
        if not isinstance(data, dict):
            raise ValueError('Некорректная заявка.')
        name, phone, request_id = (data.get(key) for key in ('name', 'phone', 'request_id'))
        if (not isinstance(name, str) or not 1 <= len(name.strip()) <= 100
                or any(char.isdecimal() or ord(char) < 32 for char in name)):
            raise ValueError('Укажите имя без цифр, до 100 символов.')
        if not isinstance(phone, str) or not re.fullmatch(r'\+?(?:[ ()-]*[0-9]){10,15}[ ()-]*', phone):
            raise ValueError('Укажите телефон: от 10 до 15 цифр.')
        if data.get('consent') is not True or data.get('consent_version') != CONSENT_VERSION:
            raise ValueError('Подтвердите актуальное согласие на обработку данных.')
        if not isinstance(request_id, str) or not re.fullmatch(r'[0-9a-f-]{36}', request_id):
            raise ValueError('Некорректный идентификатор заявки.')
        phone = re.sub(r'[^0-9]', '', phone)
        if len(phone) == 11 and phone.startswith('8'):
            phone = '7' + phone[1:]
        now = time.time()
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('DELETE FROM appointments WHERE created < ?', (now - RETENTION,))
            existing = db.execute('SELECT name, phone FROM appointments WHERE id = ?', (request_id,)).fetchone()
            if existing:
                if existing != (name.strip(), phone):
                    raise ValueError('Идентификатор уже использован для другой заявки.')
                return
            if db.execute('SELECT 1 FROM appointments WHERE phone = ? AND created > ?', (phone, now - 600)).fetchone():
                raise OverflowError('Заявка с этим телефоном уже принята. Дождитесь звонка клиники.')
            if db.execute('SELECT count(*) FROM appointments WHERE created > ?', (now - 60,)).fetchone()[0] >= 20:
                raise OverflowError('Слишком много заявок. Повторите через минуту.')
            db.execute('INSERT INTO appointments(id, name, phone, consent_version, created) VALUES (?, ?, ?, ?, ?)',
                       (request_id, name.strip(), phone, CONSENT_VERSION, now))

    def notify_one(self):
        now = time.time()
        with self.connect() as db:
            db.execute('DELETE FROM appointments WHERE created < ?', (now - RETENTION,))
            row = db.execute('SELECT id, name, phone, created, attempts FROM appointments WHERE sent IS NULL AND retry_at <= ? ORDER BY created LIMIT 1', (now,)).fetchone()
        if not row:
            return
        request_id, name, phone, created, attempts = row
        stamp = datetime.fromtimestamp(created, timezone.utc).strftime('%d.%m.%Y %H:%M UTC')
        text = (f'Новая заявка SayDent\nИмя: {escape(name)}\n'
                f'Телефон: <a href="tel:+{phone}">+{phone}</a>\n'
                f'Время: {stamp}\nНомер заявки: {request_id}\nСвяжитесь с пациентом для согласования записи.')
        request = Request('https://platform-api2.max.ru/messages?chat_id=' + self.chat_id,
                          data=json.dumps({'text': text, 'format': 'html'}, ensure_ascii=False).encode(),
                          headers={'Content-Type': 'application/json'}, method='POST')
        request.add_unredirected_header('Authorization', self.token)
        try:
            with urlopen(request, timeout=15, context=self.max_tls) as response:
                result = json.load(response)
            if not isinstance(result, dict) or result.get('success') is False:
                raise ValueError('MAX rejected notification')
            message = result.get('message')
            body = message.get('body') if isinstance(message, dict) else None
            if not isinstance(body, dict) or not isinstance(body.get('mid'), str) or not body['mid']:
                raise ValueError('MAX did not confirm delivery')
        except Exception as error:
            # Log the failure class/status only. Bodies and URLs can contain personal data.
            logging.warning('MAX delivery failed (%s, status %s); queued for retry',
                            type(error).__name__, getattr(error, 'code', None))
            with self.connect() as db:
                db.execute('UPDATE appointments SET attempts = attempts + 1, retry_at = ? WHERE id = ?',
                           (now + min(3600, 30 * 2 ** min(attempts, 7)), request_id))
        else:
            with self.connect() as db:
                db.execute('UPDATE appointments SET sent = ? WHERE id = ?', (time.time(), request_id))


def handler_for(app):
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(ROOT), **kwargs)

        def log_message(self, *args):
            pass  # URLs can contain personal data; do not write access logs here.

        def reply(self, status, message):
            body = json.dumps({'ok': status == 200, 'message': message}, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            self.connection.settimeout(10)
            if self.path != '/api/appointments':
                return self.reply(404, 'Не найдено.')
            if self.headers.get('Origin') != app.origin:
                return self.reply(403, 'Недопустимый источник запроса.')
            if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                return self.reply(415, 'Ожидается JSON.')
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 4096 or self.headers.get('Transfer-Encoding'):
                    return self.reply(413, 'Недопустимый размер запроса.')
                app.accept(json.loads(self.rfile.read(length)))
            except (ValueError, RecursionError):
                return self.reply(400, 'Проверьте имя, телефон и согласие. Обновите страницу при необходимости.')
            except OverflowError as error:
                return self.reply(429, str(error))
            except (sqlite3.Error, OSError):
                logging.error('Appointment storage unavailable')
                return self.reply(503, 'Не удалось принять заявку. Повторите позже или позвоните в клинику.')
            self.reply(200, 'Заявка принята. Администратор свяжется с вами для подтверждения записи.')

        def allowed_static(self):
            path = unquote(urlsplit(self.path).path)
            if path == '/':
                path = '/index.html'
            target = (ROOT / path.lstrip('/')).resolve()
            public = {'index.html', 'privacy.html', 'consent.html', 'license.html', 'style.css', 'script.js', 'saydent-license.pdf'}
            return (target.parent == ROOT and target.name in public or
                    target.parent == ROOT / 'images' and target.suffix in {'.png', '.jpg', '.webp'}) and target.is_file()

        def do_GET(self):
            if not self.allowed_static():
                return self.reply(404, 'Не найдено.')
            super().do_GET()

        def do_HEAD(self):
            if not self.allowed_static():
                return self.reply(404, 'Не найдено.')
            super().do_HEAD()
    return Handler


def main():
    os.umask(0o077)
    token = os.environ.get('MAX_BOT_TOKEN', '')
    chat_id = os.environ.get('MAX_CHAT_ID', '')
    origin = os.environ.get('PUBLIC_ORIGIN', '').rstrip('/')
    if not token or not re.fullmatch(r'-?[0-9]+', chat_id) or not re.fullmatch(r'https?://[^/]+', origin):
        raise SystemExit('Set MAX_BOT_TOKEN, numeric MAX_CHAT_ID and PUBLIC_ORIGIN (scheme://host[:port]).')
    database = Path(os.environ.get('DATABASE_PATH', str(ROOT / 'data' / 'appointments.sqlite3')))
    database.parent.mkdir(parents=True, exist_ok=True)
    app = App(str(database), origin, token, chat_id)
    stop = threading.Event()

    def deliver():
        while not stop.is_set():
            try:
                app.notify_one()
            except Exception:
                logging.error('Notification worker failed; retrying')
            stop.wait(1)

    worker = threading.Thread(target=deliver, daemon=True)
    server = ThreadingHTTPServer(('127.0.0.1', int(os.environ.get('PORT', '8765'))), handler_for(app))
    worker.start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        server.server_close()
        worker.join(timeout=20)


if __name__ == '__main__':
    main()
