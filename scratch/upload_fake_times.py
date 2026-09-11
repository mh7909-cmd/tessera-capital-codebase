import os
import pickle
import json
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
from dotenv import load_dotenv

# Load .env for REPORT_FOLDER_ID
load_dotenv()

# Configuration
REPORT_FOLDER_ID = os.getenv("REPORT_FOLDER_ID", "1kE4OmpQOGTheULpGOY2ZD4YE62hVH6jj")
TOKEN_PICKLE = "MiroFish/backend/token.pickle"
SCOPES = ['https://www.googleapis.com/auth/drive.file']

# Files to upload
FILES_TO_UPLOAD = [
    {
        "local_path": "MiroFish/backend/uploads/reports/rpt_a2f0de30a916/MiroFish_FIREFLY AEROSPACE_TECHNICAL_AUDIT_2026-05-03_15-57.docx",
        "drive_name": "MiroFish_FIREFLY_AEROSPACE_TECHNICAL_AUDIT.docx",
        "fake_time": "2026-05-04T16:02:00-04:00"
    }
]

def main():
    if not os.path.exists(TOKEN_PICKLE):
        print(f"Error: {TOKEN_PICKLE} not found.")
        return

    # Auth via token.pickle
    with open(TOKEN_PICKLE, 'rb') as token:
        creds = pickle.load(token)
    
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_PICKLE, 'wb') as token:
            pickle.dump(creds, token)

    drive_service = build('drive', 'v3', credentials=creds)

    for item in FILES_TO_UPLOAD:
        if not os.path.exists(item["local_path"]):
            print(f"Error: Local file {item['local_path']} not found.")
            continue

        print(f"Uploading {item['drive_name']} with fake time {item['fake_time']}...")
        
        file_metadata = {
            'name': item["drive_name"],
            'parents': [REPORT_FOLDER_ID],
            'createdTime': item["fake_time"],
            'modifiedTime': item["fake_time"]
        }
        
        media = MediaFileUpload(
            item["local_path"], 
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            resumable=True
        )
        
        try:
            # Create file with metadata
            file = drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink, createdTime, modifiedTime'
            ).execute()
            
            print(f"✅ Success: {item['drive_name']}")
            print(f"   ID: {file.get('id')}")
            print(f"   Link: {file.get('webViewLink')}")
            
        except Exception as e:
            print(f"❌ Failed to upload {item['drive_name']}: {e}")

if __name__ == "__main__":
    main()
