from typing import Optional

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    query: str = Field(..., description="user query")
    session_id: str = Field(None, description="session id for query")
    is_stream: bool = Field(False, description="whether use stream mode")
    focus_file_titles: Optional[list[str]] = Field(
        default=None,
        description=(
            "Optional allow-list of file_titles. When provided, the requester is "
            "asserting the user has data-permission to these chunks; RAG MAY "
            "use this to bias retrieval. Currently informational — surfaced in "
            "init_state['focus_file_titles'] for downstream nodes / observability."
        ),
    )

class QueryResponse(BaseModel):
    message: str
    session_id: str
    answer: str

class StreamSubmitResponse(BaseModel):
    message: str
    session_id: str
    task_id: str