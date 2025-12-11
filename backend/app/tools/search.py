from typing import List, Optional
from pydantic import BaseModel, Field
from app.tools.base import Tool
from app.db.client import get_lancedb_client
from app.services.embeddings import get_embedding_service
from app.db.schemas import SearchResult
import concurrent.futures
import asyncio
import structlog

logger = structlog.get_logger()

class SearchParameters(BaseModel):
    query: Optional[str] = Field(None, description="Natural language query. If omitted, performs a pure filter search (e.g. just by price/location).")
    min_price: Optional[int] = Field(None, description="Minimum price in USD")
    max_price: Optional[int] = Field(None, description="Maximum price in USD")
    min_beds: Optional[int] = Field(None, description="Minimum number of bedrooms")
    max_beds: Optional[int] = Field(None, description="Maximum number of bedrooms")
    min_baths: Optional[int] = Field(None, description="Minimum number of bathrooms")
    
    # New Phase 2 Filters
    pets_allowed: Optional[bool] = Field(None, description="If True, only show listings allowing pets")
    parking: Optional[bool] = Field(None, description="If True, only show listings with parking")
    laundry: Optional[bool] = Field(None, description="If True, only show listings with laundry")
    air_conditioning: Optional[bool] = Field(None, description="If True, only show listings with AC")
    
    min_vibe: Optional[float] = Field(None, description="Minimum vibe score (0-5)")
    city: Optional[str] = Field(None, description="City to filter by")
    neighborhood: Optional[str] = Field(None, description="Neighborhood to filter by")
    
    sort_by: Optional[str] = Field("relevance", description="Sort order: 'relevance', 'price_asc', 'price_desc', 'newest'")

class SearchListingsTool(Tool):
    name = "search_listings"
    description = "Search for rentals. Supports semantic query, boolean filters, and sorting."
    parameters = SearchParameters

    async def execute(self, query: str = None, 
                      min_price: int = None, max_price: int = None, 
                      min_beds: int = None, max_beds: int = None, 
                      min_baths: int = None, 
                      pets_allowed: bool = None, parking: bool = None,
                      laundry: bool = None, air_conditioning: bool = None,
                      min_vibe: float = None,
                      city: str = None, neighborhood: str = None,
                      sort_by: str = "relevance") -> List[dict]:
                      
        logger.info(f"Search: '{query}' filters={{price: {min_price}-{max_price}, pets: {pets_allowed}, sort: {sort_by}}}")
        
        client = get_lancedb_client()
        table = client.get_table()
        
        if query:
            # Semantic Search
            embedding_service = get_embedding_service()
            loop = asyncio.get_running_loop()
            vector = await loop.run_in_executor(None, embedding_service.get_embedding, query)
            search_builder = table.search(vector)
        else:
            # Pure Filter Search
            search_builder = table.search() # No vector
            
        search_builder.limit(50)

        # 3. Construct Filters
        filters = []
        if min_price is not None: filters.append(f"price >= {min_price}")
        if max_price is not None: filters.append(f"price <= {max_price}")
        if min_beds is not None: filters.append(f"beds >= {min_beds}")
        if max_beds is not None: filters.append(f"beds <= {max_beds}")
        if min_baths is not None: filters.append(f"baths >= {min_baths}")
        
        # Boolean filters - strictly enforce if requested
        if pets_allowed: filters.append("pets_allowed = true")
        if parking: filters.append("parking = true")
        if laundry: filters.append("laundry = true")
        if air_conditioning: filters.append("air_conditioning = true")
        
        if min_vibe is not None: filters.append(f"vibe_score >= {min_vibe}")
        if city: filters.append(f"city = '{city}'")
        if neighborhood: filters.append(f"neighborhood = '{neighborhood}'")
            
        if filters:
            filter_str = " AND ".join(filters)
            logger.debug(f"Applying filters: {filter_str}")
            search_builder.where(filter_str)

        # 4. Execute & Sort
        # LanceDB semantics: vector search always returns sorted by distance first. 
        # If we want exact sorting (e.g. price), we might need to post-sort or use specific LancDB API if available.
        # For now, we fetch results and post-sort in Python if sort_by != relevance.
        # This is acceptable for N=50.
        
        results = search_builder.to_list()
        
        # Post-processing
        listings = []
        for row in results:
            if "vector" in row: del row["vector"]
            if "_distance" in row:
                row["distance"] = row["_distance"]
                del row["_distance"]
            listings.append(row)
            
        # Python-side Sorting
        if sort_by == "price_asc":
            listings.sort(key=lambda x: x["price"])
        elif sort_by == "price_desc":
            listings.sort(key=lambda x: x["price"], reverse=True)
        elif sort_by == "newest":
            # Assuming created_at is comparable string or datetime, otherwise simplistic sort
            listings.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        # relevance is default (already sorted by vector distance)
            
        return listings
