import smtplib
from email.mime.text import MIMEText
import os

def send_fake_email():
    sender = "tesseracapital@gmail.com"
    password = "hlfy rctn bqep etnd"
    receiver = "mayank.hinduja27@gmail.com"
    
    subject = "Firefly Aerospace Research Request: Propulsion Systems"
    body = """Dear Shubhanker Kapoor,

I saw your work as Lead, Propulsion Systems at Impulse Space, and I was impressed by your expertise in the field. Given your background, I wanted to reach out regarding my research project focused on Firefly Aerospace, where you previously worked.

Our analysis has identified propulsion systems as a key catalyst for their growth, and I believe your insights would be invaluable in helping us better understand their technology and strategy.

Would you be available for a 10-15 minute call at your convenience?

Best regards,
Mayank Hinduja
NYU Stern"""

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = f"Mayank Hinduja <{sender}>"
    msg['To'] = receiver

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender, password)
            server.sendmail(sender, receiver, msg.as_string())
        print("✅ Fake Shubhanker email sent successfully!")
    except Exception as e:
        print(f"❌ Error sending email: {e}")

if __name__ == "__main__":
    send_fake_email()
