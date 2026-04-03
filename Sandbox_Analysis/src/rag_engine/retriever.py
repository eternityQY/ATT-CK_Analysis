import logging
from typing import List, Dict
from src.kb_builder.indexer import Indexer

logger = logging.getLogger(__name__)

class KnowledgeRetriever:
    """
    Knowledge Retriever based on FAISS Vector Database
    """

    def __init__(self, vector_db_dir: str):
        """
        Initialize retriever and load local index
        """
        self.vector_db_dir = vector_db_dir
        self.vector_store = None
        
        try:
            # Reuse Indexer class from kb_builder to load index
            indexer = Indexer()
            self.vector_store = indexer.load_local()
            logger.info(f"Knowledge Retriever initialized from {vector_db_dir}")
        except Exception as e:
            logger.error(f"Failed to load Vector DB: {e}")
            raise RuntimeError("Vector DB not loaded. Please run 'python tools/build_kb.py' first.")

    def retrieve(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Retrieve Top-K relevant documents based on query
        
        Args:
            query: Query string (Natural Language)
            top_k: Number of results to return
            
        Returns:
            List[Dict]: List containing content, source, type, metadata
        """
        if not self.vector_store:
            logger.warning("Vector store is not initialized.")
            return []

        try:
            # Perform similarity search
            docs = self.vector_store.similarity_search(query, k=top_k)
            
            results = []
            for doc in docs:
                results.append({
                    "content": doc.page_content,
                    "source": doc.metadata.get("source", "Unknown"),
                    "type": doc.metadata.get("type", "Unknown"),
                    "metadata": doc.metadata
                })
            
            logger.info(f"Retrieved {len(results)} documents for query: {query[:50]}...")
            return results

        except Exception as e:
            logger.error(f"Error during retrieval: {e}")
            return []