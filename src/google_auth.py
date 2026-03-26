import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# The God-Mode Scopes
SCOPES =[
    'https://www.googleapis.com/auth/drive', 
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/cloud-platform' # Covers Vertex AND AI Studio
]

def get_google_credentials() -> Credentials:
    creds = None
    token_path = 'B:/MACCREv2/token.json'
    creds_path = 'B:/MACCREv2/credentials.json'

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("[Auth Engine] Refreshing expired master token...")
            creds.refresh(Request())
        else:
            print("[Auth Engine] No token found. Initiating secure OAuth flow...")
            if not os.path.exists(creds_path):
                raise FileNotFoundError(f"CRITICAL: {creds_path} is missing. Halting.")
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
            print("[Auth Engine] Master Token secured.")
            
    return creds