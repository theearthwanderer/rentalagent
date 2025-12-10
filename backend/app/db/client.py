import lancedb
from lancedb.pydantic import pydantic_to_schema
from app.core.config import settings
from app.db.schemas import Listing

class LanceDBClient:
    _instance = None
    _db = None
    _table = None

    TABLE_NAME = "listings"

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._db = lancedb.connect(settings.LANCEDB_URI)
        
    def get_table(self):
        if self.TABLE_NAME in self._db.table_names():
            return self._db.open_table(self.TABLE_NAME)
        
        # Create table if not exists
        # Schema is derived from Pydantic model
        # Note: We need a dummy embedding size or properly define schema for LanceDB
        # For now, we assume strict schema provided by pydantic_to_schema
        # But lancedb.pydantic support is limited in synchronous client? 
        # Actually pydantic_to_schema works.
        schema = pydantic_to_schema(Listing)
        return self._db.create_table(
            self.TABLE_NAME, 
            schema=schema,
            exist_ok=True
        )

def get_lancedb_client():
    return LanceDBClient.get_instance()
