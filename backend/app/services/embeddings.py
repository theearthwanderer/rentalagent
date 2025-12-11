from sentence_transformers import SentenceTransformer
import structlog

logger = structlog.get_logger()

class EmbeddingService:
    _instance = None
    _model = None
    
    MODEL_NAME = "intfloat/e5-large-v2"

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        logger.info(f"Loading embedding model: {self.MODEL_NAME}")
        self._model = SentenceTransformer(self.MODEL_NAME)
        logger.info("Embedding model loaded")

    def get_embedding(self, text: str, is_query: bool = False) -> list[float]:
        # E5 models require specific prefixes
        prefix = "query: " if is_query else "passage: "
        return self._model.encode(prefix + text).tolist()

def get_embedding_service():
    return EmbeddingService.get_instance()
