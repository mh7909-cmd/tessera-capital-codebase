import smtplib
from email.mime.text import MIMEText
import os
from dotenv import load_dotenv

def main():
    load_dotenv()
    user = os.environ.get("GMAIL_USER")
    password = os.environ.get("GMAIL_APP_PASSWORD")
    
    print(f"Testing with account: {user}")
    
    recipient = "mayank.hinduja27@gmail.com"
    msg = MIMEText("This is a direct SMTP test to verify connectivity.")
    msg['Subject'] = "SMTP Verification Test"
    msg['From'] = user
    msg['To'] = recipient
    
    try:
        print("1. Connecting to smtp.gmail.com:587...")
        server = smtplib.SMTP('smtp.gmail.com', 587, timeout=15)
        
        print("2. Sending EHLO...")
        server.ehlo()
        
        print("3. Starting TLS...")
        server.starttls()
        
        print("4. Sending EHLO again...")
        server.ehlo()
        
        print(f"5. Logging in as {user}...")
        server.login(user, password)
        
        print(f"6. Sending mail to {recipient}...")
        results = server.sendmail(user, [recipient], msg.as_string())
        
        server.quit()
        print("7. Success! SMTP session closed.")
        print(f"Sendmail results: {results}")
        
    except Exception as e:
        print(f"FAILED at some point: {e}")

if __name__ == "__main__":
    main()
