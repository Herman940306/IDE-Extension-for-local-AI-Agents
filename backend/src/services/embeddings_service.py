"""
Code embeddings service using Sentence Transformers
Project Creator: Herman Swanepoel
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional
from pathlib import Path
import hashlib
import json

from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)


class EmbeddingsService:
    """
    Service for generating and managing code embeddings
    Uses CodeBERT for semantic code understanding
    """

    def __init__(
        self,
        model_name: str = "microsoft/codebert-base",
        chroma_persist_dir: str = "./data/chroma",
        collection_name: str = "code_embeddings"
    ):
        """
        Initialize embeddings service
        
        Args:
            model_name: Sentence transformer model to use
            chroma_persist_dir: Directory for ChromaDB persistence
            chroma_persist_dir: Directory for ChromaDB persistence
            collection_name: Name of the ChromaDB collection
        """
        self.model_name = model_name
        self.chroma_persist_dir = chroma_persist_dir
        self.collection_name = collection_name
        self.model: Optional[SentenceTransformer] = None
        self.chroma_client: Optional[chromadb.Client] = None
        self.collection: Optional[Any] = None
        self.is_initialized = False

    async def initialize(self) -> None:
        """Initialize the embeddings model and vector store"""
        try:
            logger.info(f"Loading embeddings model: {self.model_name}")
            
            # Load model in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            self.model = await loop.run_in_executor(
                None,
                lambda: SentenceTransformer(self.model_name)
            )
            
            # Initialize ChromaDB
            self.chroma_client = chromadb.Client(Settings(
                persist_directory=self.chroma_persist_dir,
                anonymized_telemetry=False
            ))
            
            # Get or create collection
            self.collection = self.chroma_client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "Code embeddings for semantic search"}
            )
            
            self.is_initialized = True
            logger.info("✓ Embeddings service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize embeddings service: {e}")
            raise

    async def embed_code(self, code: str, metadata: Optional[Dict[str, Any]] = None) -> List[float]:
        """
        Generate embedding for code snippet
        
        Args:
            code: Code to embed
            metadata: Optional metadata
            
        Returns:
            Embedding vector
        """
        if not self.is_initialized or not self.model:
            raise RuntimeError("Embeddings service not initialized")

        try:
            # Generate embedding in thread pool
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(
                None,
                lambda: self.model.encode(code, convert_to_numpy=True)
            )
            
            return embedding.tolist()
            
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise

    async def embed_codebase(
        self,
        workspace_path: str,
        file_extensions: List[str] = [".py", ".ts", ".js", ".tsx", ".jsx"]
    ) -> int:
        """
        Generate embeddings for entire codebase
        
        Args:
            workspace_path: Path to workspace
            file_extensions: File extensions to process
            
        Returns:
            Number of files processed
        """
        if not self.is_initialized:
            raise RuntimeError("Embeddings service not initialized")

        workspace = Path(workspace_path)
        if not workspace.exists():
            raise ValueError(f"Workspace path does not exist: {workspace_path}")

        files_processed = 0
        
        try:
            # Find all code files
            code_files = []
            for ext in file_extensions:
                code_files.extend(workspace.rglob(f"*{ext}"))

            logger.info(f"Found {len(code_files)} code files to process")

            # Process files in batches
            batch_size = 10
            for i in range(0, len(code_files), batch_size):
                batch = code_files[i:i + batch_size]
                await self._process_file_batch(batch)
                files_processed += len(batch)
                
                if files_processed % 50 == 0:
                    logger.info(f"Processed {files_processed}/{len(code_files)} files")

            logger.info(f"✓ Codebase embedding complete: {files_processed} files")
            return files_processed
            
        except Exception as e:
            logger.error(f"Failed to embed codebase: {e}")
            raise

    async def _process_file_batch(self, files: List[Path]) -> None:
        """Process a batch of files"""
        for file_path in files:
            try:
                # Read file content
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                
                # Generate file ID
                file_id = self._generate_file_id(str(file_path))
                
                # Generate embedding
                embedding = await self.embed_code(content)
                
                # Store in ChromaDB
                self.collection.upsert(
                    ids=[file_id],
                    embeddings=[embedding],
                    documents=[content],
                    metadatas=[{
                        "file_path": str(file_path),
                        "file_name": file_path.name,
                        "extension": file_path.suffix,
                        "size": len(content)
                    }]
                )
                
            except Exception as e:
                logger.warning(f"Failed to process {file_path}: {e}")

    async def find_similar_code(
        self,
        query: str,
        top_k: int = 5,
        file_extension: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Find similar code using semantic search
        
        Args:
            query: Search query
            top_k: Number of results to return
            file_extension: Filter by file extension
            
        Returns:
            List of similar code snippets with metadata
        """
        if not self.is_initialized:
            raise RuntimeError("Embeddings service not initialized")

        try:
            # Generate query embedding
            query_embedding = await self.embed_code(query)
            
            # Build where clause for filtering
            where = None
            if file_extension:
                where = {"extension": file_extension}

            # Search in ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where
            )

            # Format results
            similar_code = []
            if results and results['documents']:
                for i in range(len(results['documents'][0])):
                    similar_code.append({
                        "code": results['documents'][0][i],
                        "metadata": results['metadatas'][0][i],
                        "distance": results['distances'][0][i] if 'distances' in results else None
                    })

            return similar_code
            
        except Exception as e:
            logger.error(f"Failed to search similar code: {e}")
            raise

    async def update_file_embedding(self, file_path: str, content: str) -> None:
        """
        Update embedding for a single file (incremental update)
        
        Args:
            file_path: Path to file
            content: File content
        """
        if not self.is_initialized:
            raise RuntimeError("Embeddings service not initialized")

        try:
            file_id = self._generate_file_id(file_path)
            embedding = await self.embed_code(content)
            
            path_obj = Path(file_path)
            self.collection.upsert(
                ids=[file_id],
                embeddings=[embedding],
                documents=[content],
                metadatas=[{
                    "file_path": file_path,
                    "file_name": path_obj.name,
                    "extension": path_obj.suffix,
                    "size": len(content)
                }]
            )
            
            logger.debug(f"Updated embedding for {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to update file embedding: {e}")
            raise

    async def delete_file_embedding(self, file_path: str) -> None:
        """
        Delete embedding for a file
        
        Args:
            file_path: Path to file
        """
        if not self.is_initialized:
            raise RuntimeError("Embeddings service not initialized")

        try:
            file_id = self._generate_file_id(file_path)
            self.collection.delete(ids=[file_id])
            logger.debug(f"Deleted embedding for {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to delete file embedding: {e}")
            raise

    def _generate_file_id(self, file_path: str) -> str:
        """Generate unique ID for file"""
        return hashlib.md5(file_path.encode()).hexdigest()

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about embeddings
        
        Returns:
            Statistics dictionary
        """
        if not self.is_initialized or not self.collection:
            return {"initialized": False}

        try:
            count = self.collection.count()
            return {
                "initialized": True,
                "model": self.model_name,
                "collection": self.collection_name,
                "total_embeddings": count,
                "persist_directory": self.chroma_persist_dir
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {"initialized": True, "error": str(e)}
