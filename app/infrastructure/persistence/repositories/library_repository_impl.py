import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, cast

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.interfaces.repositories.library_repository import LibraryRepository
from app.domain.entities.library_file import LibraryFile
from app.domain.entities.library_folder import LibraryFolder
from app.infrastructure.persistence.models.library_file_model import LibraryFileModel
from app.infrastructure.persistence.models.library_folder_model import (
    LibraryFolderModel,
)


class LibraryRepositoryImpl(LibraryRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_folder_entity(self, model: LibraryFolderModel) -> LibraryFolder:
        return LibraryFolder(
            id=str(model.id),
            name=cast(str, model.name),
            parent_id=str(model.parent_id) if model.parent_id else None,
            type=cast(str, model.type),
            description=cast(Optional[str], model.description),
            created_by=str(model.created_by),
            created_at=cast(datetime, model.created_at),
            updated_at=cast(datetime, model.updated_at),
        )

    def _to_file_entity(self, model: LibraryFileModel) -> LibraryFile:
        return LibraryFile(
            id=str(model.id),
            folder_id=str(model.folder_id),
            display_name=cast(str, model.display_name),
            original_file_name=cast(str, model.original_file_name),
            storage_path=cast(str, model.storage_path),
            content_type=cast(str, model.content_type),
            file_extension=cast(str, model.file_extension),
            size_bytes=cast(int, model.size_bytes),
            type=cast(str, model.type),
            description=cast(Optional[str], model.description),
            uploaded_by=str(model.uploaded_by),
            created_at=cast(datetime, model.created_at),
            updated_at=cast(datetime, model.updated_at),
        )

    async def save_folder(self, folder: LibraryFolder) -> LibraryFolder:
        model = LibraryFolderModel(
            id=uuid.UUID(folder.id) if folder.id else uuid.uuid4(),
            name=folder.name,
            parent_id=uuid.UUID(folder.parent_id) if folder.parent_id else None,
            type=folder.type,
            description=folder.description,
            created_by=uuid.UUID(folder.created_by),
            created_at=folder.created_at,
            updated_at=folder.updated_at,
        )
        self.session.add(model)
        await self.session.flush()
        return self._to_folder_entity(model)

    async def get_folder(self, folder_id: str) -> Optional[LibraryFolder]:
        result = await self.session.execute(
            select(LibraryFolderModel).where(
                LibraryFolderModel.id == uuid.UUID(folder_id)
            )
        )
        model = result.scalar_one_or_none()
        return self._to_folder_entity(model) if model else None

    async def update_folder(self, folder: LibraryFolder) -> LibraryFolder:
        result = await self.session.execute(
            update(LibraryFolderModel)
            .where(LibraryFolderModel.id == uuid.UUID(folder.id or ""))
            .values(
                name=folder.name,
                type=folder.type,
                description=folder.description,
                updated_at=folder.updated_at,
            )
            .returning(LibraryFolderModel)
        )
        model = result.scalar_one()
        await self.session.flush()
        return self._to_folder_entity(model)

    async def delete_folder(self, folder_id: str) -> bool:
        result = await self.session.execute(
            delete(LibraryFolderModel).where(
                LibraryFolderModel.id == uuid.UUID(folder_id)
            )
        )
        return cast(Any, result).rowcount > 0

    async def list_folders(self, parent_id: Optional[str]) -> List[LibraryFolder]:
        query = select(LibraryFolderModel)
        if parent_id:
            query = query.where(LibraryFolderModel.parent_id == uuid.UUID(parent_id))
        else:
            query = query.where(LibraryFolderModel.parent_id.is_(None))

        result = await self.session.execute(query.order_by(LibraryFolderModel.name))
        return [self._to_folder_entity(model) for model in result.scalars().all()]

    async def list_folders_recursive(
        self, root_folder_id: Optional[str]
    ) -> List[LibraryFolder]:
        if root_folder_id is None:
            result = await self.session.execute(
                select(LibraryFolderModel).order_by(LibraryFolderModel.name)
            )
            return [self._to_folder_entity(model) for model in result.scalars().all()]

        descendants = (
            select(LibraryFolderModel.id)
            .where(LibraryFolderModel.parent_id == uuid.UUID(root_folder_id))
            .cte(name="library_folder_descendants", recursive=True)
        )
        descendants = descendants.union_all(
            select(LibraryFolderModel.id).where(
                LibraryFolderModel.parent_id == descendants.c.id
            )
        )

        result = await self.session.execute(
            select(LibraryFolderModel)
            .where(LibraryFolderModel.id.in_(select(descendants.c.id)))
            .order_by(LibraryFolderModel.name)
        )
        return [self._to_folder_entity(model) for model in result.scalars().all()]

    async def get_folder_child_counts(self, folder_ids: List[str]) -> Dict[str, int]:
        if not folder_ids:
            return {}

        folder_uuids = [uuid.UUID(folder_id) for folder_id in folder_ids]
        counts = {folder_id: 0 for folder_id in folder_ids}

        folder_result = await self.session.execute(
            select(
                LibraryFolderModel.parent_id,
                func.count(LibraryFolderModel.id),
            )
            .where(LibraryFolderModel.parent_id.in_(folder_uuids))
            .group_by(LibraryFolderModel.parent_id)
        )
        for parent_id, count in folder_result.all():
            counts[str(parent_id)] = counts.get(str(parent_id), 0) + int(count)

        file_result = await self.session.execute(
            select(
                LibraryFileModel.folder_id,
                func.count(LibraryFileModel.id),
            )
            .where(LibraryFileModel.folder_id.in_(folder_uuids))
            .group_by(LibraryFileModel.folder_id)
        )
        for folder_id, count in file_result.all():
            counts[str(folder_id)] = counts.get(str(folder_id), 0) + int(count)

        return counts

    async def get_folder_child_file_sizes(
        self, folder_ids: List[str]
    ) -> Dict[str, int]:
        if not folder_ids:
            return {}

        folder_uuids = [uuid.UUID(folder_id) for folder_id in folder_ids]
        result = await self.session.execute(
            select(
                LibraryFileModel.folder_id,
                func.coalesce(func.sum(LibraryFileModel.size_bytes), 0),
            )
            .where(LibraryFileModel.folder_id.in_(folder_uuids))
            .group_by(LibraryFileModel.folder_id)
        )
        return {
            str(folder_id): int(size_bytes) for folder_id, size_bytes in result.all()
        }

    async def folder_name_exists(
        self,
        parent_id: Optional[str],
        name: str,
        exclude_id: Optional[str] = None,
    ) -> bool:
        query = select(LibraryFolderModel.id).where(
            func.lower(LibraryFolderModel.name) == name.lower()
        )
        if parent_id:
            query = query.where(LibraryFolderModel.parent_id == uuid.UUID(parent_id))
        else:
            query = query.where(LibraryFolderModel.parent_id.is_(None))
        if exclude_id:
            query = query.where(LibraryFolderModel.id != uuid.UUID(exclude_id))

        result = await self.session.execute(query.limit(1))
        return result.scalar_one_or_none() is not None

    async def folder_has_children(self, folder_id: str) -> bool:
        folder_uuid = uuid.UUID(folder_id)
        folder_result = await self.session.execute(
            select(LibraryFolderModel.id)
            .where(LibraryFolderModel.parent_id == folder_uuid)
            .limit(1)
        )
        if folder_result.scalar_one_or_none() is not None:
            return True

        file_result = await self.session.execute(
            select(LibraryFileModel.id)
            .where(LibraryFileModel.folder_id == folder_uuid)
            .limit(1)
        )
        return file_result.scalar_one_or_none() is not None

    async def get_breadcrumbs(self, folder_id: str) -> List[LibraryFolder]:
        breadcrumbs: list[LibraryFolder] = []
        current = await self.get_folder(folder_id)
        while current:
            breadcrumbs.append(current)
            if not current.parent_id:
                break
            current = await self.get_folder(current.parent_id)
        breadcrumbs.reverse()
        return breadcrumbs

    async def save_file(self, file: LibraryFile) -> LibraryFile:
        model = LibraryFileModel(
            id=uuid.UUID(file.id) if file.id else uuid.uuid4(),
            folder_id=uuid.UUID(file.folder_id),
            display_name=file.display_name,
            original_file_name=file.original_file_name,
            storage_path=file.storage_path,
            content_type=file.content_type,
            file_extension=file.file_extension,
            size_bytes=file.size_bytes,
            type=file.type,
            description=file.description,
            uploaded_by=uuid.UUID(file.uploaded_by),
            created_at=file.created_at,
            updated_at=file.updated_at,
        )
        self.session.add(model)
        await self.session.flush()
        return self._to_file_entity(model)

    async def get_file(self, file_id: str) -> Optional[LibraryFile]:
        result = await self.session.execute(
            select(LibraryFileModel).where(LibraryFileModel.id == uuid.UUID(file_id))
        )
        model = result.scalar_one_or_none()
        return self._to_file_entity(model) if model else None

    async def update_file(self, file: LibraryFile) -> LibraryFile:
        result = await self.session.execute(
            update(LibraryFileModel)
            .where(LibraryFileModel.id == uuid.UUID(file.id or ""))
            .values(
                display_name=file.display_name,
                type=file.type,
                description=file.description,
                updated_at=file.updated_at,
            )
            .returning(LibraryFileModel)
        )
        model = result.scalar_one()
        await self.session.flush()
        return self._to_file_entity(model)

    async def delete_file(self, file_id: str) -> bool:
        result = await self.session.execute(
            delete(LibraryFileModel).where(LibraryFileModel.id == uuid.UUID(file_id))
        )
        return cast(Any, result).rowcount > 0

    async def list_files(self, folder_id: str) -> List[LibraryFile]:
        result = await self.session.execute(
            select(LibraryFileModel)
            .where(LibraryFileModel.folder_id == uuid.UUID(folder_id))
            .order_by(LibraryFileModel.display_name)
        )
        return [self._to_file_entity(model) for model in result.scalars().all()]

    async def list_files_recursive(
        self, root_folder_id: Optional[str]
    ) -> List[LibraryFile]:
        if root_folder_id is None:
            result = await self.session.execute(
                select(LibraryFileModel).order_by(LibraryFileModel.display_name)
            )
            return [self._to_file_entity(model) for model in result.scalars().all()]

        root_uuid = uuid.UUID(root_folder_id)
        descendants = (
            select(LibraryFolderModel.id)
            .where(LibraryFolderModel.parent_id == root_uuid)
            .cte(name="library_folder_descendants", recursive=True)
        )
        descendants = descendants.union_all(
            select(LibraryFolderModel.id).where(
                LibraryFolderModel.parent_id == descendants.c.id
            )
        )

        result = await self.session.execute(
            select(LibraryFileModel)
            .where(
                (LibraryFileModel.folder_id == root_uuid)
                | (LibraryFileModel.folder_id.in_(select(descendants.c.id)))
            )
            .order_by(LibraryFileModel.display_name)
        )
        return [self._to_file_entity(model) for model in result.scalars().all()]

    async def file_name_exists(
        self,
        folder_id: str,
        display_name: str,
        exclude_id: Optional[str] = None,
    ) -> bool:
        query = select(LibraryFileModel.id).where(
            LibraryFileModel.folder_id == uuid.UUID(folder_id),
            func.lower(LibraryFileModel.display_name) == display_name.lower(),
        )
        if exclude_id:
            query = query.where(LibraryFileModel.id != uuid.UUID(exclude_id))

        result = await self.session.execute(query.limit(1))
        return result.scalar_one_or_none() is not None
