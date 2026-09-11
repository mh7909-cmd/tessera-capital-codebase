import os
import gspread
from pathlib import Path

def debug_gspread_auth_depth():
    creds_path = "client_secret.json"
    auth_user_path = "authorized_user.json"
    
    if not (Path(creds_path).exists() and Path(auth_user_path).exists()):
        print(f"Missing creds or auth user at {os.getcwd()}")
        return

    try:
        gc = gspread.oauth(
            credentials_filename=creds_path,
            authorized_user_filename=auth_user_path
        )
        
        auth_obj = gc.http_client.auth
        print(f"Auth Object type: {type(auth_obj)}")
        print(f"Auth Object attributes: {[attr for attr in dir(auth_obj) if not attr.startswith('_')]}")
        
        # Check credentials in auth_obj
        if hasattr(auth_obj, 'credentials'):
            creds = auth_obj.credentials
            print(f"Credentials type: {type(creds)}")
            if hasattr(creds, 'token'):
                print(f"Token value type: {type(creds.token)}")
                print("SUCCESS: Token found in gc.http_client.auth.credentials.token")
            else:
                print("No token in credentials.")
        
    except Exception as e:
        print(f"Error during debug: {e}")

if __name__ == "__main__":
    debug_gspread_auth_depth()
