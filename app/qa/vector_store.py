import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer
from elasticsearch import Elasticsearch
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from typing import List, Dict, Any, Protocol
from abc import ABC, abstractmethod
import json
import uuid
import hashlib
from app.config import settings

class VectorStore(Protocol):
    """Vector store interface"""
    
    @abstractmethod
    def add_chunks(self, chunks: List[str], document_id: int, user_id: int) -> None:
        """Add text chunks to vector store"""
        pass
    
    @abstractmethod
    def search_similar_chunks(self, query: str, user_id: int, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search for similar chunks in vector store"""
        pass
    
    @abstractmethod
    def delete_document_chunks(self, document_id: int, user_id: int) -> None:
        """Delete all chunks for a document"""
        pass
    
    @abstractmethod
    def delete_user_data(self, user_id: int) -> None:
        """Delete all data for a user"""
        pass

class QdrantVectorStore(VectorStore):
    def __init__(self):
        # Initialize Qdrant client
        if settings.qdrant_url:
            self.client = QdrantClient(
                url=settings.qdrant_url,
                api_key=settings.qdrant_api_key,
                timeout=settings.qdrant_timeout
            )
        else:
            # Local mode
            self.client = QdrantClient(
                path=settings.qdrant_persist_directory
            )
        
        self.collection_name = settings.qdrant_collection_name
        self.embedding_model = SentenceTransformer(settings.embedding_model)
        self._create_collection_if_not_exists()
    
    def _generate_uuid_from_string(self, string_id: str) -> str:
        """Generate a deterministic UUID from a string ID"""
        # Create a deterministic UUID using SHA-256 hash
        hash_object = hashlib.sha256(string_id.encode())
        hex_dig = hash_object.hexdigest()
        # Take first 32 characters and format as UUID
        uuid_str = f"{hex_dig[:8]}-{hex_dig[8:12]}-{hex_dig[12:16]}-{hex_dig[16:20]}-{hex_dig[20:32]}"
        return uuid_str
    
    def _create_collection_if_not_exists(self):
        """Create Qdrant collection if it doesn't exist"""
        try:
            # Check if collection exists
            collections = self.client.get_collections()
            collection_names = [col.name for col in collections.collections]
            
            if self.collection_name not in collection_names:
                # Get embedding dimension from the model
                sample_embedding = self.embedding_model.encode(["sample text"])
                vector_size = len(sample_embedding[0])
                
                # Create collection with proper vector configuration
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=vector_size,
                        distance=Distance.COSINE
                    )
                )
                print(f"Created Qdrant collection '{self.collection_name}' with vector size {vector_size}")
        except Exception as e:
            print(f"Error creating Qdrant collection: {e}")
            raise
    
    def add_chunks(self, chunks: List[str], document_id: int, user_id: int) -> None:
        """Add text chunks to Qdrant with user isolation"""
        if not chunks:
            return
        
        # Generate embeddings
        embeddings = self.embedding_model.encode(chunks).tolist()
        
        # Create points for Qdrant
        points = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            # Create a string ID and convert to UUID
            string_id = f"user_{user_id}_doc_{document_id}_chunk_{i}"
            point_uuid = self._generate_uuid_from_string(string_id)
            
            point = PointStruct(
                id=point_uuid,
                vector=embedding,
                payload={
                    "content": chunk,
                    "document_id": document_id,
                    "user_id": user_id,
                    "chunk_index": i,
                    "text_preview": chunk[:200] + "..." if len(chunk) > 200 else chunk,
                    "string_id": string_id  # Keep original string ID for reference
                }
            )
            points.append(point)
        
        # Upload points to Qdrant
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )
    
    def search_similar_chunks(self, query: str, user_id: int, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search for similar chunks in Qdrant (user-isolated)"""
        # Generate query embedding
        query_embedding = self.embedding_model.encode([query]).tolist()[0]
        
        # Create filter for user isolation
        user_filter = Filter(
            must=[
                FieldCondition(
                    key="user_id",
                    match=MatchValue(value=user_id)
                )
            ]
        )
        
        # Search in Qdrant
        search_results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            query_filter=user_filter,
            limit=top_k,
            with_payload=True
        )
        
        # Format results
        chunks = []
        for result in search_results:
            chunks.append({
                'content': result.payload['content'],
                'metadata': {
                    'document_id': result.payload['document_id'],
                    'user_id': result.payload['user_id'],
                    'chunk_index': result.payload['chunk_index'],
                    'text_preview': result.payload['text_preview']
                },
                'score': result.score
            })
        
        return chunks
    
    def delete_document_chunks(self, document_id: int, user_id: int) -> None:
        """Delete all chunks for a document (user-isolated)"""
        # Create filter for document and user
        delete_filter = Filter(
            must=[
                FieldCondition(
                    key="document_id",
                    match=MatchValue(value=document_id)
                ),
                FieldCondition(
                    key="user_id",
                    match=MatchValue(value=user_id)
                )
            ]
        )
        
        # Delete points matching the filter
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=delete_filter
        )
    
    def delete_user_data(self, user_id: int) -> None:
        """Delete all data for a user"""
        # Create filter for user
        user_filter = Filter(
            must=[
                FieldCondition(
                    key="user_id",
                    match=MatchValue(value=user_id)
                )
            ]
        )
        
        # Delete all user's points
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=user_filter
        )

class ChromaVectorStore(VectorStore):
    def __init__(self):
        self.client = chromadb.PersistentClient(
            path=settings.chroma_persist_directory,
            settings=ChromaSettings(anonymized_telemetry=False)
        )
        self.embedding_model = SentenceTransformer(settings.embedding_model)
        self.collection = self.client.get_or_create_collection(
            name="documents",
            metadata={"hnsw:space": "cosine"}
        )
    
    def add_chunks(self, chunks: List[str], document_id: int, user_id: int) -> None:
        """Add text chunks to vector store with user isolation"""
        if not chunks:
            return
        
        # Generate embeddings
        embeddings = self.embedding_model.encode(chunks).tolist()
        
        # Create unique IDs for each chunk with user prefix
        chunk_ids = [f"user_{user_id}_doc_{document_id}_chunk_{i}" for i in range(len(chunks))]
        
        # Create metadata for each chunk
        metadatas = [
            {
                "document_id": document_id,
                "user_id": user_id,
                "chunk_index": i,
                "text_preview": chunk[:200] + "..." if len(chunk) > 200 else chunk
            }
            for i, chunk in enumerate(chunks)
        ]
        
        # Add to collection
        self.collection.add(
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadatas,
            ids=chunk_ids
        )
    
    def search_similar_chunks(self, query: str, user_id: int, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search for similar chunks in vector store (user-isolated)"""
        # Generate query embedding
        query_embedding = self.embedding_model.encode([query]).tolist()[0]
        
        # Search in collection for user's documents only
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where={"user_id": user_id}
        )
        
        # Format results
        chunks = []
        if results['documents'] and results['documents'][0]:
            for i, doc in enumerate(results['documents'][0]):
                chunks.append({
                    'content': doc,
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i] if results['distances'] else None
                })
        
        return chunks
    
    def delete_document_chunks(self, document_id: int, user_id: int) -> None:
        """Delete all chunks for a document (user-isolated)"""
        # FIXED: Use $and operator for multiple conditions in ChromaDB
        results = self.collection.get(
            where={
                "$and": [
                    {"document_id": {"$eq": document_id}},
                    {"user_id": {"$eq": user_id}}
                ]
            }
        )
        
        if results['ids']:
            self.collection.delete(ids=results['ids'])
    
    def delete_user_data(self, user_id: int) -> None:
        """Delete all data for a user"""
        results = self.collection.get(
            where={"user_id": {"$eq": user_id}}
        )
        
        if results['ids']:
            self.collection.delete(ids=results['ids'])

class ElasticsearchVectorStore(VectorStore):
    def __init__(self):
        self.client = Elasticsearch([settings.elasticsearch_url])
        self.index_name = settings.elasticsearch_index
        self.embedding_model = SentenceTransformer(settings.embedding_model)
        self._create_index_if_not_exists()
    
    def _create_index_if_not_exists(self):
        """Create Elasticsearch index with proper mapping"""
        if not self.client.indices.exists(index=self.index_name):
            mapping = {
                "mappings": {
                    "properties": {
                        "content": {"type": "text"},
                        "embedding": {
                            "type": "dense_vector",
                            "dims": 384  # all-MiniLM-L6-v2 embedding dimension
                        },
                        "user_id": {"type": "integer"},
                        "document_id": {"type": "integer"},
                        "chunk_index": {"type": "integer"},
                        "text_preview": {"type": "text"},
                        "created_at": {"type": "date"}
                    }
                }
            }
            self.client.indices.create(index=self.index_name, body=mapping)
    
    def add_chunks(self, chunks: List[str], document_id: int, user_id: int) -> None:
        """Add text chunks to Elasticsearch with user isolation"""
        if not chunks:
            return
        
        # Generate embeddings
        embeddings = self.embedding_model.encode(chunks).tolist()
        
        # Prepare documents for bulk indexing
        docs = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            doc = {
                "_index": self.index_name,
                "_id": f"user_{user_id}_doc_{document_id}_chunk_{i}",
                "_source": {
                    "content": chunk,
                    "embedding": embedding,
                    "user_id": user_id,
                    "document_id": document_id,
                    "chunk_index": i,
                    "text_preview": chunk[:200] + "..." if len(chunk) > 200 else chunk,
                    "created_at": "now"
                }
            }
            docs.append(doc)
        
        # Bulk index
        from elasticsearch.helpers import bulk
        bulk(self.client, docs)
    
    def search_similar_chunks(self, query: str, user_id: int, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search for similar chunks using vector similarity (user-isolated)"""
        # Generate query embedding
        query_embedding = self.embedding_model.encode([query]).tolist()
        
        # Elasticsearch kNN search with user filter
        search_body = {
            "knn": {
                "field": "embedding",
                "query_vector": query_embedding,
                "k": top_k,
                "num_candidates": 100,
                "filter": {
                    "term": {"user_id": user_id}
                }
            },
            "_source": ["content", "document_id", "chunk_index", "text_preview"]
        }
        
        response = self.client.search(index=self.index_name, body=search_body)
        
        # Format results
        chunks = []
        for hit in response['hits']['hits']:
            chunks.append({
                'content': hit['_source']['content'],
                'metadata': {
                    'document_id': hit['_source']['document_id'],
                    'user_id': user_id,
                    'chunk_index': hit['_source']['chunk_index'],
                    'text_preview': hit['_source']['text_preview']
                },
                'score': hit['_score']
            })
        
        return chunks
    
    def delete_document_chunks(self, document_id: int, user_id: int) -> None:
        """Delete all chunks for a document (user-isolated)"""
        query = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {"document_id": document_id}},
                        {"term": {"user_id": user_id}}
                    ]
                }
            }
        }
        
        self.client.delete_by_query(index=self.index_name, body=query)
    
    def delete_user_data(self, user_id: int) -> None:
        """Delete all data for a user"""
        query = {
            "query": {
                "term": {"user_id": user_id}
            }
        }
        
        self.client.delete_by_query(index=self.index_name, body=query)

def get_vector_store() -> VectorStore:
    """Factory function to get the configured vector store"""
    if settings.vector_db_type == "qdrant":
        return QdrantVectorStore()
    elif settings.vector_db_type == "elasticsearch":
        return ElasticsearchVectorStore()
    else:
        return ChromaVectorStore()

# Global vector store instance
vector_store = get_vector_store()
