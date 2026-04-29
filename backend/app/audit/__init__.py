"""F04 — Module audit log append-only.

Re-export public surface for F17 (LLM mutations) consumption.
"""

from app.audit.decorator import journal_llm_mutation
from app.audit.helper import record_audit
from app.audit.schemas import AuditLogEntryIn, AuditLogEntryOut, SourceOfChange

__all__ = [
    "AuditLogEntryIn",
    "AuditLogEntryOut",
    "SourceOfChange",
    "journal_llm_mutation",
    "record_audit",
]
