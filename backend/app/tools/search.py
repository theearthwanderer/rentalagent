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
    query: str = Field(..., description="Natural language query for the rental search (e.g. 'modern apartment in SoMa')")
    min_price: Optional[int] = Field(None, description="Minimum price in USD")
    max_price: Optional[int] = Field(None, description="Maximum price in USD")
    min_beds: Optional[float] = Field(None, description="Minimum number of bedrooms")
    max_beds: Optional[float] = Field(None, description="Maximum number of bedrooms")
    min_baths: Optional[float] = Field(None, description="Minimum number of bathrooms")
    city: Optional[str] = Field(None, description="City to filter by (e.g. 'San Francisco')")
    neighborhood: Optional[str] = Field(None, description="Neighborhood to filter by (e.g. 'SoMa')")

class SearchListingsTool(Tool):
    name = "search_listings"
    description = "Search for rental listings based on semantic query and filters. Use this when the user asks for apartments, houses, or rentals."
    parameters = SearchParameters

    async def execute(self, query: str, min_price: int = None, max_price: int = None, min_beds: float = None, max_beds: float = None, min_baths: float = None, city: str = None, neighborhood: str = None) -> List[dict]:
        logger.info(f"Executing search with query='{query}' filters={{min_price: {min_price}, max_price: {max_price}, min_beds: {min_beds}, max_beds: {max_beds}, min_baths: {min_baths}, city: {city}, neighborhood: {neighborhood}}}")
        
        # 1. Get Embedding (run in thread pool to avoid blocking)
        embedding_service = get_embedding_service()
        loop = asyncio.get_running_loop()
        vector = await loop.run_in_executor(None, embedding_service.get_embedding, query)

        # 2. Build Query
        client = get_lancedb_client()
        table = client.get_table()
        
        # LanceDB PyArrow/Pydantic search
        search_builder = table.search(vector)
        search_builder.limit(5)

        # Construct filter string (SQL-like for LanceDB)
        filters = []
        if min_price:
            filters.append(f"price >= {min_price}")
        if max_price:
            filters.append(f"price <= {max_price}")
        if min_beds:
            filters.append(f"beds >= {min_beds}")
        if max_beds:
            filters.append(f"beds <= {max_beds}")
        if min_baths:
            filters.append(f"baths >= {min_baths}")
        if city:
            filters.append(f"city = '{city}'")
        if neighborhood:
            filters.append(f"neighborhood = '{neighborhood}'")
            
        if filters:
            filter_str = " AND ".join(filters)
            logger.debug(f"Applying filters: {filter_str}")
            search_builder.where(filter_str)

        # 3. Execute
        results = search_builder.to_list()
        
        listings = []
        for row in results:
            # row is a dict. Remove vector for brevity in LLM context
            if "vector" in row:
                del row["vector"]
            # Convert _distance to distance if present
            if "_distance" in row:
                row["distance"] = row["_distance"]
                del row["_distance"]
                
            listings.append(row)
            
        return listings
