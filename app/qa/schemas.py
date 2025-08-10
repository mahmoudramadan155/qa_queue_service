# app/qa/schemas.py
from pydantic import BaseModel
from typing import List, Optional, Literal, Dict, Any
from datetime import datetime

class DocumentUpload(BaseModel):
    filename: str
    chunk_count: int
    content_hash: str
    task_id: Optional[str] = None
    status: Literal["processing", "completed", "failed"] = "completed"

class DocumentInfo(BaseModel):
    id: int
    filename: str
    chunk_count: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class QuestionRequest(BaseModel):
    question: str

class QuestionResponse(BaseModel):
    question: str
    answer: str
    response_time_ms: int
    task_id: Optional[str] = None
    status: Literal["processing", "completed", "failed"] = "completed"

class StreamingChunk(BaseModel):
    """Individual streaming response chunk"""
    type: Literal["status", "chunk", "complete", "error"]
    content: Optional[str] = None
    message: Optional[str] = None
    response_time: Optional[int] = None

class QueryLogInfo(BaseModel):
    id: int
    question: str
    answer: str
    response_time: int
    chunks_used: Optional[int] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class LLMInfo(BaseModel):
    """Information about the current LLM being used"""
    type: str
    model: Optional[str] = None
    url: Optional[str] = None
    available: Optional[bool] = None
    streaming_supported: bool = False
    has_api_key: Optional[bool] = None

class LLMStatusResponse(BaseModel):
    """Response for LLM status endpoint"""
    status: str
    llm_info: LLMInfo
    queue_status: Dict[str, Any]
    settings: dict
    error: Optional[str] = None

class TaskStatus(BaseModel):
    """Task status response"""
    task_id: str
    status: Literal["PENDING", "PROCESSING", "SUCCESS", "FAILURE", "RETRY", "REVOKED"]
    progress: Optional[int] = None
    message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

class NotificationInfo(BaseModel):
    """User notification"""
    id: str
    type: str
    message: str
    data: Dict[str, Any]
    timestamp: datetime
    read: bool = False

class UserReport(BaseModel):
    """Comprehensive user activity report"""
    user_id: int
    email: str
    member_since: datetime
    report_period_days: int
    documents: Dict[str, Any]
    queries: Dict[str, Any]
    limits: Dict[str, Any]

class QueueStatus(BaseModel):
    """Queue system status"""
    queue_lengths: Dict[str, int]
    active_tasks: int
    scheduled_tasks: int
    system_load: str

class BulkOperationRequest(BaseModel):
    """Request for bulk operations"""
    operation_type: str
    target_ids: List[int]
    operation_data: Optional[Dict[str, Any]] = None

class BulkOperationResponse(BaseModel):
    """Response for bulk operations"""
    operation_id: str
    status: str
    total_items: int
    processed_items: int
    failed_items: int
    results: List[Dict[str, Any]]