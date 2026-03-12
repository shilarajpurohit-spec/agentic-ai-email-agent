import ollama
import re
import pandas as pd
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
import sys

# TOOLS

def read_excel(filepath):
    """Read contacts from Excel file"""
    try:
        if not Path(filepath).exists():
            return {"error": f"File '{filepath}' not found"}
        
        df = pd.read_excel(filepath)
        
        # Validate columns
        required = ['name', 'email']
        missing = [col for col in required if col not in df.columns]
        if missing:
            return {"error": f"Missing columns: {missing}. Required: name, email"}
        
        contacts = df.to_dict('records')
        return {"success": True, "contacts": contacts, "count": len(contacts)}
    
    except Exception as e:
        return {"error": str(e)}

def generate_email(contact_name, contact_email, contact_company, email_context):
    """Generate personalized email using AI"""
    try:
        company_info = f" at {contact_company}" if contact_company else ""

        prompt = f"""
You are an expert email copywriter.

Write a professional personalized email.

Recipient: {contact_name}{company_info}
Email: {contact_email}

Campaign Context:
{email_context}

Requirements:
- Address them by name
- Mention their company if provided
- Include a clear call-to-action
- Keep under 200 words

Return EXACTLY in this format:

SUBJECT: subject line here
BODY:
email body text here
"""

        response = ollama.chat(
            model='llama3.1:8b',
            messages=[{'role': 'user', 'content': prompt}]
        )

        content = response['message']['content']

        # Split subject and body
        lines = content.splitlines()

        subject = ""
        body_lines = []

        for line in lines:
            if line.startswith("SUBJECT:"):
                subject = line.replace("SUBJECT:", "").strip()
            elif line.startswith("BODY:"):
                continue
            else:
                body_lines.append(line)

        body = "\n".join(body_lines).strip()

        return {"success": True, "subject": subject, "body": body}

    except Exception as e:
        return {"error": f"Failed to generate email: {str(e)}"}


def send_email_smtp(to_email, subject, body, smtp_config=None):
    """Send email via SMTP"""
    if not smtp_config:
        return {"error": "SMTP not configured. Run in preview mode."}
    
    try:
        msg = MIMEMultipart()
        msg['From'] = smtp_config['sender_email']
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(smtp_config['server'], smtp_config['port'])
        server.starttls()
        server.login(smtp_config['sender_email'], smtp_config['password'])
        server.send_message(msg)
        server.quit()
        
        return {"success": True, "message": f"Sent to {to_email}"}
    
    except Exception as e:
        return {"error": f"Failed to send: {str(e)}"}

# INTERACTIVE INTERFACE

class InteractiveEmailAgent:
    def __init__(self):
        self.contacts = []
        self.email_context = ""
        self.smtp_config = None
        self.generated_emails = []
    
    def print_header(self, text):
        """Print a nice header"""
        print(f"\n{'='*70}")
        print(f"  {text}")
        print(f"{'='*70}\n")
    
    def print_box(self, title, content):
        """Print content in a box"""
        print(f"\n┌{'─'*68}┐")
        print(f"│ {title:<66} │")
        print(f"├{'─'*68}┤")
        for line in content.split('\n'):
            print(f"│ {line:<66} │")
        print(f"└{'─'*68}┘\n")
    
    def step_load_contacts(self):
        """Step 1: Load contacts from Excel"""
        self.print_header("STEP 1: Load Contacts")
        
        print("Enter the path to your Excel file with contacts.")
        print("Required columns: 'name', 'email' (optional: 'company')")
        print("Example: contacts.xlsx\n")
        
        filepath = input(" Excel file path: ").strip()
        
        if not filepath:
            print("No file specified. Exiting.")
            sys.exit(1)
        
        print(f"\n Reading {filepath}...")
        result = read_excel(filepath)
        
        if "error" in result:
            print(f" {result['error']}")
            sys.exit(1)
        
        self.contacts = result['contacts']
        print(f" Loaded {result['count']} contacts")
        
        # Preview contacts
        print("\n Contacts Preview:")
        for i, contact in enumerate(self.contacts[:3], 1):
            company = f" ({contact.get('company', 'N/A')})" if contact.get('company') else ""
            print(f"  {i}. {contact['name']} - {contact['email']}{company}")
        
        if len(self.contacts) > 3:
            print(f"  ... and {len(self.contacts) - 3} more")
        
        input("\n✓ Press Enter to continue...")
    
    def step_define_context(self):
        """Step 2: Define email context"""
        self.print_header("STEP 2: Define Email Campaign")
        
        print("Describe what this email campaign is about.")
        print("The AI will use this to personalize each email.\n")
        print("Examples:")
        print("  - 'Invite to our product launch webinar on March 15th'")
        print("  - 'Offer 30% discount on annual SaaS plans, expires end of month'")
        print("  - 'Follow up after conference, mention we met at booth #42'\n")
        
        print(" Enter your email context (press Enter twice when done):")
        print("-" * 70)
        
        lines = []
        while True:
            line = input()
            if line == "" and lines and lines[-1] == "":
                break
            lines.append(line)
        
        self.email_context = '\n'.join(lines).strip()
        
        if not self.email_context:
            print(" No context provided. Exiting.")
            sys.exit(1)
        
        print("\n Email context saved")
        self.print_box("Your Campaign Context", self.email_context)
        
        input("✓ Press Enter to continue...")
    
    def step_generate_emails(self):
        """Step 3: Generate emails for each contact"""
        self.print_header("STEP 3: Generate Personalized Emails")
        
        print(f" AI is generating {len(self.contacts)} personalized emails...")
        print("This may take a moment...\n")
        
        self.generated_emails = []
        
        for i, contact in enumerate(self.contacts, 1):
            print(f"[{i}/{len(self.contacts)}] Generating for {contact['name']}...", end=" ")
            
            result = generate_email(
                contact_name=contact['name'],
                contact_email=contact['email'],
                contact_company=contact.get('company', ''),
                email_context=self.email_context
            )
            
            if "error" in result:
                print(f" {result['error']}")
                self.generated_emails.append({
                    "contact": contact,
                    "error": result['error']
                })
            else:
                print("✓")
                self.generated_emails.append({
                    "contact": contact,
                    "subject": result['subject'],
                    "body": result['body']
                })
        
        successful = len([e for e in self.generated_emails if "error" not in e])
        print(f"\n Generated {successful}/{len(self.contacts)} emails successfully")
        
        input("\n Press Enter to review emails...")
    
    def step_review_emails(self):
        """Step 4: Review and approve emails"""
        self.print_header("STEP 4: Review Emails")
        
        approved_emails = []
        
        for i, email_data in enumerate(self.generated_emails, 1):
            if "error" in email_data:
                continue
            
            contact = email_data['contact']
            
            # Show email preview
            print(f"\n{'─'*70}")
            print(f"Email {i}/{len(self.generated_emails)}")
            print(f"{'─'*70}")
            print(f" To: {contact['name']} <{contact['email']}>")
            if contact.get('company'):
                print(f"Company: {contact['company']}")
            print(f"\n Subject: {email_data['subject']}")
            print(f"\n{email_data['body']}")
            print(f"{'─'*70}\n")
            
            # Ask for approval
            while True:
                choice = input("Choose: [A]pprove, [S]kip, [E]dit subject, [Q]uit: ").strip().upper()
                
                if choice == 'A':
                    approved_emails.append(email_data)
                    print(" Approved\n")
                    break
                elif choice == 'S':
                    print(" Skipped\n")
                    break
                elif choice == 'E':
                    new_subject = input("New subject: ").strip()
                    if new_subject:
                        email_data['subject'] = new_subject
                        print(" Subject updated")
                elif choice == 'Q':
                    print("\n Exiting review process...")
                    return approved_emails
                else:
                    print("Invalid choice. Try again.")
        
        print(f"\n Approved {len(approved_emails)} emails for sending")
        return approved_emails
    
    def step_send_emails(self, approved_emails):
        """Step 5: Send approved emails"""
        if not approved_emails:
            print("\n  No emails to send.")
            return
        
        self.print_header("STEP 5: Send Emails")
        
        print(f"You have {len(approved_emails)} approved emails.\n")
        print("Options:")
        print("  1. Preview only (dry run)")
        print("  2. Send via SMTP (requires configuration)")
        print("  3. Export to file")
        
        choice = input("\nChoose (1/2/3): ").strip()
        
        if choice == '1':
            # Preview mode
            print("\n PREVIEW MODE\n")
            for email_data in approved_emails:
                contact = email_data['contact']
                print(f"{'='*70}")
                print(f"To: {contact['email']}")
                print(f"Subject: {email_data['subject']}")
                print(f"\n{email_data['body']}")
                print(f"{'='*70}\n")
            print("✓ All emails previewed (not sent)")
        
        elif choice == '2':
            # SMTP sending
            print("\n  SMTP Configuration Required")
            print("\nEnter your SMTP details:")
            
            smtp_config = {
                'server': input("SMTP Server (e.g., smtp.gmail.com): ").strip(),
                'port': int(input("Port (usually 587): ").strip() or "587"),
                'sender_email': input("Your email: ").strip(),
                'password': input("App password: ").strip()
            }
            
            confirm = input(f"\n  Send {len(approved_emails)} emails? (yes/no): ").strip().lower()
            
            if confirm == 'yes':
                print("\n Sending emails...\n")
                sent_count = 0
                
                for email_data in approved_emails:
                    contact = email_data['contact']
                    print(f"Sending to {contact['email']}...", end=" ")
                    
                    result = send_email_smtp(
                        to_email=contact['email'],
                        subject=email_data['subject'],
                        body=email_data['body'],
                        smtp_config=smtp_config
                    )
                    
                    if "error" in result:
                        print(f" {result['error']}")
                    else:
                        print("✓")
                        sent_count += 1
                
                print(f"\n Successfully sent {sent_count}/{len(approved_emails)} emails")
            else:
                print("Cancelled.")
        
        elif choice == '3':
            # Export to file
            filename = input("Filename (e.g., emails.txt): ").strip() or "emails.txt"
            
            with open(filename, 'w') as f:
                for email_data in approved_emails:
                    contact = email_data['contact']
                    f.write(f"{'='*70}\n")
                    f.write(f"To: {contact['name']} <{contact['email']}>\n")
                    f.write(f"Subject: {email_data['subject']}\n\n")
                    f.write(f"{email_data['body']}\n")
                    f.write(f"{'='*70}\n\n")
            
            print(f" Exported to {filename}")
    
    def run(self):
        """Main flow"""
        print("\n")
        print("╔═══════════════════════════════════════════════════════════════════╗")
        print("║                                                                   ║")
        print("║              🤖 INTERACTIVE EMAIL AGENT                           ║")
        print("║              Personalized Email Campaigns with AI                 ║")
        print("║                                                                   ║")
        print("╚═══════════════════════════════════════════════════════════════════╝")
        
        try:
            # Step 1: Load contacts
            self.step_load_contacts()
            
            # Step 2: Define email context
            self.step_define_context()
            
            # Step 3: Generate emails
            self.step_generate_emails()
            
            # Step 4: Review emails
            approved_emails = self.step_review_emails()
            
            # Step 5: Send emails
            self.step_send_emails(approved_emails)
            
            self.print_header("All Done!")
            print("Your email campaign is complete.\n")
        
        except KeyboardInterrupt:
            print("\n\n  Interrupted by user. Exiting...")
            sys.exit(0)
        except Exception as e:
            print(f"\n Unexpected error: {str(e)}")
            sys.exit(1)

# RUN
if __name__ == "__main__":
    agent = InteractiveEmailAgent()
    agent.run()