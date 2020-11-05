"""Pydantic model for the Problem response schema."""

from typing import Optional

from pydantic import BaseModel


class Problem(BaseModel):
    """Model of the RFC7807 Problem response schema."""

    type: str
    title: str
    status: Optional[int]
    detail: Optional[str]
    instance: Optional[str]
