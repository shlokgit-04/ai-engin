from datetime import datetime
from pydantic import BaseModel, Field
from .classification import DocumentClassification


class DocumentMetadata(BaseModel):
    document_id: str = ""
    file_name: str = ""
    original_name: str = ""
    uploaded_by: str = ""
    department: str = ""
    project: str = ""
    document_type: str = ""
    confidentiality: DocumentClassification = DocumentClassification.INTERNAL
    version: int = 1
    page_count: int = 0
    page_number: int = 0
    chunk_index: int = 0
    date_uploaded: datetime | None = None
    last_modified: datetime | None = None
    file_size: int = 0
    mime_type: str = ""
    checksum: str = ""
    language: str = ""
    tags: list[str] = Field(default_factory=list)
    owner: str = ""
