import os.path
import glob
import base64
import datetime
import re
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import config
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# Permission to modify Gmail emails (necessary to mark them as read)
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

def get_gmail_service():
    """Shows the login screen the first time and returns the Gmail service."""
    import base64
    
    # In Docker/CI environments, we might have credentials in env vars as base64
    creds_env = {
        'credentials.json': os.getenv('GOOGLE_CREDENTIALS_BASE64'),
        'client_secret.json': os.getenv('GMAIL_CLIENT_SECRET_BASE64'),
        'token.json': os.getenv('GMAIL_TOKEN_BASE64')
    }
    
    for filename, b64_content in creds_env.items():
        if b64_content and not os.path.exists(filename):
            try:
                with open(filename, 'wb') as f:
                    f.write(base64.b64decode(b64_content))
                logger.info(f"Created {filename} from environment variable.")
            except Exception as e:
                logger.error(f"Error creating {filename} from env: {e}")

    creds = None
    # The file token.json is created automatically the first time you login, 
    # so you don't have to login every time you run the script.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        
    # If there are no valid credentials, ask to login
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Check if we are in a CI/Headless environment to avoid hanging
            if os.getenv('GITHUB_ACTIONS') == 'true' or os.getenv('CI') == 'true':
                logger.error("Authentication failed: No valid token found in CI environment and cannot open browser for manual login.")
                return None
            
            flow = InstalledAppFlow.from_client_secrets_file(
                'client_secret.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save credentials for next time
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    try:
        service = build('gmail', 'v1', credentials=creds)
        logger.info("Successfully authenticated to Gmail API.")
        return service
    except Exception as error:
        logger.error(f'An error occurred: {error}')
        return None

def download_attachments(service, output_dir='data', folder_name=None, target_date=None):
    """Searches for emails with attachments and downloads their .xls files for a specific date"""
    if target_date is None:
        target_date = datetime.datetime.now().strftime("%Y-%m-%d")
    
    logger.info(f"Target date for downloads: {target_date}")
    # You can change 'output_dir' if you want another folder
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Search for emails that have attachments
    query = "has:attachment"
    
    # If a folder (label) was specified, add it to the query
    if folder_name:
        query += f" label:\"{folder_name}\""
    
    try:
        # Search for emails with the query and that are "Unread" to not process them twice
        query += " is:unread"
        logger.info(f"Searching for emails with query: {query}")
        results = service.users().messages().list(userId='me', q=query).execute()
        messages = results.get('messages', [])

        if not messages:
            logger.info("No new emails found.")
            return

        logger.info(f"Found {len(messages)} emails. Analyzing attachments...")

        cleared_old_files = False

        for message in messages:
            msg = service.users().messages().get(userId='me', id=message['id']).execute()
            
            email_has_valid_attachment = False
            # Iterate over the email parts looking for documents
            if 'parts' in msg['payload']:
                for part in msg['payload']['parts']:
                    # Check if the part has a filename (i.e. it is an attachment)
                    if part.get('filename'):
                        filename = part['filename']
                        # Check if it has a date pattern and matches target_date
                        date_match = re.search(r'\d{4}-\d{2}-\d{2}', filename)
                        file_date = date_match.group(0) if date_match else None
                        
                        # Only download if it's an .xls or .xlsx file, starts with desired prefixes, AND matches target_date
                        valid_prefixes = tuple(config.FILE_PREFIXES)
                        if filename.startswith(valid_prefixes) and (filename.endswith('.xls') or filename.endswith('.xlsx')) and file_date == target_date:
                            
                            email_has_valid_attachment = True

                            # If it's the first valid file we find, we delete the previous ones
                            if not cleared_old_files:
                                existing_files = glob.glob(os.path.join(output_dir, '*CAN*.xls*'))
                                for f in existing_files:
                                    try:
                                        os.remove(f)
                                        logger.info(f"Deleted old file: {f}")
                                    except Exception as e:
                                        logger.error(f"Could not delete old file {f}: {e}")
                                cleared_old_files = True

                            attachment_id = part['body'].get('attachmentId')
                            
                            # Get the attachment using its ID
                            attachment = service.users().messages().attachments().get(
                                userId='me', messageId=message['id'], id=attachment_id).execute()
                            
                            file_data = base64.urlsafe_b64decode(attachment['data'].encode('UTF-8'))
                            
                            filepath = os.path.join(output_dir, filename)
                            
                            # Save the file in the 'data' folder
                            with open(filepath, 'wb') as f:
                                f.write(file_data)
                                
                            logger.info(f"Downloaded: {filepath}")
            
            # ONLY if finishing reviewing the email we found valid files for that day, mark it as read
            if email_has_valid_attachment:
                service.users().messages().modify(
                    userId='me', 
                    id=message['id'], 
                    body={'removeLabelIds': ['UNREAD']}
                ).execute()
                logger.info(f"Email marked as read.")
            else:
                logger.info(f"Email ID {message['id']} did not contain attachments for {target_date}. Keeping as UNREAD.")
                            
    except Exception as error:
        logger.error(f"An error occurred searching/downloading attachments: {error}")

def run_downloader(target_date=None):
    """Main function to run the downloader."""
    service = get_gmail_service()
    if service:
        # You can change 'INBOX' for the name of your custom folder/label
        # For example: folder_name='Work/Reports'
        download_attachments(service, output_dir=config.DATA_DIR, folder_name=config.GMAIL_LABEL, target_date=target_date)
        return True
    return False

if __name__ == '__main__':
    run_downloader()
