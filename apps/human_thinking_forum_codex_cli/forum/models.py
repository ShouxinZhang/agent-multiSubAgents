from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=1, max_length=128)


class CreatePostRequest(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    content: str = Field(min_length=1, max_length=4000)


class CreateReplyRequest(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


@dataclass(frozen=True)
class AgentDefinition:
    agent_id: str
    name: str
    persona: str
    model: str
