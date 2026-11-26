"""Validated metadata schema for MonsoonMind source documents."""

from pydantic import BaseModel, Field


class DocMeta(BaseModel):
    """Structured metadata extracted from an IMD report."""

    title: str = Field(description="Document title")
    doc_type: str = Field(description="Document category, such as monsoon_report or cyclone_report")
    year: int | None = Field(default=None, description="Report year")
    state: str | None = Field(
        default="Tamil Nadu",
        description="State or region covered by the report",
    )
    districts: list[str] = Field(
        default_factory=list,
        description="Districts explicitly mentioned in the report",
    )
    topics: list[str] = Field(
        default_factory=list,
        description="Weather topics covered, such as rainfall or cyclone",
    )
    language: str = Field(
        default="English",
        description="Primary language of the document",
    )
