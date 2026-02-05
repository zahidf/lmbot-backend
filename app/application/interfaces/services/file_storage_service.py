from abc import ABC, abstractmethod
from typing import BinaryIO


class FileStorageService(ABC):
    """Interface for file storage operations"""
    
    @abstractmethod
    async def save_file(
        self,
        file_content: bytes,
        file_name: str,
        content_type: str
    ) -> str:
        """
        Save file to storage
        
        Args:
            file_content: File binary content
            file_name: Original file name
            content_type: MIME type
            
        Returns:
            File path where the file was saved
        """
        pass
    
    @abstractmethod
    async def delete_file(self, file_path: str) -> bool:
        """
        Delete file from storage
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if deleted, False otherwise
        """
        pass
    
    @abstractmethod
    async def get_file(self, file_path: str) -> bytes:
        """
        Get file content from storage
        
        Args:
            file_path: Path to the file
            
        Returns:
            File binary content
        """
        pass