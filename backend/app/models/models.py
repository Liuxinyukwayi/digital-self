from sqlalchemy import Column, Integer, String, Text, DateTime, Float, JSON, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class MemoryType(str, enum.Enum):
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    FACT = "fact"
    PREFERENCE = "preference"
    OPINION = "opinion"
    GOAL = "goal"
    RELATIONSHIP = "relationship"
    KNOWLEDGE = "knowledge"
    PERSONA = "persona"


class DataSource(str, enum.Enum):
    WECHAT = "wechat"
    QQ = "qq"
    FEISHU = "feishu"
    GITHUB = "github"
    EMAIL = "email"
    MANUAL = "manual"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    display_name = Column(String(100))
    persona_data = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    memories = relationship("Memory", back_populates="user")
    knowledge_items = relationship("Knowledge", back_populates="user")
    events = relationship("Event", back_populates="user")
    conversations = relationship("Conversation", back_populates="user")
    persona_profiles = relationship("PersonaProfile", back_populates="user")


class Memory(Base):
    __tablename__ = "memories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    content = Column(Text, nullable=False)
    summary = Column(Text)
    memory_type = Column(Enum(MemoryType), default=MemoryType.LONG_TERM)
    source = Column(Enum(DataSource))
    importance = Column(Integer, default=5)
    tags = Column(JSON)
    metadata_ = Column("metadata", JSON)
    embedding_id = Column(String(100))
    evidence_count = Column(Integer, default=1)
    confidence = Column(Float, default=0.5)
    last_evidence_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    accessed_at = Column(DateTime(timezone=True))

    user = relationship("User", back_populates="memories")


class Knowledge(Base):
    __tablename__ = "knowledge"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String(200), nullable=False)
    content = Column(Text)
    content_type = Column(String(50))
    category = Column(String(100))
    tags = Column(JSON)
    metadata_ = Column("metadata", JSON)
    embedding_id = Column(String(100))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="knowledge_items")


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String(200), nullable=False)
    description = Column(Text)
    event_date = Column(DateTime)
    event_type = Column(String(50))
    importance = Column(Integer, default=5)
    tags = Column(JSON)
    related_memory_ids = Column(JSON)
    metadata_ = Column("metadata", JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="events")


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String(200))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    metadata_ = Column("metadata", JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    conversation = relationship("Conversation", back_populates="messages")


class PersonaProfile(Base):
    __tablename__ = "persona_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    version = Column(Integer, default=1)
    interests = Column(JSON)
    values = Column(JSON)
    goals = Column(JSON)
    speech_style = Column(JSON)
    thinking_style = Column(String(200))
    summary = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="persona_profiles")
