import json
import os
import io
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload


class GoogleDriveDataManager:
    """
    Handles data operations with Google Drive, replacing local file operations.
    """

    def __init__(self):
        """Initialize Google Drive connection from credentials in environment variable."""
        # Get credentials from environment variable
        creds_json = os.environ.get('GOOGLE_DRIVE_CREDENTIALS')
        if not creds_json:
            raise ValueError("GOOGLE_DRIVE_CREDENTIALS environment variable not set")

        # Drive API scope
        scopes = ['https://www.googleapis.com/auth/drive']

        # Create credentials from JSON string
        try:
            service_account_info = json.loads(creds_json)
            self.credentials = service_account.Credentials.from_service_account_info(
                service_account_info, scopes=scopes)

            # Build the Drive service
            self.drive_service = build('drive', 'v3', credentials=self.credentials)

            # Get or create the data folder in Drive
            self.data_folder_id = self._get_or_create_data_folder()

        except Exception as e:
            raise Exception(f"Failed to initialize Google Drive connection: {str(e)}")

    def _get_or_create_data_folder(self):
        """Get or create a 'data' folder in Google Drive to store all files."""
        folder_name = 'bot-data'

        # Search for existing folder
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = self.drive_service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)'
        ).execute()

        items = results.get('files', [])

        if items:
            # Return existing folder ID
            return items[0]['id']
        else:
            # Create a new folder
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }

            folder = self.drive_service.files().create(
                body=folder_metadata,
                fields='id'
            ).execute()

            return folder.get('id')

    def _get_file_id(self, file_path):
        """Get the ID of a file in Google Drive based on its path."""
        # Extract just the filename from the path
        file_name = os.path.basename(file_path)

        # Search for the file in our data folder
        query = f"name='{file_name}' and '{self.data_folder_id}' in parents and trashed=false"
        results = self.drive_service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)'
        ).execute()

        items = results.get('files', [])

        if items:
            return items[0]['id']
        return None


def load_data(file_path, default=None):
    """
    Load data from a JSON file stored in Google Drive.

    Args:
        file_path (str): Path to the file (used as the filename in Drive)
        default (any, optional): Default value to return if file doesn't exist

    Returns:
        The loaded data, or the default value if the file doesn't exist
    """
    try:
        # Initialize Drive manager
        drive_manager = GoogleDriveDataManager()

        # Get the file ID
        file_id = drive_manager._get_file_id(file_path)

        if file_id:
            # Download file content
            request = drive_manager.drive_service.files().get_media(fileId=file_id)
            file_content = io.BytesIO()
            downloader = MediaIoBaseDownload(file_content, request)

            done = False
            while not done:
                _, done = downloader.next_chunk()

            # Reset file pointer to beginning and load JSON
            file_content.seek(0)
            return json.load(file_content)
        else:
            # File doesn't exist in Drive, return default
            return default if default is not None else {}

    except Exception as e:
        print(f"Error loading data from Google Drive: {str(e)}")
        return default if default is not None else {}


def save_data(data, file):
    """
    Save data to a JSON file in Google Drive.

    Args:
        data: The data to save
        file (str): Path to the file (used as the filename in Drive)
    """
    try:
        # Initialize Drive manager
        drive_manager = GoogleDriveDataManager()

        # Convert data to JSON and then to bytes
        json_data = json.dumps(data, indent=4, ensure_ascii=False)
        file_content = io.BytesIO(json_data.encode('utf-8'))

        # Get file name from path
        file_name = os.path.basename(file)

        # Check if file already exists
        file_id = drive_manager._get_file_id(file)

        # Prepare media upload
        media = MediaIoBaseUpload(
            file_content,
            mimetype='application/json',
            resumable=True
        )

        if file_id:
            # Update existing file
            drive_manager.drive_service.files().update(
                fileId=file_id,
                media_body=media
            ).execute()
        else:
            # Create new file
            file_metadata = {
                'name': file_name,
                'parents': [drive_manager.data_folder_id]
            }

            drive_manager.drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()

    except Exception as e:
        # Log error but don't crash the application
        print(f"Error saving data to Google Drive: {str(e)}")


# For backwards compatibility, provide direct access to functions
if __name__ == "__main__":
    # Test the module
    test_data = {"test": "data", "number": 123}
    save_data(test_data, "test_file.json")
    loaded_data = load_data("test_file.json")
    print(f"Loaded data: {loaded_data}")