import os
import aiofiles
import uuid
from pathlib import Path
from app.application.interfaces.services.file_storage_service import FileStorageService


class LocalFileStorageService(FileStorageService):
    """Local filesystem implementation of file storage"""
    
    def __init__(self, upload_dir: str = None):
        if upload_dir is None:
            project_root = Path(__file__).parent.parent.parent.parent
            upload_dir = project_root / "uploads"

        self.upload_dir = Path(upload_dir)
        # Create upload directory if it doesn't exist
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        print(f"📁 Upload directory: {self.upload_dir.absolute()}")
    
    async def save_file(
        self,
        file_content: bytes,
        file_name: str,
        content_type: str
    ) -> str:
        """
        Save file to local filesystem
        
        Args:
            file_content: File binary content
            file_name: Original file name
            content_type: MIME type
            
        Returns:
            File path where the file was saved
        """
        
        # Generate unique filename
        file_ext = file_name.rsplit(".", 1)[-1] if "." in file_name else ""
        unique_name = f"{uuid.uuid4()}.{file_ext}" if file_ext else str(uuid.uuid4())
        
        file_path = self.upload_dir / unique_name
        
        # Save file
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(file_content)
        
        return str(file_path)
    
    async def delete_file(self, file_path: str) -> bool:
        """
        Delete file from local filesystem
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if deleted, False otherwise
        """
        try:
            path = Path(file_path)
            if path.exists() and path.is_file():
                path.unlink()
                return True
            return False
        except Exception:
            return False
    
    async def get_file(self, file_path: str) -> bytes:
        """
        Get file content from local filesystem
        
        Args:
            file_path: Path to the file
            
        Returns:
            File binary content
        """
        async with aiofiles.open(file_path, "rb") as f:
            return await f.read()