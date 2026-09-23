from dotenv import load_dotenv
load_dotenv('.env.development')

import os
import requests
from config import EVOLUTION_GET_CHAT_ENDPOINT, EVOLUTION_API_KEY, WHATSAPP_CHAT_ID

def check_admins():
    print(f"Endpoint: {EVOLUTION_GET_CHAT_ENDPOINT}")
    url = f"{EVOLUTION_GET_CHAT_ENDPOINT}?groupJid={WHATSAPP_CHAT_ID}"
    headers = {"apikey": EVOLUTION_API_KEY}
    
    try:
        response = requests.get(url, headers=headers)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"Error text: {response.text}")
            return
            
        chat_data = response.json()
        
        if isinstance(chat_data, list) and len(chat_data) > 0:
            chat_data = chat_data[0]
            
        participants = chat_data.get('participants', [])
        print(f"Number of participants: {len(participants)}")
        
        admins = []
        for p in participants:
            admin_status = p.get('admin')
            if admin_status in ('admin', 'superadmin'):
                admin_id = p.get('id')
                if admin_id:
                    admins.append(admin_id)
                    
        print(f"Admins: {admins}")
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == '__main__':
    check_admins()
