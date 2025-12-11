import csv
import json
import logging
import sys
import os
from datetime import datetime
from pathlib import Path

# Add backend directory to python path
# If we are in backend/scripts/seed_airbnb.py, parent.parent is backend
backend_dir = Path(__file__).resolve().parent.parent 
sys.path.append(str(backend_dir))
# print(f"Added {backend_dir} to sys.path")

from app.db.client import LanceDBClient
from app.db.schemas import Listing
from app.services.embeddings import EmbeddingService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CSV_PATH = "/Users/henrytran/Downloads/listings.csv"

def parse_price(price_str):
    if not price_str: return 0
    clean = price_str.replace("$", "").replace(",", "")
    try:
        return int(float(clean))
    except:
        return 0

def parse_amenities(amenities_str):
    """
    Amenities in CSV are list-like strings: '["Wifi", "Cable TV", ...]'
    """
    try:
        # Sometimes it's double-quoted JSON string
        return json.loads(amenities_str)
    except:
        return []

def derive_booleans(amenities_list):
    ams = [a.lower() for a in amenities_list]
    return {
        "pets_allowed": any("pet" in a or "dog" in a or "cat" in a for a in ams),
        "parking": any("parking" in a for a in ams),
        "laundry": any("washer" in a or "dryer" in a or "laundry" in a for a in ams),
        "air_conditioning": any("air conditioning" in a or "ac" in a for a in ams),
    }

def clean_score(score_str):
    if not score_str: return 0.0
    try:
        return float(score_str)
    except:
        return 0.0

def seed():
    logger.info("Initializing DB and Embeddings...")
    client = LanceDBClient()
    embedder = EmbeddingService()
    
    # Drop existing table to start fresh with new schema
    try:
        client._db.drop_table(client.TABLE_NAME)
        logger.info("Dropped existing table")
    except:
        pass
        
    # Re-create table
    table = client.get_table() # This will create it with new schema
    
    logger.info(f"Reading CSV from {CSV_PATH}...")
    
    listings_to_insert = []
    
    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            # Filters
            if row['room_type'] != "Entire home/apt":
                continue
            
            # Host location filter - loose match
            if "San Francisco" not in row.get('host_location', ''):
                continue
                
            # Basic data
            amenities = parse_amenities(row.get('amenities', '[]'))
            bools = derive_booleans(amenities)
            
            # Combine text for embedding
            desc = f"{row.get('name', '')}. {row.get('description', '')}. {row.get('neighborhood_overview', '')}"
            # Truncate if too long (rare but safe)
            desc = desc[:2000]
            
            try:
                # Embed (this is the slow part, normally valid to batch, but for simplicity loop is OK for <500 items)
                # Actually, for speed, let's collect texts first then batch embed if list is huge.
                # But here we do row-by-row for simplicity of logic.
                vector = embedder.get_embedding(desc)
                
                listing = Listing(
                    id=row['id'],
                    title=row['name'] or "Untitled Listing",
                    price=parse_price(row['price']),
                    beds=int(float(row.get('bedrooms') or 1)), # default 1 to avoid crash
                    baths=int(float(row.get('bathrooms_text', '1').split(' ')[0] if row.get('bathrooms_text') else 1)), # heuristic
                    sqft=0, # Not reliably in Airbnb CSV
                    city="San Francisco",
                    neighborhood=row.get('neighbourhood_cleansed') or "San Francisco",
                    description=desc,
                    
                    pets_allowed=bools['pets_allowed'],
                    parking=bools['parking'],
                    laundry=bools['laundry'],
                    air_conditioning=bools['air_conditioning'],
                    
                    vibe_score=clean_score(row.get('review_scores_rating', '0')),
                    location_score=clean_score(row.get('review_scores_location', '0')),
                    safety_score=4.0, # Placeholder
                    walkability_score=clean_score(row.get('review_scores_location', '0')), # Proxy
                    
                    amenities=amenities[:10], # Keep top 10 to save space
                    images=[row.get('picture_url', '')],
                    created_at=datetime.now(),
                    
                    vector=vector,
                    external_url=row.get('listing_url', '')
                )
                
                listings_to_insert.append(listing.model_dump())
                
                if len(listings_to_insert) >= 10: # Log progress
                    print(".", end="", flush=True)
                    
            except Exception as e:
                logger.warning(f"Skipping row {row.get('id')}: {e}")
                continue

    logger.info(f"\nInserting {len(listings_to_insert)} listings...")
    if listings_to_insert:
        table.add(listings_to_insert)
        logger.info("Done!")
    else:
        logger.warning("No listings found matching criteria!")

if __name__ == "__main__":
    seed()
