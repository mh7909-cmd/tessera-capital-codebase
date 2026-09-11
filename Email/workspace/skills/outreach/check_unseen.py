import email, imaplib, os
from auto_responder import load_env
from campaign_tracker import load_state

load_env()
user = os.environ.get("GMAIL_USER") or os.environ.get("GMAIL_ADDRESS")
pwd = os.environ.get("GMAIL_APP_PASSWORD")

mail = imaplib.IMAP4_SSL("imap.gmail.com")
mail.login(user, pwd)
mail.select("inbox")

status, messages = mail.search(None, '(UNSEEN)')
unseen_ids = messages[0].split()
print("Unseen messages found:", len(unseen_ids))

state = load_state()

for num in unseen_ids:
    status, data = mail.fetch(num, "(RFC822)")
    msg = email.message_from_bytes(data[0][1])
    in_reply_to = msg.get('In-Reply-To')
    msg_id = msg.get('Message-ID')
    subject = msg.get('Subject')
    sender = msg.get('From')
    print(f"Msg {num} - Subject: {subject} - From: {sender}")
    print(f"Msg {num} Message-ID: {msg_id}")
    print(f"Msg {num} In-Reply-To: {in_reply_to}")
    
    if in_reply_to:
        clean_in_reply_to = in_reply_to.strip("<>")
        print(f"Is {clean_in_reply_to} in tracked threads? {clean_in_reply_to in state['threads']}")
    else:
        print("No in_reply_to")
    print("---")
