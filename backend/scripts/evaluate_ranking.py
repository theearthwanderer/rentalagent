import asyncio
import sys
from pathlib import Path
import json

# Fix Path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(backend_dir))

from app.tools.search import SearchListingsTool

GOLDEN_SET = [
    {
        "query": "Pet friendly apartment in Mission District",
        "expected_filters": {"pets_allowed": True},
        "expected_terms": ["Mission"]
    },
    {
        "query": "Quiet place with parking near Golden Gate Park",
        "expected_filters": {"parking": True},
        "expected_terms": [] # "Quiet" is semantic, difficult to check with exact term
    },
    {
        "query": "Cheap studio under $2000",
        "expected_filters": {"max_price": 2000},
        "expected_terms": []
    }
]

async def eval_ranking():
    tool = SearchListingsTool()
    print(f"--- Running Ranking Evaluation on {len(GOLDEN_SET)} queries ---\n")
    
    score_cards = []
    
    for case in GOLDEN_SET:
        q = case["query"]
        print(f"Query: '{q}'")
        
        # Execute Search (simulate how Agent uses it - Agent extracts filters first)
        # For this script, we assume the Agent *correctly* calls the tool with filters.
        # So we pass the "expected_filters" to the tool.
        # This tests the TOOL'S ranking, not the Agent's extraction (that's a different test).
        
        args = {"query": q}
        args.update(case["expected_filters"])
        
        results = await tool.execute(**args)
        
        # Evaluation
        top_5 = results[:5]
        hit = False
        
        # Check if top 5 satisfy the condition (redundant if using strict filters, but good sanity check)
        # AND check if they are relevant.
        
        print(f"  Returned {len(results)} results.")
        if not results:
            print("  [FAIL] No results found.")
            continue
            
        print(f"  Top 1: {results[0].get('title')} - ${results[0].get('price')}")
        
        # Metric: Hit@5
        # For "Pet friendly", verify they actually allow pets
        if "pets_allowed" in case["expected_filters"]:
            hits = sum(1 for r in top_5 if r.get('pets_allowed'))
            print(f"  Pet Friendly Hit Rate@5: {hits}/5")
            
        # For "Price", verify
        if "max_price" in case["expected_filters"]:
            hits = sum(1 for r in top_5 if r.get('price') <= case["expected_filters"]["max_price"])
            print(f"  Price Compliance Hit Rate@5: {hits}/5")
            
        print("")

if __name__ == "__main__":
    asyncio.run(eval_ranking())
