from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.core.config import get_settings
from app.db.session import get_db
from app.models import AdminUser, KnowledgeDocument
from app.services.knowledge_file_ingest import extract_knowledge_file_text, title_from_upload
from app.services.knowledge_rag import reindex_document

router = APIRouter(prefix="/api/admin/knowledge", tags=["admin"])


class DocumentListItem(BaseModel):
    id: int
    title: str
    is_published: bool
    body_preview: str
    created_at: str
    updated_at: str

    @classmethod
    def from_orm_list(cls, d: KnowledgeDocument) -> "DocumentListItem":
        b = d.body or ""
        return cls(
            id=d.id,
            title=d.title,
            is_published=d.is_published,
            body_preview=(b[:200] + "…") if len(b) > 200 else b,
            created_at=d.created_at.isoformat(),
            updated_at=d.updated_at.isoformat(),
        )


class DocumentOut(BaseModel):
    id: int
    title: str
    is_published: bool
    body: str
    body_preview: str
    created_at: str
    updated_at: str

    @classmethod
    def from_orm_row(cls, d: KnowledgeDocument) -> "DocumentOut":
        b = d.body or ""
        return cls(
            id=d.id,
            title=d.title,
            is_published=d.is_published,
            body=b,
            body_preview=(b[:200] + "…") if len(b) > 200 else b,
            created_at=d.created_at.isoformat(),
            updated_at=d.updated_at.isoformat(),
        )


class DocumentIn(BaseModel):
    title: str = Field(min_length=1, max_length=512)
    body: str = Field(min_length=0, max_length=1_000_000)
    is_published: bool = False


@router.get("/documents", response_model=list[DocumentListItem])
def list_docs(
    _: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> list[DocumentListItem]:
    rows = (
        db.execute(select(KnowledgeDocument).order_by(KnowledgeDocument.updated_at.desc()))
        .scalars()
        .all()
    )
    return [DocumentListItem.from_orm_list(d) for d in rows]


@router.post("/documents", response_model=DocumentOut)
def create_doc(
    body: DocumentIn,
    _: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> DocumentOut:
    d = KnowledgeDocument(
        title=body.title.strip(), body=body.body or "", is_published=body.is_published
    )
    db.add(d)
    db.commit()
    db.refresh(d)
    reindex_document(db, d.id)
    return DocumentOut.from_orm_row(d)


def _form_bool(v: str) -> bool:
    return (v or "").strip().lower() in ("1", "true", "yes", "on")


@router.post("/documents/upload", response_model=DocumentOut)
async def create_doc_from_upload(
    file: UploadFile = File(...),
    title: str = Form(""),
    is_published: str = Form("false"),
    _: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> DocumentOut:
    settings = get_settings()
    max_b = max(256_000, int(settings.knowledge_upload_max_bytes))
    raw = await file.read()
    if len(raw) > max_b:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large (max {max_b // 1_048_576} MB).",
        )
    text, err = extract_knowledge_file_text(
        file.filename or "upload", raw, file.content_type
    )
    if err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err)
    t = (title or "").strip() or title_from_upload(file.filename or "article")
    published = _form_bool(is_published)
    d = KnowledgeDocument(title=t, body=text or "", is_published=published)
    db.add(d)
    db.commit()
    db.refresh(d)
    reindex_document(db, d.id)
    return DocumentOut.from_orm_row(d)


@router.get("/documents/{doc_id}", response_model=DocumentOut)
def get_doc(
    doc_id: int,
    _: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> DocumentOut:
    d = db.get(KnowledgeDocument, doc_id)
    if d is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found")
    return DocumentOut.from_orm_row(d)


@router.put("/documents/{doc_id}", response_model=DocumentOut)
def put_doc(
    doc_id: int,
    body: DocumentIn,
    _: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> DocumentOut:
    d = db.get(KnowledgeDocument, doc_id)
    if d is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found")
    d.title = body.title.strip()
    d.body = body.body or ""
    d.is_published = body.is_published
    db.add(d)
    db.commit()
    db.refresh(d)
    reindex_document(db, d.id)
    return DocumentOut.from_orm_row(d)


@router.delete("/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_doc(
    doc_id: int,
    _: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> None:
    d = db.get(KnowledgeDocument, doc_id)
    if d is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found")
    db.delete(d)
    db.commit()
