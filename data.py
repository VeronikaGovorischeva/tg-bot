import json
import os
import io
import time
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload


class GoogleDriveDataManager:
    """
    Handles data operations with Google Drive, replacing local file operations.
    Optimized with caching for authentication and file IDs.
    """

    # Class-level variables for caching
    _instance = None
    _drive_service = None
    _file_id_cache = {}  # Maps filenames to file IDs
    _data_folder_id = None
    _last_cache_refresh = 0
    _cache_ttl = 3600  # Cache TTL in seconds (1 hour)

    def __new__(cls):
        """Singleton pattern to ensure only one instance is created."""
        if cls._instance is None:
            cls._instance = super(GoogleDriveDataManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize Google Drive connection from credentials in environment variable."""
        # Skip initialization if already done
        if GoogleDriveDataManager._drive_service is not None:
            return

        # Get credentials from environment variable
        try:
            creds_json = os.environ.get('GOOGLE_DRIVE_CREDENTIALS')
            if not creds_json:
                raise ValueError("GOOGLE_DRIVE_CREDENTIALS environment variable not set")

            # Drive API scope
            scopes = ['https://www.googleapis.com/auth/drive']

            # Create credentials from JSON string
            service_account_info = json.loads(creds_json)
            credentials = service_account.Credentials.from_service_account_info(
                service_account_info, scopes=scopes)

            # Build the Drive service
            GoogleDriveDataManager._drive_service = build('drive', 'v3', credentials=credentials)

            # Get or create the data folder in Drive
            self._ensure_data_folder()

        except Exception as e:
            raise Exception(f"Failed to initialize Google Drive connection: {str(e)}")

    def _ensure_data_folder(self):
        """Get or create a 'data' folder in Google Drive to store all files."""
        if GoogleDriveDataManager._data_folder_id is not None:
            return GoogleDriveDataManager._data_folder_id

        folder_name = 'bot-data'

        # Search for existing folder
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = GoogleDriveDataManager._drive_service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)'
        ).execute()

        items = results.get('files', [])

        if items:
            # Return existing folder ID
            GoogleDriveDataManager._data_folder_id = items[0]['id']
        else:
            # Create a new folder
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }

            folder = GoogleDriveDataManager._drive_service.files().create(
                body=folder_metadata,
                fields='id'
            ).execute()

            GoogleDriveDataManager._data_folder_id = folder.get('id')

        return GoogleDriveDataManager._data_folder_id

    def refresh_file_id_cache(self, force=False):
        """
        Refresh the file ID cache if it's expired or forced.

        Args:
            force (bool): Force refresh even if cache is not expired
        """
        current_time = time.time()

        # Check if cache needs refreshing
        if not force and current_time - GoogleDriveDataManager._last_cache_refresh < GoogleDriveDataManager._cache_ttl:
            return

        # Refresh the cache
        try:
            # Get all files in the data folder
            query = f"'{GoogleDriveDataManager._data_folder_id}' in parents and trashed=false"
            results = GoogleDriveDataManager._drive_service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)'
            ).execute()

            # Clear existing cache
            GoogleDriveDataManager._file_id_cache = {}

            # Update cache with fresh data
            for file in results.get('files', []):
                GoogleDriveDataManager._file_id_cache[file['name']] = file['id']

            # Update last refresh timestamp
            GoogleDriveDataManager._last_cache_refresh = current_time

        except Exception as e:
            print(f"Error refreshing file ID cache: {str(e)}")

    def get_file_id(self, file_name):
        """
        Get the ID of a file in Google Drive based on its name.
        Uses cache if available, otherwise performs a lookup.

        Args:
            file_name (str): Name of the file

        Returns:
            str: File ID or None if not found
        """
        # Extract just the filename from the path if it contains slashes
        file_name = os.path.basename(file_name)

        # Check if the file ID is in the cache
        if file_name in GoogleDriveDataManager._file_id_cache:
            return GoogleDriveDataManager._file_id_cache[file_name]

        # If not in cache, refresh the cache (if needed) and check again
        self.refresh_file_id_cache()
        if file_name in GoogleDriveDataManager._file_id_cache:
            return GoogleDriveDataManager._file_id_cache[file_name]

        # If still not found, perform a direct lookup
        query = f"name='{file_name}' and '{GoogleDriveDataManager._data_folder_id}' in parents and trashed=false"
        results = GoogleDriveDataManager._drive_service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)'
        ).execute()

        items = results.get('files', [])

        if items:
            # Cache the result for future use
            file_id = items[0]['id']
            GoogleDriveDataManager._file_id_cache[file_name] = file_id
            return file_id

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

        # Extract just the filename from the path
        file_name = os.path.basename(file_path)

        # Get the file ID
        file_id = drive_manager.get_file_id(file_name)

        if file_id:
            # Download file content
            request = GoogleDriveDataManager._drive_service.files().get_media(fileId=file_id)
            file_content = io.BytesIO()
            downloader = MediaIoBaseDownload(file_content, request)

            done = False
            while done is False:
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


def save_data(data, file_path):
    """
    Save data to a JSON file in Google Drive.

    Args:
        data: The data to save
        file_path (str): Path to the file (used as the filename in Drive)
    """
    try:
        # Initialize Drive manager
        drive_manager = GoogleDriveDataManager()

        # Convert data to JSON and then to bytes
        json_data = json.dumps(data, indent=4, ensure_ascii=False)
        file_content = io.BytesIO(json_data.encode('utf-8'))

        # Get file name from path
        file_name = os.path.basename(file_path)

        # Check if file already exists
        file_id = drive_manager.get_file_id(file_name)

        # Prepare media upload
        media = MediaIoBaseUpload(
            file_content,
            mimetype='application/json',
            resumable=True
        )

        if file_id:
            # Update existing file
            GoogleDriveDataManager._drive_service.files().update(
                fileId=file_id,
                media_body=media
            ).execute()
        else:
            # Create new file
            file_metadata = {
                'name': file_name,
                'parents': [GoogleDriveDataManager._data_folder_id]
            }

            file = GoogleDriveDataManager._drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()

            # Update cache with new file ID
            GoogleDriveDataManager._file_id_cache[file_name] = file.get('id')

    except Exception as e:
        # Log error but don't crash the application
        print(f"Error saving data to Google Drive: {str(e)}")


def list_files(prefix=None):
    """
    List files in the data folder.

    Args:
        prefix (str, optional): Filter files starting with this prefix

    Returns:
        list: List of file names
    """
    try:
        # Initialize Drive manager
        drive_manager = GoogleDriveDataManager()

        # Refresh cache to ensure we have the latest file list
        drive_manager.refresh_file_id_cache(force=True)

        # Filter by prefix if provided
        if prefix:
            return [name for name in GoogleDriveDataManager._file_id_cache.keys()
                    if name.startswith(prefix)]
        else:
            return list(GoogleDriveDataManager._file_id_cache.keys())

    except Exception as e:
        print(f"Error listing files from Google Drive: {str(e)}")
        return []


# For backwards compatibility, provide direct access to functions
if __name__ == "__main__":
    # Test the module
    test_data = {"test": "data", "number": 123}
    save_data(test_data, "test_file.json")
    loaded_data = load_data("test_file.json")
    print(f"Loaded data: {loaded_data}")

    all_files = list_files()
    print(f"Files in Google Drive: {all_files}")