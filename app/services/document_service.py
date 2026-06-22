from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.schemas.document import DocumentCreate, DocumentRead


class DocumentService:
    def __init__(self) -> None:
        self._store: dict[UUID, DocumentRead] = {}
        self._by_project: dict[UUID, list[UUID]] = {}

    def create(self, project_id: UUID, payload: DocumentCreate) -> DocumentRead:
        now = datetime.now(timezone.utc)
        doc = DocumentRead(
            id=uuid4(),
            project_id=project_id,
            kind=payload.kind,
            title=payload.title,
            content=payload.content,
            created_at=now,
        )
        self._store[doc.id] = doc
        self._by_project.setdefault(project_id, []).append(doc.id)
        return doc

    def list_for_project(self, project_id: UUID) -> list[DocumentRead]:
        ids = self._by_project.get(project_id, [])
        return [self._store[doc_id] for doc_id in ids]
