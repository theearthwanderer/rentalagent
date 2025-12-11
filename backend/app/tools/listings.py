from typing import List, Optional
from pydantic import BaseModel, Field
from app.tools.base import Tool
from app.db.client import get_lancedb_client
import structlog

logger = structlog.get_logger()

class GetListingDetailsParameters(BaseModel):
    listing_id: str = Field(..., description="ID of the listing to retrieve details for")

class GetListingDetailsTool(Tool):
    name = "get_listing_details"
    description = "Retrieve full details for a specific listing by its ID. Use this when the user asks for more information about a specific apartment."
    parameters = GetListingDetailsParameters

    async def execute(self, listing_id: str) -> dict:
        logger.info(f"Fetching details for listing_id={listing_id}")
        
        client = get_lancedb_client()
        table = client.get_table()
        
        # LanceDB query by ID
        # exact match query
        results = table.search()\
            .where(f"id = '{listing_id}'")\
            .limit(1)\
            .to_list()
            
        if not results:
            return {"error": "Listing not found"}
            
        listing = results[0]
        
        # Cleanup for LLM consumption
        if "vector" in listing:
            del listing["vector"]
            
        return listing
