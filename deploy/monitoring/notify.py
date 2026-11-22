"""Send an infrastructure notification independently of the appointment server."""
import json
import os
from pathlib import Path
import re
import ssl
import sys
from urllib.request import Request, urlopen

MESSAGES = {
    'saydent': 'Процесс SayDent аварийно завершился. systemd перезапускает сайт.',
    'nginx': 'Nginx аварийно завершился. systemd перезапускает веб-сервер.',
    'health': 'Сайт не отвечает на локальную проверку. Запущено восстановление.',
    'tls': 'Сайт отвечает, но локальная проверка HTTPS не прошла. Проверьте TLS-сертификат.',
    'test': 'Тест мониторинга SayDent. Уведомления о сбоях подключены.',
}

if __name__ == '__main__':
    token = os.environ['MAX_BOT_TOKEN']
    chat_id = os.environ['MAX_CHAT_ID']
    if not token or not re.fullmatch(r'-?[1-9][0-9]*', chat_id):
        sys.exit('Invalid MAX alert configuration')

    context = ssl.create_default_context()
    context.load_verify_locations(str(Path(__file__).with_name('russian-trusted-root-ca.pem')))
    request = Request(
        'https://platform-api2.max.ru/messages?chat_id=' + chat_id,
        data=json.dumps({'text': 'saydentkzn.ru · ' + MESSAGES[sys.argv[1]]}, ensure_ascii=False).encode(),
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    request.add_unredirected_header('Authorization', token)
    try:
        with urlopen(request, context=context, timeout=12) as response:
            result = json.load(response)
        message_id = result['message']['body']['mid']
        if result.get('success') is False or not isinstance(message_id, str) or not message_id:
            raise ValueError('Message not confirmed')
    except Exception as error:
        sys.exit(f'MAX alert failed: {type(error).__name__}, HTTP {getattr(error, "code", None)}')
    print('MAX confirmed delivery', flush=True)
