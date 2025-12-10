import sys
import os
import asyncio

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.tools.search import SearchListingsTool
import structlog

logger = structlog.get_logger()

async def main():
    logger.info("Starting smoke test...")
    tool = SearchListingsTool()
    
    query = "modern apartment in SoMa under 4000"
    logger.info(f"Running search for: '{query}'")
    
    results = await tool.execute(query=query, min_price=None, max_price=4000)
    
    print(f"\nFound {len(results)} results:")
    for res in results:
        print(f"- {res['title']} (${res['price']}): {res['description'][:50]}...")

if __name__ == "__main__":
    asyncio.run(main())
