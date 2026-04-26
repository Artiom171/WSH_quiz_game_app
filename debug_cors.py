import http.client
import json

for method in ['OPTIONS', 'POST']:
    try:
        conn = http.client.HTTPConnection('192.168.1.18', 8000, timeout=5)
        headers = {
            'Origin': 'http://localhost:8000',
            'Access-Control-Request-Method': 'POST',
            'Access-Control-Request-Headers': 'content-type',
            'Content-Type': 'application/json'
        }
        body = json.dumps({'name': 'test'}) if method == 'POST' else None
        conn.request(method, '/session', body=body, headers=headers)
        res = conn.getresponse()
        print('===', method, res.status, res.reason)
        print(dict(res.getheaders()))
        print(res.read().decode('utf-8', errors='replace'))
        conn.close()
    except Exception as exc:
        print(method, 'ERROR', exc)
