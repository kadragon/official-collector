import hashlib
from src.ai import AIManager
from pinecone.grpc import PineconeGRPC as Pinecone

class PineconeManager:
    def __init__(self, api_key, index_name = "official-collect-info"):
        self.pinecone = Pinecone(api_key=api_key)
        self.index = self.pinecone.Index(name=index_name)
        self.ai_manager = AIManager()

    @staticmethod
    def generate_id(title):
        return hashlib.sha256(title.encode('utf-8')).hexdigest()
    
    def upsert_data(self, text, classification, viewing, vector):
        vector_id = self.generate_id(text)
        embedding = vector
        
        self.index.upsert(
            vectors=[{
                "id": vector_id,
                "metadata": {"title": text, "classification": classification, "viewing": viewing},
                "values": embedding
            }]
        )
        print(f"Complete: {text} / {classification} / {viewing}")

    def query(self, embedding):
        response = self.index.query(
            vector=embedding,
            top_k=10,
            include_metadata=True
        )
        return response