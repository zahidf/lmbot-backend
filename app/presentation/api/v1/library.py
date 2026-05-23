from io import BytesIO
import logging
from urllib.parse import quote

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    Query,
    UploadFile,
    status,
)
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
    return _ranged_file_stream_response(result, disposition, None)


def _parse_range_header(range_header: str, content_length: int) -> tuple[int, int]:
    if not range_header.startswith("bytes="):
        raise ValueError("Invalid Range header")
    if "," in range_header:
        raise ValueError("Multiple ranges are not supported")
    if content_length <= 0:
        raise ValueError("Range not satisfiable")

    range_spec = range_header.removeprefix("bytes=").strip()
    if "-" not in range_spec:
        raise ValueError("Invalid Range header")

    start_text, end_text = range_spec.split("-", 1)
    if not start_text and not end_text:
        raise ValueError("Invalid Range header")

    if not start_text:
        suffix_length = int(end_text)
        if suffix_length <= 0:
            raise ValueError("Range not satisfiable")
        start = max(content_length - suffix_length, 0)
        end = content_length - 1
        return start, end

    start = int(start_text)
    end = int(end_text) if end_text else content_length - 1
    if start < 0 or end < start or start >= content_length:
        raise ValueError("Range not satisfiable")
    return start, min(end, content_length - 1)


def _range_not_satisfiable(content_length: int) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_416_RANGE_NOT_SATISFIABLE,
        detail="Range not satisfiable",
        headers={
            "Accept-Ranges": "bytes",
            "Content-Range": f"bytes */{content_length}",
        },
    )


def _ranged_file_stream_response(
    result,
    disposition: str,
    range_header: str | None,
) -> StreamingResponse:
    encoded_name = quote(result.file.original_file_name)
    content = result.content
    content_length = len(content)
    response_status = status.HTTP_200_OK
    headers = {
        "Accept-Ranges": "bytes",
        "Content-Disposition": (f"{disposition}; filename*=UTF-8''{encoded_name}"),
        "Content-Length": str(content_length),
        "X-Content-Type-Options": "nosniff",
    }

    if range_header:
        try:
            start, end = _parse_range_header(range_header, content_length)
        except (TypeError, ValueError):
            raise _range_not_satisfiable(content_length)

        content = content[start : end + 1]
        response_status = status.HTTP_206_PARTIAL_CONTENT
        headers["Content-Range"] = f"bytes {start}-{end}/{content_length}"
        headers["Content-Length"] = str(len(content))

    return StreamingResponse(
        BytesIO(content),
        status_code=response_status,
        media_type=result.file.content_type,
        headers=headers,
    )


@router.get("/items", response_model=LibraryItemsResponse)
async def list_library_items(
    folder_id: str | None = Query(
        None,
        description=(
            "Folder to browse. Without search this lists direct children only; with "
            "search it restricts results to this folder's recursive subtree."
        ),
    ),
    search: str | None = Query(
        None,
        description=(
            "Case-insensitive name search. With folder_id, searches the full subtree "
            "under that folder; without folder_id, searches the whole accessible "
            "library."
        ),
    ),
    type: str | None = Query(None, description="Optional library type filter."),
    date: str | None = Query(
        None,
        description=(
            "Date sort direction. Use oldest for ascending; any other/omitted value "
            "sorts newest first. Mutually exclusive with size sorting."
        ),
    ),
    size: str | None = Query(
        None,
        description=(
            "Size sort direction: largest or smallest. This is a separate sort axis "
            "from date and takes precedence when provided."
        ),
    ),
    limit: int = Query(100, description="Maximum items to return, capped at 100."),
    offset: int = Query(0, description="Offset into the filtered result set."),
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
                    item_count=item.item_count,
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


@router.get(
    "/files/{file_id}/download",
    responses={
        206: {"description": "Partial content for a valid HTTP Range request."},
        416: {"description": "Range not satisfiable."},
    },
)
async def download_library_file(
    file_id: str,
    range_header: str | None = Header(
        None,
        alias="Range",
        description="Optional byte range, e.g. bytes=0-1023, bytes=1024-, bytes=-500.",
    ),
    current_user=Depends(get_current_user),
    use_case: DownloadLibraryFile = Depends(get_download_library_file_use_case),
):
    try:
        result = await use_case.execute(file_id)
        return _ranged_file_stream_response(result, "attachment", range_header)
    except HTTPException:
        raise
    except ValueError as e:
        _raise_for_value_error(e)
    except Exception as e:
        logger.error(f"Download library file failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get(
    "/files/{file_id}/preview",
    responses={
        206: {"description": "Partial content for a valid HTTP Range request."},
        416: {"description": "Range not satisfiable."},
    },
)
async def preview_library_file(
    file_id: str,
    range_header: str | None = Header(
        None,
        alias="Range",
        description="Optional byte range, e.g. bytes=0-1023, bytes=1024-, bytes=-500.",
    ),
    current_user=Depends(get_current_user),
    use_case: DownloadLibraryFile = Depends(get_download_library_file_use_case),
):
    try:
        result = await use_case.execute(file_id)
        return _ranged_file_stream_response(result, "inline", range_header)
    except HTTPException:
        raise
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
