from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, UniqueConstraint, Index, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.connection import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # User limits and stats
    document_count = Column(Integer, default=0)
    query_count_today = Column(Integer, default=0)
    last_query_date = Column(DateTime(timezone=True))
    
    # Relationships
    documents = relationship("Document", back_populates="owner", cascade="all, delete-orphan")
    queries = relationship("QueryLog", back_populates="user", cascade="all, delete-orphan")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_user_email', 'email'),
        Index('idx_user_active', 'is_active'),
    )

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    content_hash = Column(String(64), nullable=False)  # For deduplication
    chunk_count = Column(Integer, default=0)
    file_size = Column(Integer, nullable=False)  # in bytes
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    owner = relationship("User", back_populates="documents")
    
    # Ensure unique content per user (prevent duplicates)
    __table_args__ = (
        UniqueConstraint('user_id', 'content_hash', name='unique_user_document'),
        Index('idx_document_user_id', 'user_id'),
        Index('idx_document_hash', 'content_hash'),
    )

class QueryLog(Base):
    __tablename__ = "query_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    response_time = Column(Integer)  # in milliseconds
    chunks_used = Column(Integer, default=0)  # number of chunks used for context
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="queries")
    
    # Indexes for performance and analytics
    __table_args__ = (
        Index('idx_query_user_id', 'user_id'),
        Index('idx_query_created_at', 'created_at'),
        Index('idx_query_user_date', 'user_id', 'created_at'),
    )

class UserSession(Base):
    """Track user sessions for rate limiting and analytics"""
    __tablename__ = "user_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_token = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_activity = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)
    
    # Indexes
    __table_args__ = (
        Index('idx_session_token', 'session_token'),
        Index('idx_session_user_active', 'user_id', 'is_active'),
    )