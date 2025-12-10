import sys
import os
from datetime import datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.client import get_lancedb_client
from app.services.embeddings import get_embedding_service
from app.db.schemas import Listing
import structlog

logger = structlog.get_logger()

DUMMY_LISTINGS = [
    {
        "id": "listing_001",
        "title": "Modern 1BD in SoMa",
        "price": 3200,
        "beds": 1.0,
        "baths": 1.0,
        "city": "San Francisco",
        "neighborhood": "SoMa",
        "amenities": ["Gym", "Roof Deck", "In-unit W/D"],
        "external_url": "https://example.com/listing1",
        "description": "Stunning modern 1 bedroom apartment in the heart of SoMa. Features high ceilings, large windows, and a chef's kitchen. Building usually includes gym and roof deck."
    },
    {
        "id": "listing_002",
        "title": "Spacious Loft near Caltrain",
        "price": 4500,
        "beds": 2.0,
        "baths": 2.0,
        "city": "San Francisco",
        "neighborhood": "SoMa",
        "amenities": ["Parking", "Concierge"],
        "external_url": "https://example.com/listing2",
        "description": "Huge industrial loft conversion with 2 bedrooms and 2 bathrooms. Walking distance to Caltrain and Oracle Park. Concrete floors and exposed brick."
    },
    {
        "id": "listing_003",
        "title": "Luxury Highrise Studio",
        "price": 2800,
        "beds": 0.0,
        "baths": 1.0,
        "city": "San Francisco",
        "neighborhood": "SoMa",
        "amenities": ["Pool", "Gym", "Doorman"],
        "external_url": "https://example.com/listing3",
        "description": "Cozy but luxurious studio in a premier highrise. Access to pool, gym, and 24/7 doorman. Great views of the city."
    },
     {
        "id": "listing_004",
        "title": "Cozy Garden Apartment",
        "price": 2500,
        "beds": 1.0,
        "baths": 1.0,
        "city": "Oakland",
        "neighborhood": "Adams Point",
        "amenities": ["Garden", "Pets Allowed"],
        "external_url": "https://example.com/listing4",
        "description": "Lovely garden unit in a quiet fourplex. Hardwood floors and shared backyard. Pet friendly."
    }
]

def seed_data():
    logger.info("Starting seed process...")
    
    # Initialize services
    client = get_lancedb_client()
    embedding_service = get_embedding_service()
    
    # Drop existing table to ensure schema update
    try:
        client._db.drop_table(client.TABLE_NAME)
        logger.info("Dropped existing table")
    except Exception as e:
        logger.info(f"Top drop skipped/failed: {e}")

    table = client.get_table()
    
    # Prepare data
    data_to_insert = []
    ids = []
    
    for item in DUMMY_LISTINGS:
        logger.info(f"Processing listing: {item['title']}")
        
        # Embed description
        vector = embedding_service.get_embedding(item["description"])
        
        listing = Listing(
            **item,
            vector=vector,
            last_embedded_at=datetime.now()
        )
        data_to_insert.append(listing.model_dump())
        ids.append(item["id"])

    # Overwrite mode: delete existing if IDs match or just add?
    # LanceDB doesn't strictly enforce primary key uniqueness on add easily without merge.
    # For seed, easier to drop/recreate or just append. 
    # Since `get_table` implementation in client creates if not exists, 
    # we might want to drop only if we are hard resetting.
    # For now, let's just add components.
    
    logger.info(f"Inserting {len(data_to_insert)} listings...")
    table.add(data_to_insert)
    logger.info("Seed complete!")

if __name__ == "__main__":
    seed_data()
