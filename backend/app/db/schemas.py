from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field
from lancedb.pydantic import Vector

class Listing(BaseModel):
    """Core Listing model for rental properties"""
    id: str
    title: str
    price: int
    beds: int
    baths: int
    sqft: int
    city: str
    neighborhood: str
    description: str
    
    # New Fields for Phase 2 (Airbnb Data)
    pets_allowed: bool
    parking: bool
    laundry: bool
    air_conditioning: bool
    
    # Vibe & Scores
    vibe_score: float  # derived from review_rating
    location_score: float # derived from review_location
    safety_score: float # placeholder
    walkability_score: float # placeholder or derived
    
    amenities: list[str]
    images: list[str]
    created_at: datetime = Field(default_factory=datetime.now)

    # Vector for LanceDB
    vector: Vector(768)
    
    # Metadata
    external_url: str
    source: str = "seed"
    is_active: bool = True
    last_embedded_at: datetime | None = None
    
    # Vector for LanceDB
    vector: Vector(768)

    model_config = ConfigDict(extra="ignore")

class SearchResult(BaseModel):
    listing: Listing
    distance: float | None = None
