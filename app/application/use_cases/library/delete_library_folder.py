from app.application.interfaces.repositories.library_repository import LibraryRepository


class DeleteLibraryFolder:
    def __init__(self, library_repository: LibraryRepository):
        self.library_repository = library_repository

    async def execute(self, folder_id: str) -> str:
        """Delete an empty folder."""
        folder = await self.library_repository.get_folder(folder_id)
        if not folder:
            raise ValueError("Folder not found")

        if await self.library_repository.folder_has_children(folder_id):
            raise ValueError("Folder must be empty before it can be deleted")

        deleted = await self.library_repository.delete_folder(folder_id)
        if not deleted:
            raise ValueError("Folder not found")
        return folder_id
