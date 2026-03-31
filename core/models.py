"""
core/models.py

All shared data shapes for the Narada pipeline.
Interfaces are defined here first — all agents and providers
depend on these shapes. Nothing downstream redefines them.
"""

from pydantic import BaseModel


# --------------------------------------------------------------------------- #
# Search layer
# --------------------------------------------------------------------------- #

class SearchResult(BaseModel):
    """A single result returned by the search provider."""
    url: str
    title: str
    snippet: str


class ScrapedPage(BaseModel):
    """Cleaned plain-text content scraped from a URL."""
    url: str
    title: str
    content: str  # HTML stripped — plain text only


# --------------------------------------------------------------------------- #
# Extraction layer
# --------------------------------------------------------------------------- #

class CellValue(BaseModel):
    """
    A single attribute value for an entity.
    source_url makes every cell in the output table traceable
    back to the exact page it came from.
    """
    value: str
    source_url: str


class Entity(BaseModel):
    """
    A discovered entity — a company, restaurant, tool, person, etc.
    attributes maps column name to a CellValue (value + source).
    """
    name: str
    attributes: dict[str, CellValue]


# --------------------------------------------------------------------------- #
# Query analysis layer
# --------------------------------------------------------------------------- #

class QueryAnalysis(BaseModel):
    """
    Output from the query analyzer agent.
    Produced before any search or scraping happens.
    Determines the schema and search strategy for the entire run.
    """
    entity_type: str          # e.g. "company", "restaurant", "open-source tool"
    attributes: list[str]     # columns to extract, e.g. ["funding", "founded", "hq"]
    search_queries: list[str] # 2-3 targeted queries to run against the search provider


# --------------------------------------------------------------------------- #
# Pipeline output
# --------------------------------------------------------------------------- #

class PipelineMetadata(BaseModel):
    """Diagnostic info attached to every pipeline run."""
    search_provider: str
    llm_provider: str
    llm_model: str
    pages_scraped: int
    duration_seconds: float


class PipelineResult(BaseModel):
    """
    Final output of a full Narada pipeline run.
    Returned by the API and consumed by the frontend.
    """
    query: str
    entity_type: str
    attributes: list[str]     # ordered column names
    entities: list[Entity]    # rows in the output table
    metadata: PipelineMetadata
