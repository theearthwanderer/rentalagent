from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field
from lancedb.pydantic import Vector

class Listing(BaseModel):
    """Core Listing model for rental properties"""
    id: str
    title: str
    price: int
    beds: float
    baths: float
    city: str
    neighborhood: str
    description: str
    amenities: list[str] = Field(default_factory=list)
    external_url: str
    
    # Metadata
    source: str = "seed"
    is_active: bool = True
    last_scraped_at: datetime = Field(default_factory=datetime.now)
    last_embedded_at: datetime | None = None
    
    # Vector for LanceDB
    vector: Vector(768)

    model_config = ConfigDict(extra="ignore")

class SearchResult(BaseModel):
    listing: Listing
    distance: float | None = None
