"""
Document Processing for RAG System

WHY THIS MODULE:
- Loads banking documents (Word, PDF, TXT)
- Splits into chunks (optimal size for retrieval)
- Prepares documents for embedding

LEARNING POINTS:
- Document loaders for different formats
- Text chunking strategies
- Metadata enrichment
- Why chunk size matters for RAG
"""

import logging
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass
import langchain

# Document loaders from LangChain
from langchain_community.document_loaders import (
    Docx2txtLoader,
    PyPDFLoader,
    TextLoader
)
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document

logger = logging.getLogger(__name__)


@dataclass
class ProcessingStats:
    """Statistics from document processing"""
    total_documents: int = 0
    total_chunks: int = 0
    avg_chunk_size: float = 0.0
    document_types: Dict[str, int] = None
    
    def __post_init__(self):
        if self.document_types is None:
            self.document_types = {}


class DocumentProcessor:
    """
    Processes documents for RAG system
    
    WHY CHUNKING:
    - LLMs have token limits (can't send entire document)
    - Smaller chunks = more precise retrieval
    - Better to retrieve "Premium Savings: 3.2% APY" than entire 10-page policy
    
    CHUNK SIZE CONSIDERATIONS:
    - Too small (100 chars): Loses context ("3.2% APY" - for what?)
    - Too large (5000 chars): Wastes tokens, less precise
    - Sweet spot: 1000-1500 chars with 200 char overlap
    """
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ):
        """
        Initialize document processor
        
        Args:
            chunk_size: Target size of each chunk in characters
            chunk_overlap: Overlap between chunks (preserves context at boundaries)
        
        WHY OVERLAP:
        - Prevents splitting mid-sentence or mid-concept
        - Example without overlap:
          Chunk1: "Premium Savings offers 3.2%"
          Chunk2: "APY on balances over $10,000"
        - Example with overlap:
          Chunk1: "Premium Savings offers 3.2% APY on balances"
          Chunk2: "3.2% APY on balances over $10,000"
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Create text splitter with smart splitting rules
        # WHY RecursiveCharacterTextSplitter:
        # - Tries to split on paragraphs first
        # - Falls back to sentences
        # - Then words
        # - Preserves semantic meaning
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=[
                "\n\n",  # Paragraphs (preferred)
                "\n",    # Lines
                ". ",    # Sentences
                " ",     # Words
                ""       # Characters (last resort)
            ]
        )
        
        logger.info(f"DocumentProcessor initialized (chunk_size={chunk_size}, overlap={chunk_overlap})")
    
    def load_document(self, file_path: Path) -> List[Document]:
        """
        Load a single document
        
        Args:
            file_path: Path to document file
            
        Returns:
            List of LangChain Document objects
            
        WHY LANGCHAIN DOCUMENTS:
        - Standard format across LangChain ecosystem
        - Contains page_content (text) and metadata
        - Easy to pass to embeddings and vector stores
        """
        extension = file_path.suffix.lower()
        
        try:
            # Choose loader based on file type
            if extension == '.docx':
                loader = Docx2txtLoader(str(file_path))
            elif extension == '.pdf':
                loader = PyPDFLoader(str(file_path))
            elif extension == '.txt':
                loader = TextLoader(str(file_path), encoding='utf-8')
            else:
                logger.warning(f"Unsupported file type: {extension}")
                return []
            
            documents = loader.load()
            logger.info(f"Loaded {len(documents)} page(s) from {file_path.name}")
            
            return documents
            
        except Exception as e:
            logger.error(f"Error loading {file_path.name}: {str(e)}")
            return []
    
    def chunk_documents(self, documents: List[Document]) -> List[Document]:
        """
        Split documents into chunks
        
        Args:
            documents: List of loaded documents
            
        Returns:
            List of chunked documents
        """
        chunks = self.text_splitter.split_documents(documents)
        logger.info(f"Split {len(documents)} documents into {len(chunks)} chunks")
        
        return chunks
    
    def enrich_metadata(
        self,
        chunks: List[Document],
        source_file: Path
    ) -> List[Document]:
        """
        Add useful metadata to chunks
        
        WHY METADATA:
        - Track source document
        - Filter results (only show fee-related chunks for fee questions)
        - Debugging and logging
        - Citation in responses
        
        Args:
            chunks: Document chunks
            source_file: Original file path
            
        Returns:
            Chunks with enriched metadata
        """
        doc_type = self._infer_document_type(source_file.name)
        
        for i, chunk in enumerate(chunks):
            chunk.metadata.update({
                'source': str(source_file),
                'filename': source_file.name,
                'doc_type': doc_type,
                'chunk_index': i,
                'total_chunks': len(chunks),
                'chunk_size': len(chunk.page_content)
            })
        
        return chunks
    
    def _infer_document_type(self, filename: str) -> str:
        """
        Infer document category from filename
        
        WHY:
        - Enables filtering (only search fee docs for fee questions)
        - Better retrieval precision
        - Can weight certain doc types higher
        """
        filename_lower = filename.lower()
        
        if 'account' in filename_lower or 'product' in filename_lower:
            return 'account_info'
        elif 'fee' in filename_lower or 'charge' in filename_lower:
            return 'fees'
        elif 'loan' in filename_lower or 'mortgage' in filename_lower:
            return 'loans'
        elif 'security' in filename_lower or 'fraud' in filename_lower:
            return 'security'
        elif 'service' in filename_lower or 'support' in filename_lower:
            return 'customer_service'
        else:
            return 'general'
    
    def process_directory(
        self,
        directory: Path
    ) -> tuple[List[Document], ProcessingStats]:
        """
        Process all documents in a directory
        
        Args:
            directory: Path to directory containing documents
            
        Returns:
            Tuple of (processed chunks, statistics)
        """
        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")
        
        all_chunks = []
        stats = ProcessingStats()
        
        # Find all supported files
        supported_extensions = ['.docx', '.pdf', '.txt']
        files = []
        for ext in supported_extensions:
            files.extend(directory.glob(f'*{ext}'))
        
        logger.info(f"Found {len(files)} documents to process")
        
        # Process each file
        for file_path in files:
            try:
                # Load document
                documents = self.load_document(file_path)
                if not documents:
                    continue
                
                # Chunk
                chunks = self.chunk_documents(documents)
                
                # Enrich metadata
                chunks = self.enrich_metadata(chunks, file_path)
                
                all_chunks.extend(chunks)
                
                # Update stats
                stats.total_documents += 1
                stats.total_chunks += len(chunks)
                doc_type = chunks[0].metadata['doc_type']
                stats.document_types[doc_type] = stats.document_types.get(doc_type, 0) + 1
                
                logger.info(f"✅ Processed {file_path.name}: {len(chunks)} chunks")
                
            except Exception as e:
                logger.error(f"❌ Failed to process {file_path.name}: {str(e)}")
                continue
        
        # Calculate average chunk size
        if all_chunks:
            stats.avg_chunk_size = sum(
                len(chunk.page_content) for chunk in all_chunks
            ) / len(all_chunks)
        
        logger.info(f"Processing complete: {stats.total_chunks} total chunks from {stats.total_documents} documents")
        
        return all_chunks, stats


# Convenience function
def process_banking_documents(docs_dir: str = "data/sample_banking_docs") -> tuple[List[Document], ProcessingStats]:
    """
    Process banking documents from default directory
    
    Returns:
        Tuple of (chunks, statistics)
        
    Example:
        chunks, stats = process_banking_documents()
        print(f"Created {stats.total_chunks} chunks")
    """
    processor = DocumentProcessor()
    return processor.process_directory(Path(docs_dir))


# Test code
if __name__ == "__main__":
    print("\n" + "="*70)
    print("📄 Document Processor Test")
    print("="*70 + "\n")
    
    # Process documents
    print("Processing banking documents...")
    chunks, stats = process_banking_documents()
    
    # Show statistics
    print("\n📊 Processing Statistics:")
    print("-" * 70)
    print(f"Total Documents: {stats.total_documents}")
    print(f"Total Chunks: {stats.total_chunks}")
    print(f"Average Chunk Size: {stats.avg_chunk_size:.0f} characters")
    
    print("\nDocuments by Type:")
    for doc_type, count in stats.document_types.items():
        print(f"  • {doc_type}: {count} document(s)")
    
    # Show sample chunks
    print("\n📝 Sample Chunks:")
    print("-" * 70)
    
    for i, chunk in enumerate(chunks[:3], 1):
        print(f"\nChunk {i}:")
        print(f"Source: {chunk.metadata['filename']}")
        print(f"Type: {chunk.metadata['doc_type']}")
        print(f"Size: {chunk.metadata['chunk_size']} characters")
        print(f"Content Preview:")
        preview = chunk.page_content[:200]
        print(f"  {preview}...")
    
    print("\n" + "="*70)
    print(f"✅ Successfully processed {stats.total_chunks} chunks!")
    print("="*70 + "\n")