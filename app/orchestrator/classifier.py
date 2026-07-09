import re

from app.orchestrator.enums import RequestCategory


_IMAGE_EXT = re.compile(r"\.(png|jpg|jpeg)\b", re.IGNORECASE)
_DOC_EXT = re.compile(r"\.(pdf|docx?)\b", re.IGNORECASE)

_IMAGE_KEYWORDS = {"image", "picture", "photo", "analyze image", "upload image"}
_DOC_QUERY_KEYWORDS = {
    "summarize", "summarise", "search document", "find contract",
    "extract from document", "document query", "find in document",
}
_DOC_UPLOAD_KEYWORDS = {
    "upload document", "upload file", "upload pdf", "upload doc",
    "attach file", "upload", "pdf", "docx",
}
_MEETING_KEYWORDS = {"minutes", "mom", "meeting", "transcript", "meeting notes", "agenda"}
_TASK_KEYWORDS = {"task", "deadline", "reminder", "todo", "to-do", "assign", "follow-up"}
_COMPANY_KEYWORDS = {
    "nurofin", "vendor", "project", "employee", "finance",
    "agreement", "customer", "proposal", "policy", "internal",
    "meeting notes", "company", "hr", "payroll", "contract",
    "revenue", "quarterly", "board", "expense", "budget",
    "invoice", "purchase order", "po", "sow", "statement of work",
    "ndp", "nda", "non-disclosure", "sla", "kpi",
    "department", "team", "headcount", "hiring", "onboarding",
    "salary", "compensation", "benefits", "insurance",
    "audit", "compliance", "regulation", "approval",
    "submission", "nuro", "mou", "confidential",
}


class Classifier:
    def classify(self, message: str) -> RequestCategory:
        lower = message.lower()

        if _IMAGE_EXT.search(lower) or any(k in lower for k in _IMAGE_KEYWORDS):
            return RequestCategory.IMAGE_ANALYSIS

        if any(k in lower for k in _DOC_QUERY_KEYWORDS):
            return RequestCategory.DOCUMENT_QUERY

        if _DOC_EXT.search(lower) or any(k in lower for k in _DOC_UPLOAD_KEYWORDS):
            return RequestCategory.DOCUMENT_UPLOAD

        if any(k in lower for k in _MEETING_KEYWORDS):
            return RequestCategory.MEETING

        if any(k in lower for k in _TASK_KEYWORDS):
            return RequestCategory.TASK_ASSISTANT

        if any(k in lower for k in _COMPANY_KEYWORDS):
            return RequestCategory.COMPANY_KNOWLEDGE

        return RequestCategory.GENERAL_CHAT
