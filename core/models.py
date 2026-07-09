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
    back to the exact page it came from. source_quote is the exact
    sentence/phrase the value was pulled from — lets a user verify
    the claim without re-reading the whole page. confidence is the
    model's own certainty in [0, 1], used by the aggregator to break
    ties when two sources disagree on the same attribute.
    """
    value: str
    source_url: str
    source_quote: str = ""
    confidence: float = 0.5


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
    search_iterations: int = 1  # 1 = no agentic re-search needed, >1 = gap-filling rounds ran
    gap_ratio: float = 0.0      # fraction of empty cells in the final table


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
    errors: list[str] = []    # non-fatal issues encountered during the run (partial results still returned)
