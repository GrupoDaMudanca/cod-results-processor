import requests

url = "http://192.168.0.12:8082/message/sendText/cod-results-processor"
headers = {"apikey": "54AD174D6129-47F7-93CA-5954A3B6999B"}
number = "120363427460649133@g.us"
msg_id = "AC5DBCDC8F7EAAA2B22B94355764772D"

payloads = [
    {
        "name": "Payload 1 (Root quoted)",
        "json": {
            "number": number,
            "text": "Teste Payload 1 (Root quoted)",
            "quoted": {"key": {"id": msg_id}}
        }
    },
    {
        "name": "Payload 2 (Root quoted with remoteJid)",
        "json": {
            "number": number,
            "text": "Teste Payload 2 (Root quoted with remoteJid)",
            "quoted": {"key": {"id": msg_id, "remoteJid": number}}
        }
    },
    {
        "name": "Payload 3 (options.quoted.key)",
        "json": {
            "number": number,
            "text": "Teste Payload 3 (options.quoted.key)",
            "options": {"quoted": {"key": {"id": msg_id, "remoteJid": number}}}
        }
    },
    {
        "name": "Payload 4 (options.quoted string)",
        "json": {
            "number": number,
            "text": "Teste Payload 4 (options.quoted string)",
            "options": {"quoted": msg_id}
        }
    },
    {
        "name": "Payload 5 (Root quoted messageId)",
        "json": {
            "number": number,
            "text": "Teste Payload 5 (Root quoted messageId)",
            "quoted": {"messageId": msg_id}
        }
    }
]

for p in payloads:
    try:
        r = requests.post(url, json=p["json"], headers=headers)
        print(f"{p['name']}: {r.status_code} {r.text}")
    except Exception as e:
        print(f"{p['name']}: ERROR {e}")
