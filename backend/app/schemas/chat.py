from pydantic import BaseModel
from typing import List, Optional

class ChatRequest(BaseModel):
    message: str
    thread_id: Optional[str] = None
    sessionId: Optional[str] = None
    agent_mode: Optional[str] = None
    agent_id: Optional[str] = None
    agent_model: Optional[str] = None
    agent_prompt: Optional[str] = None
    repository_id: Optional[str] = None
    force_rag: bool = False
    is_diagnosis: Optional[bool] = False
    problem_id: Optional[str] = None
    problem_title: Optional[str] = None
    user_code: Optional[str] = None
    course_dataset_ids: Optional[List[str]] = None
