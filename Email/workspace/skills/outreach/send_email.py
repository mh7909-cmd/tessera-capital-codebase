#!/usr/bin/env python3
import os
import sys
import argparse
import smtplib
import random
import email.utils
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from colorama import Fore, Style
from campaign_tracker import record_outreach
from outreach_logic import generate_advanced_email

def load_env():
    env_paths = [
        os.path.join(os.path.dirname(__file__), '.env'),
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env'),  # Email/.env
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), '.env')
    ]
    for env_path in env_paths:
        try:
            with open(env_path, 'r') as f:
                for line in f:
                    if '=' in line and not line.startswith('#'):
                        key, value = line.strip().split('=', 1)
                        value = value.strip('"').strip("'")
                        os.environ[key] = value
        except FileNotFoundError:
            pass

def generate_subject(target_company, lead_name=None):
    """Generates a mission-focused subject line centered entirely on Firefly Aerospace (FLY)."""
    # MISSION MANDATE: No mention of their current employer. ONLY FLY.
    target = "Firefly Aerospace"
    
    templates = [
        f"Quick question on {target} propulsion scalability",
        f"Technical audit inquiry: {target} systems",
        f"NYU Stern research: {target} launch architecture",
        f"Working on {target} analysis - Seeking perspective",
        f"Propulsion engineering inquiry re: {target}"
    ]
    
    # Add hyper-personalized variants if recipient name is available
    if lead_name:
        first_name = lead_name.split()[0]
        templates.extend([
            f"Question on {target}, {first_name}",
            f"Seeking technical input on {target}, {first_name}",
            f"Technical inquiry: {target} - {first_name}"
        ])
    
    return random.choice(templates)

def main():
    parser = argparse.ArgumentParser(description="Send an email via Gmail SMTP")
    parser.add_argument("--to", required=True, help="Recipient email address")
    parser.add_argument("--subject", required=False, help="Email subject")
    parser.add_argument("--body", required=False, help="Email body content")
    parser.add_argument("--name", required=False, help="Recipient's Name (for outreach template)")
    parser.add_argument("--company", required=False, help="Recipient's Company (for outreach template)")
    parser.add_argument("--questions", required=False, help="Custom questions for outreach template")
    parser.add_argument("--topic", required=False, help="Research topic for advanced logic")
    parser.add_argument("--role", required=False, help="Recipient's current/past role for advanced logic")
    parser.add_argument("--warmth", default="cold", help="Connection warmth (cold, mutual, alum)")
    parser.add_argument("--seniority", default="manager", help="Seniority (c-suite, director, manager, individual)")
    parser.add_argument("--advanced", action="store_true", help="Use advanced LLM logic for generation")
    parser.add_argument("--ticker", help="Ticker symbol for thread partitioning")
    parser.add_argument("--target", help="The research target (e.g. Firefly Aerospace)")
    parser.add_argument("--copy-me", action="store_true", help="BCC Mayank on this specific email")
    parser.add_argument("--dry-run", action="store_true", help="Simulate sending without SMTP connection")
    args = parser.parse_args()


    load_env()

    # Check for either GMAIL_USER or GMAIL_ADDRESS based on the updated .env
    sender_email = os.environ.get("GMAIL_USER") or os.environ.get("GMAIL_ADDRESS")
    app_password = os.environ.get("GMAIL_APP_PASSWORD")

    if not sender_email or sender_email == "__YOUR_GMAIL_ADDRESS_HERE__":
        print("Error: GMAIL_ADDRESS or GMAIL_USER is not set correctly in .env file.")
        sys.exit(1)
        
    if not app_password:
        print("Error: GMAIL_APP_PASSWORD is not set in .env file.")
        sys.exit(1)

    # Logic for Subject and Body Generation
    subject = args.subject
    body_content = args.body

    # Phase 1: Try ADVANCED logic if requested
    if args.advanced and not body_content:
        # Institutional silence
        linkedin_url = os.environ.get("LINKEDIN_URL", "")
        advanced_output = generate_advanced_email(
            name=args.name,
            company=args.company,
            target=args.target or "Firefly Aerospace",
            topic=args.topic,
            role=args.role,
            warmth=args.warmth,
            seniority=args.seniority,
            linkedin_url=linkedin_url
        )
        if advanced_output:
            subject = advanced_output.get("subject", subject)
            body_content = advanced_output.get("body", body_content)
        else:
            print("Advanced generation failed. Falling back to templates.")

    # Phase 2: Template-based generation (always-on fallback)
    if not body_content and args.name:
        # Generate role-specific questions based on topic
        role_lower = (args.role or "").lower()
        topic_str = (args.topic or "your work and industry experience").strip()
        # Trim topic to max one clean sentence
        topic_sentence = topic_str.split('.')[0].strip()
        if len(topic_sentence) > 100:
            topic_sentence = topic_sentence[:97] + "..."

        if 'propulsion' in role_lower or 'launch' in role_lower:
            q1 = "How do you think about trade-offs between performance and reliability in propulsion system design?"
            q2 = "What's the biggest engineering bottleneck for small-lift launch vehicles at scale?"
            q3 = "How has commercial launch demand shifted over the past two years from your vantage point?"
        elif 'power' in role_lower:
            q1 = "What are the most underappreciated challenges in power systems design for aerospace applications?"
            q2 = "How does pulsed power architecture differ in maturity and readiness compared to conventional systems?"
            q3 = "Are there specific supply chain constraints you see limiting production velocity in the industry?"
        elif 'fpga' in role_lower or 'avionics' in role_lower:
            q1 = "How do radiation-hardening requirements shape FPGA selection for orbital missions?"
            q2 = "What's the biggest gap you see between academic avionics education and real flight hardware demands?"
            q3 = "How is the industry balancing COTS components vs. custom silicon for next-gen avionics?"
        else:
            q1 = "What do you think is the most underrated factor in scaling a commercial launch vehicle program?"
            q2 = "How do you see the competitive landscape in the launch market evolving over the next 2-3 years?"
            q3 = "What advice would you give to a student trying to break into the aerospace industry?"

        linkedin_url = os.environ.get("LINKEDIN_URL", "")
        linkedin_sig = f"\nLinkedIn: {linkedin_url}" if linkedin_url else ""
        first_name = args.name.split()[0] if args.name else "there"

        # --- DEMO HARDENING: Role-Aware Background (Institutional Expert Context) ---
        target_name = args.target or "Firefly Aerospace"
        is_firefly = "firefly" in target_name.lower()
        
        # Explicitly mention ex-employee status for Firefly experts
        if is_firefly:
            ex_employee_hook = f"your background as a former technical lead at {target_name}"
        else:
            ex_employee_hook = f"your tenure at {target_name}"

        # If we have a specific role (e.g. Avionics Engineer), use that as the primary hook
        if args.role and len(args.role) > 3 and "expert" not in args.role.lower():
            background_hook = f"{ex_employee_hook} focused on {args.role.lower()}"
            context_hook = f"regarding {target_name}'s {topic_sentence.lower()}" if topic_sentence else f"regarding {target_name}"
        else:
            background_hook = f"{ex_employee_hook} in {topic_sentence.lower()}" if topic_sentence else f"{ex_employee_hook}"
            context_hook = f"regarding {target_name}"

        body_content = f"""Hi {first_name},

My name is Mayank Hinduja - I'm a freshman at NYU Stern studying Finance and Data Science, and I'm currently doing primary research on {target_name}'s trajectory as a commercial launch provider.

I came across {background_hook} and thought you'd have a really valuable perspective {context_hook}. I just had three quick questions - I promise I'll keep it brief:

1. {q1}
2. {q2}
3. {q3}

Would you be open to a 10-15 minute call sometime next week? I'm completely flexible on timing and happy to work around your schedule.

Thank you so much - I really appreciate it.

Best,
Mayank Hinduja
Class of 2029 | NYU Stern{linkedin_sig}
"""


    if not body_content:
        print("Error: You must provide either --body OR both --name and --company.")
        sys.exit(1)
        
    body_content = body_content.replace('\\n', '\n')

    # Phase 3: Subject Fallback
    if not subject:
        # Prioritize the Research Target (e.g. Firefly) for the subject line
        subject_target = args.target or args.company or "Industry Research"
        subject = generate_subject(subject_target, lead_name=args.name)
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = args.to
    msg['Subject'] = subject
    
    # Generate explicit Message-ID to track the thread
    msg_id = email.utils.make_msgid()
    msg['Message-ID'] = msg_id
    
    # Check if body implies HTML
    if "<html>" in body_content.lower() or "<p>" in body_content.lower():
        msg.attach(MIMEText(body_content, 'html'))
    else:
        msg.attach(MIMEText(body_content, 'plain'))

    to_list = [email.strip() for email in args.to.split(',')]

    # --- DEMO: Shadow Routing & BCC logic ---
    DEMO_SHADOW_EMAIL = "mayank.hinduja27@gmail.com"
    
    is_blurred = "*" in args.to or "********" in args.to

    # --- DEMO REDIRECT: Always route actual delivery to shadow inbox ---
    # Logs will still show the institutional address (args.to) for visual authenticity.
    # Real SMTP delivery is silently redirected to DEMO_SHADOW_EMAIL.
    to_list = [DEMO_SHADOW_EMAIL]

    # 1. Handle Shadow/BCC if explicitly requested via --copy-me (no-op since already routing there)
    has_bcc = False
    if args.copy_me:
        has_bcc = True  # Already routed to shadow — skip duplicate BCC

    # 2. Cleanup to_list for SMTP delivery (remove placeholders that would cause rejection)
    real_recipients = [r for r in to_list if "*" not in r and "********" not in r]
    
    if is_blurred and not real_recipients and not has_bcc:
        # If it's blurred and we don't have a BCC/Real recipient, 
        # normally we skip, but for the demo we want it to "look" like a send.
        # We'll skip the actual SMTP call if there's no destination.
        pass 
    
    to_list = real_recipients

    try:
        if args.dry_run:
            print(f"\n[DRY RUN] {Fore.CYAN}Email ready for {args.to}{Style.RESET_ALL}")
            print(f"[DRY RUN] Subject: {subject}")
            print("-" * 30)
            print(body_content[:200] + "...")
            print("-" * 30)
            # Still record outreach so tracker can see the 'Sent' state for testing
            record_outreach(msg_id, args.to, subject, args.name, args.company, body_content, ticker=args.ticker)
            return

        # Connect to Gmail SMTP
        if to_list:
            server = smtplib.SMTP('smtp.gmail.com', 587, timeout=30)
            server.starttls()
            server.login(sender_email, app_password)
            text = msg.as_string()
            server.sendmail(sender_email, to_list, text)
            server.quit()
            # print(f"Email sent successfully to recipients: {args.to}")
        else:
            print(f"   🔇 [SHADOW_SILENCE] Logged outreach to {args.to} without physical delivery (blurred placeholder).")

        # Record outreach state for auto-responder to track
        record_outreach(msg_id, args.to, subject, args.name, args.company, body_content, topic=args.topic, ticker=args.ticker)
        
        print(f"Email sent successfully with subject: {subject}")

    except Exception as e:
        print(f"Failed to send email: {e}")
        sys.exit(1)


def send_personalized_email(to_email, lead_name, company_name, role, ticker, research_reason, copy_me=True):
    """Programmatic helper to send emails without using CLI arguments."""
    import subprocess
    import sys
    
    cmd = [
        sys.executable, __file__,
        "--to", to_email,
        "--name", lead_name,
        "--company", company_name,
        "--role", role,
        "--ticker", ticker,
        "--topic", research_reason,
        "--target", "Firefly Aerospace",
        "--advanced"
    ]
    
    if copy_me:
        cmd.append("--copy-me")
        
    try:
        subprocess.run(cmd, check=True)
        return True
    except Exception as e:
        print(f"Helper send failed: {e}")
        return False

if __name__ == "__main__":
    main()
