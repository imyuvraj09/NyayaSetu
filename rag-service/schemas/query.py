"""
Request schema for incoming legal queries.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional


class QueryRequest(BaseModel):
    """Schema for a user's legal question submitted to the RAG pipeline.

    Attributes:
        query:      The legal question (3–2000 characters, stripped).
        session_id: Optional session identifier for conversation tracking.
    """

    query: str = Field(
        ...,
        min_length=3,
        max_length=2000,
        description="The legal question to ask (3–2000 characters).",
        examples=["What are my legal rights if someone threatens me?"],
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Optional session ID for conversation continuity.",
        examples=["session-abc-123"],
    )

    @field_validator("query", mode="before")
    @classmethod
    def strip_and_validate_query(cls, value: str) -> str:
        """Strip whitespace; reject empty or blank strings."""
        if not isinstance(value, str):
            raise ValueError("query must be a string")
        stripped = value.strip()
        if not stripped:
            raise ValueError("query cannot be empty or blank")
        return stripped

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "query": "What are my legal rights if someone threatens me?",
                    "session_id": "test-session-001",
                }
            ]
        }
    }
