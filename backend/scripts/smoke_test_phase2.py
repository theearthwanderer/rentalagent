import asyncio
import sys
from pathlib import Path

# Fix Path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(backend_dir))

from app.tools.search import SearchListingsTool
import structlog

# Simple logger config
structlog.configure(
    processors=[
        structlog.processors.JSONRenderer()
    ]
)

async def main():
    tool = SearchListingsTool()
    
    print("\n--- TEST 1: Basic Search (San Francisco) ---")
    results = await tool.execute(query="apartment in San Francisco")
    print(f"Found {len(results)} results")
    if results:
        print(f"Top 1: {results[0]['title']} (${results[0]['price']})")

    print("\n--- TEST 2: Pets Allowed (Boolean) ---")
    # Should only return pets_allowed=True
    results_pets = await tool.execute(query="pet friendly", pets_allowed=True)
    print(f"Found {len(results_pets)} pet-friendly results")
    # Verify
    all_pets = all(r['pets_allowed'] for r in results_pets)
    print(f"VERIFICATION: All results have pets_allowed=True? {all_pets}")
    
    print("\n--- TEST 3: Vibe Score Filter (>4.8) ---")
    results_vibe = await tool.execute(query="nice place", min_vibe=4.8)
    print(f"Found {len(results_vibe)} high-vibe results")
    all_vibe = all(r['vibe_score'] >= 4.8 for r in results_vibe)
    print(f"VERIFICATION: All results have vibe >= 4.8? {all_vibe}")
    
    print("\n--- TEST 4: Parking + Laundry ---")
    results_pl = await tool.execute(query="convenient", parking=True, laundry=True)
    print(f"Found {len(results_pl)} results with Parking+Laundry")
    all_pl = all(r['parking'] and r['laundry'] for r in results_pl)
    print(f"VERIFICATION: All have Parking+Laundry? {all_pl}")

if __name__ == "__main__":
    asyncio.run(main())
