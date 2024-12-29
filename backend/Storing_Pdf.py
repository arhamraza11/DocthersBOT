import fitz  # PyMuPDF
from qdrant_client import QdrantClient
from qdrant_client.http import models
from sentence_transformers import SentenceTransformer
import base64
import uuid
import logging
import os
# Initialize logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Qdrant client and SentenceTransformer
QDRANT_API_URL = os.getenv("QDRANT_API_URL")# Replace with your actual Qdrant cluster URL
API_KEY = os.getenv("QDRANT_API_KEY")  # Replace with your Qdrant API key # Replace with your Qdrant API key
qdrant_client = QdrantClient(
    url=QDRANT_API_URL,
    api_key=API_KEY
)
model = SentenceTransformer('all-MiniLM-L6-v2')

# Define the vector size based on the SentenceTransformer model
vector_size = model.get_sentence_embedding_dimension()

def create_qdrant_collection(collection_name, vector_size):
    """
    Create a collection in Qdrant.
    """
    try:
        qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=vector_size,
                distance=models.Distance.DOT
            )
        )
        logger.info(f"Collection '{collection_name}' created successfully.")
    except Exception as e:
        logger.warning(f"Collection creation failed or already exists: {e}")

def store_text_in_qdrant(text, collection_name):
    """
    Store text and its embedding in Qdrant.
    """
    text_embedding = model.encode(text).tolist()
    text_id = str(uuid.uuid4())
    try:
        qdrant_client.upsert(
            collection_name=collection_name,
            points=[
                models.PointStruct(
                    id=text_id,
                    vector=text_embedding,
                    payload={"page_text": text}
                )
            ]
        )
        logger.info(f"Text with ID {text_id} stored successfully.")
    except Exception as e:
        logger.error(f"Failed to upsert text data: {e}")

def process_pdf(pdf_path, collection_name):
    """
    Process a PDF, extract text from each page, and store it in Qdrant.
    """
    doc = fitz.open(pdf_path)
    points = []

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text = page.get_text()
        
        if text.strip():  # Skip empty pages
            text_embedding = model.encode(text).tolist()
            text_id = str(uuid.uuid4())
            points.append(models.PointStruct(
                id=text_id,
                vector=text_embedding,
                payload={"page_text": text, "page_number": page_num + 1}
            ))
            logger.info(f"Processed page {page_num + 1} of {pdf_path}.")
        else:
            logger.warning(f"No text found on page {page_num + 1} of {pdf_path}. Skipping...")

    # Batch upload points to Qdrant
    try:
        qdrant_client.upsert(collection_name=collection_name, points=points)
        logger.info(f"Processed and stored {len(points)} pages from {pdf_path}.")
    except Exception as e:
        logger.error(f"Failed to upsert batched text data: {e}")

# Main workflow
if __name__ == "__main__":
    # Collection name
    collection_name = "medical_documents"
    
    # Create Qdrant collection
    create_qdrant_collection(collection_name, vector_size)

    # Process PDFs
    pdf_path = 'medical_document.pdf'

    
    process_pdf(pdf_path, collection_name)
