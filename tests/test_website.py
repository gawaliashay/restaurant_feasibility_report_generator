# test_website.py
from src.rag.ingestion.ingestion_pipeline import IngestionPipeline

pipeline = IngestionPipeline()
result = pipeline.ingest_website('https://www.indiafilings.com/learn/maharashtra-shops-and-establishment-act')
print(result)