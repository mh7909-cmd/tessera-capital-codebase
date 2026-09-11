---
description: Automated Email Outreach Campaign Skill
---

# Outreach Skill

## Capability Pattern
The user will occasionally request you to do "outreach" or "send an email". When they do, follow these rules:

1. **Information Gathering**: If the user tells you to email someone but doesn't provide the contents or the email address, ask them for the missing information.
2. **Drafting Guidelines**: Always draft the email *first* and present it to the user. Ensure the tone matches what the user requests (e.g., professional, casual, sales-oriented).
3. **Execution Tool**: Only after the user approves the draft, use your `exec` tool to run the Python script located at `workspace/skills/outreach/send_email.py`.

## Automated Pipeline Outreach
You can now pull leads directly from the Research Pipeline Spreadsheet.

1. **Check Pipeline**: Use `python3 workspace/skills/outreach/lead_processor.py --list` to see all current "pending" research leads and their associated company tabs.
2. **Drafting**: For each lead found, generate a personalized draft using the "Reason" from the pipeline.
3. **Approval**: Present each draft to the user.
4. **Sending & Closing**: Once a draft is approved and sent, the script can mark the lead as "Done" in the pipeline.

## Tool Usage
To send the email, use the Python script in this directory. 

Command format:
```bash
python3 workspace/skills/outreach/send_email.py --to="<recipient_email>" --subject="<subject_line>" --body="<email_body>"
```

*Note: Use double quotes to wrap the arguments to ensure spaces inside the subject or body are handled correctly by the shell. Avoid single quotes as they may conflict with text syntax.*

## Error Handling
- If the script returns an error stating that `GMAIL_ADDRESS` is not set, prompt the user to manually edit the `.env` file in `workspace/skills/outreach/.env` and add their Gmail address.
- If a ticker tab is missing, notify the user that the lead discovery process for that company may still be running.
