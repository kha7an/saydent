#!/bin/sh
set -eu

site_responds() {
    curl -fsS "$@" --noproxy '*' --resolve saydentkzn.ru:443:127.0.0.1 \
        --max-time 4 --output /dev/null https://saydentkzn.ru/
}

if site_responds; then exit 0; fi
sleep 3
if site_responds; then exit 0; fi

if site_responds --insecure; then
    systemctl --no-block start saydent-alert@tls.service
    exit 1
fi

systemctl --no-block start saydent-alert@health.service
if ! curl -fsS --noproxy '*' --max-time 4 --output /dev/null http://127.0.0.1:8765/; then
    systemctl restart saydent.service
    curl -fsS --noproxy '*' --retry 3 --retry-connrefused --retry-delay 1 \
        --retry-max-time 8 --max-time 4 --output /dev/null http://127.0.0.1:8765/
    if site_responds; then exit 0; fi
fi

nginx -t -q
systemctl restart nginx.service
site_responds
