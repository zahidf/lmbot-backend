import uuid
from supabase import create_client, Client
from app.application.interfaces.services.file_storage_service import FileStorageService


class SupabaseFileStorageService(FileStorageService):
    """Supabase Storage implementation of FileStorageService"""

    def __init__(
        self,
        supabase_url: str,
        supabase_service_key: str,
        bucket_name: str = "documents",
    ):
        self.bucket_name = bucket_name
        self.client: Client = create_client(supabase_url, supabase_service_key)

    async def save_file(
        self,
        file_content: bytes,
        file_name: str,
        content_type: str,
    ) -> str:
        """
        Upload file to Supabase Storage.
        Returns the storage key (e.g. "abc-123.pdf") stored in DocumentModel.file_path.
        """
        file_ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
        storage_key = f"{uuid.uuid4()}.{file_ext}" if file_ext else str(uuid.uuid4())

        self.client.storage.from_(self.bucket_name).upload(
            path=storage_key,
            file=file_content,
            file_options={
                "content-type": content_type,
                "upsert": "false",
            },
        )

        return storage_key

    async def delete_file(self, file_path: str) -> bool:
        try:
            self.client.storage.from_(self.bucket_name).remove([file_path])
            return True
        except Exception:
            return False

    async def get_file(self, file_path: str) -> bytes:
        return self.client.storage.from_(self.bucket_name).download(file_path)
