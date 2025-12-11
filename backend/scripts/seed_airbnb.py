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

import re # Added import

CSV_PATH = "/Users/henrytran/Downloads/listings.csv"

def clean_text(text):
    if not text: return ""
    # Remove HTML tags
    clean = re.sub(r'<.*?>', '', text)
    # Remove multiple spaces/newlines
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean

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
        
        for i, row in enumerate(reader):
            # Filters
            if row['room_type'] != "Entire home/apt":
                continue
            
            # Host location filter - loose match
            if "San Francisco" not in row.get('host_location', ''):
                continue
                
            # Basic data
            amenities_list = parse_amenities(row.get('amenities', '[]'))
            bools = derive_booleans(amenities_list)
            
            # Helper to clean text
            raw_desc = f"{row.get('name', '')}. {row.get('description', '')}. {row.get('neighborhood_overview', '')}"
            cleaned_desc = clean_text(raw_desc)
            cleaned_desc = cleaned_desc[:2000]
            
            try:
                # Combined text for embedding (Passage)
                text_to_embed = f"{row.get('name')} {cleaned_desc}"
                
                # Generate Vector (is_query=False for passages)
                vector = embedder.get_embedding(text_to_embed, is_query=False)
                
                listing = Listing(
                    id=row['id'],
                    title=row['name'] or "Untitled Listing",
                    price=parse_price(row['price']),
                    beds=int(float(row.get('bedrooms') or 1)), # default 1 to avoid crash
                    baths=int(float(row.get('bathrooms_text', '1').split(' ')[0] if row.get('bathrooms_text') else 1)), # heuristic
                    sqft=0, # Not reliably in Airbnb CSV
                    city="San Francisco",
                    neighborhood=row.get('neighbourhood_cleansed') or "San Francisco",
                    description=cleaned_desc, # Store cleaned description
                    
                    pets_allowed=bools['pets_allowed'],
                    parking=bools['parking'],
                    laundry=bools['laundry'],
                    air_conditioning=bools['air_conditioning'],
                    
                    vibe_score=clean_score(row.get('review_scores_rating', '0')),
                    location_score=clean_score(row.get('review_scores_location', '0')),
                    safety_score=4.0, # Placeholder
                    walkability_score=clean_score(row.get('review_scores_location', '0')), # Proxy
                    
                    amenities=amenities_list[:10], # Keep top 10 to save space
                    images=[row.get('picture_url', '')],
                    created_at=datetime.now(),
                    
                    vector=vector,
                    external_url=row.get('listing_url', '')
                )
                
                listings_to_insert.append(listing.model_dump())
                
                if i % 100 == 0: # Log progress
                    logger.info(f"Processed {i} listings for embedding...")
                    
            except Exception as e:
                logger.warning(f"Skipping row {row.get('id')}: {e}")
                continue

    # 3. Create Table (OVERWRITE to clean up old indices/schema)
    if listings_to_insert:
        logger.info(f"Inserting {len(listings_to_insert)} listings into '{client.TABLE_NAME}' table (OVERWRITE mode)...")
        # Use client._db.create_table with mode='overwrite'
        table = client._db.create_table(client.TABLE_NAME, listings_to_insert, mode="overwrite")
        logger.info("Table created/overwritten.")
        logger.info("Done!")
    else:
        logger.warning("No listings found matching criteria!")

if __name__ == "__main__":
    seed()
