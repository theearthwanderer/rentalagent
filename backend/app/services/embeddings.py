from sentence_transformers import SentenceTransformer
import structlog

logger = structlog.get_logger()

class EmbeddingService:
    _instance = None
    _model = None
    
    MODEL_NAME = "sentence-transformers/all-mpnet-base-v2"

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        logger.info(f"Loading embedding model: {self.MODEL_NAME}")
        self._model = SentenceTransformer(self.MODEL_NAME)
        logger.info("Embedding model loaded")

    def get_embedding(self, text: str) -> list[float]:
        return self._model.encode(text).tolist()

def get_embedding_service():
    return EmbeddingService.get_instance()
