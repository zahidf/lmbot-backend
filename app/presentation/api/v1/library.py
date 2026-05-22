from io import BytesIO
import logging
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse

from app.application.dtos.library_dtos import (
    LibraryBrowseDTO,
    LibraryCreateFolderDTO,
    LibraryUpdateFileDTO,
    LibraryUpdateFolderDTO,
    LibraryUploadFileDTO,
)
from app.application.use_cases.library.browse_library_items import BrowseLibraryItems
from app.application.use_cases.library.create_library_folder import CreateLibraryFolder
from app.application.use_cases.library.delete_library_file import DeleteLibraryFile
from app.application.use_cases.library.delete_library_folder import DeleteLibraryFolder
from app.application.use_cases.library.download_library_file import DownloadLibraryFile
from app.application.use_cases.library.get_library_file import GetLibraryFile
from app.application.use_cases.library.get_library_folder import GetLibraryFolder
from app.application.use_cases.library.update_library_file import UpdateLibraryFile
from app.application.use_cases.library.update_library_folder import UpdateLibraryFolder
from app.application.use_cases.library.upload_library_file import UploadLibraryFile
from app.presentation.api.dependencies import (
    get_browse_library_items_use_case,
    get_create_library_folder_use_case,
    get_current_admin_user,
    get_current_user,
    get_delete_library_file_use_case,
    get_delete_library_folder_use_case,
    get_download_library_file_use_case,
    get_get_library_file_use_case,
    get_get_library_folder_use_case,
    get_update_library_file_use_case,
    get_update_library_folder_use_case,
    get_upload_library_file_use_case,
)
from app.presentation.api.schemas.library_schemas import (
    LibraryDeleteResponse,
    LibraryFileResponse,
    LibraryFileUpdateRequest,
    LibraryFolderCreateRequest,
    LibraryFolderResponse,
    LibraryFolderUpdateRequest,
    LibraryItemResponse,
    LibraryItemsResponse,
)

router = APIRouter(prefix="/library", tags=["library"])
logger = logging.getLogger(__name__)


def _folder_response(folder) -> LibraryFolderResponse:
    return LibraryFolderResponse(
        id=folder.id,
        name=folder.name,
        parent_id=folder.parent_id,
        type=folder.type,
        description=folder.description,
        created_by=folder.created_by,
        created_at=folder.created_at,
        updated_at=folder.updated_at,
    )


def _file_response(file) -> LibraryFileResponse:
    return LibraryFileResponse(
        id=file.id,
        folder_id=file.folder_id,
        display_name=file.display_name,
        original_file_name=file.original_file_name,
        content_type=file.content_type,
        file_extension=file.file_extension,
        size_bytes=file.size_bytes,
        type=file.type,
        description=file.description,
        uploaded_by=file.uploaded_by,
        created_at=file.created_at,
        updated_at=file.updated_at,
    )


def _raise_for_value_error(error: ValueError) -> None:
    message = str(error)
    http_status = (
        status.HTTP_404_NOT_FOUND
        if "not found" in message.lower()
        else status.HTTP_400_BAD_REQUEST
    )
    raise HTTPException(status_code=http_status, detail=message)


def _file_stream_response(result, disposition: str) -> StreamingResponse:
    encoded_name = quote(result.file.original_file_name)
    return StreamingResponse(
        BytesIO(result.content),
        media_type=result.file.content_type,
        headers={
            "Content-Disposition": (f"{disposition}; filename*=UTF-8''{encoded_name}"),
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/items", response_model=LibraryItemsResponse)
async def list_library_items(
    folder_id: str | None = None,
    search: str | None = None,
    type: str | None = None,
    date: str | None = None,
    size: str | None = None,
    limit: int = 100,
    offset: int = 0,
    current_user=Depends(get_current_user),
    use_case: BrowseLibraryItems = Depends(get_browse_library_items_use_case),
):
    try:
        limit = min(max(limit, 1), 100)
        offset = max(offset, 0)
        result = await use_case.execute(
            LibraryBrowseDTO(
                folder_id=folder_id,
                search=search,
                type=type,
                date=date,
                size=size,
                limit=limit,
                offset=offset,
            )
        )
        return LibraryItemsResponse(
            folder=_folder_response(result.folder) if result.folder else None,
            breadcrumbs=[_folder_response(folder) for folder in result.breadcrumbs],
            items=[
                LibraryItemResponse(
                    id=item.id,
                    kind=item.kind,
                    name=item.name,
                    type=item.type,
                    size_bytes=item.size_bytes,
                    created_at=item.created_at,
                    updated_at=item.updated_at,
                )
                for item in result.items
            ],
            total=result.total,
        )
    except ValueError as e:
        _raise_for_value_error(e)
    except Exception as e:
        logger.error(f"List library items failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get("/folders/{folder_id}", response_model=LibraryFolderResponse)
async def get_library_folder(
    folder_id: str,
    current_user=Depends(get_current_user),
    use_case: GetLibraryFolder = Depends(get_get_library_folder_use_case),
):
    try:
        return _folder_response(await use_case.execute(folder_id))
    except ValueError as e:
        _raise_for_value_error(e)
    except Exception as e:
        logger.error(f"Get library folder failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.post(
    "/folders",
    response_model=LibraryFolderResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_library_folder(
    request: LibraryFolderCreateRequest,
    current_user=Depends(get_current_admin_user),
    use_case: CreateLibraryFolder = Depends(get_create_library_folder_use_case),
):
    try:
        folder = await use_case.execute(
            LibraryCreateFolderDTO(
                name=request.name,
                parent_id=request.parent_id,
                type=request.type,
                description=request.description,
                created_by=current_user["id"],
            )
        )
        return _folder_response(folder)
    except ValueError as e:
        _raise_for_value_error(e)
    except Exception as e:
        logger.error(f"Create library folder failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.patch("/folders/{folder_id}", response_model=LibraryFolderResponse)
async def update_library_folder(
    folder_id: str,
    request: LibraryFolderUpdateRequest,
    current_user=Depends(get_current_admin_user),
    use_case: UpdateLibraryFolder = Depends(get_update_library_folder_use_case),
):
    try:
        folder = await use_case.execute(
            LibraryUpdateFolderDTO(
                folder_id=folder_id,
                name=request.name,
                type=request.type,
                description=request.description,
            )
        )
        return _folder_response(folder)
    except ValueError as e:
        _raise_for_value_error(e)
    except Exception as e:
        logger.error(f"Update library folder failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.delete("/folders/{folder_id}", response_model=LibraryDeleteResponse)
async def delete_library_folder(
    folder_id: str,
    current_user=Depends(get_current_admin_user),
    use_case: DeleteLibraryFolder = Depends(get_delete_library_folder_use_case),
):
    try:
        deleted_id = await use_case.execute(folder_id)
        return LibraryDeleteResponse(
            message="Folder deleted successfully", id=deleted_id
        )
    except ValueError as e:
        _raise_for_value_error(e)
    except Exception as e:
        logger.error(f"Delete library folder failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get("/files/{file_id}", response_model=LibraryFileResponse)
async def get_library_file(
    file_id: str,
    current_user=Depends(get_current_user),
    use_case: GetLibraryFile = Depends(get_get_library_file_use_case),
):
    try:
        return _file_response(await use_case.execute(file_id))
    except ValueError as e:
        _raise_for_value_error(e)
    except Exception as e:
        logger.error(f"Get library file failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get("/files/{file_id}/download")
async def download_library_file(
    file_id: str,
    current_user=Depends(get_current_user),
    use_case: DownloadLibraryFile = Depends(get_download_library_file_use_case),
):
    try:
        result = await use_case.execute(file_id)
        return _file_stream_response(result, "attachment")
    except ValueError as e:
        _raise_for_value_error(e)
    except Exception as e:
        logger.error(f"Download library file failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get("/files/{file_id}/preview")
async def preview_library_file(
    file_id: str,
    current_user=Depends(get_current_user),
    use_case: DownloadLibraryFile = Depends(get_download_library_file_use_case),
):
    try:
        result = await use_case.execute(file_id)
        return _file_stream_response(result, "inline")
    except ValueError as e:
        _raise_for_value_error(e)
    except Exception as e:
        logger.error(f"Preview library file failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.post(
    "/files/upload",
    response_model=LibraryFileResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_library_file(
    file: UploadFile = File(...),
    folder_id: str = Form(...),
    type: str = Form(...),
    display_name: str | None = Form(None),
    description: str | None = Form(None),
    current_user=Depends(get_current_admin_user),
    use_case: UploadLibraryFile = Depends(get_upload_library_file_use_case),
):
    try:
        result = await use_case.execute(
            LibraryUploadFileDTO(
                file=file,
                folder_id=folder_id,
                type=type,
                display_name=display_name,
                description=description,
                uploaded_by=current_user["id"],
            )
        )
        return _file_response(result)
    except ValueError as e:
        _raise_for_value_error(e)
    except Exception as e:
        logger.error(f"Upload library file failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.patch("/files/{file_id}", response_model=LibraryFileResponse)
async def update_library_file(
    file_id: str,
    request: LibraryFileUpdateRequest,
    current_user=Depends(get_current_admin_user),
    use_case: UpdateLibraryFile = Depends(get_update_library_file_use_case),
):
    try:
        result = await use_case.execute(
            LibraryUpdateFileDTO(
                file_id=file_id,
                display_name=request.display_name,
                type=request.type,
                description=request.description,
            )
        )
        return _file_response(result)
    except ValueError as e:
        _raise_for_value_error(e)
    except Exception as e:
        logger.error(f"Update library file failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.delete("/files/{file_id}", response_model=LibraryDeleteResponse)
async def delete_library_file(
    file_id: str,
    current_user=Depends(get_current_admin_user),
    use_case: DeleteLibraryFile = Depends(get_delete_library_file_use_case),
):
    try:
        deleted_id = await use_case.execute(file_id)
        return LibraryDeleteResponse(message="File deleted successfully", id=deleted_id)
    except ValueError as e:
        _raise_for_value_error(e)
    except Exception as e:
        logger.error(f"Delete library file failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )
