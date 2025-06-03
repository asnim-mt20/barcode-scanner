from pymongo import MongoClient
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

def get_mongo_collection():
    mongo_uri = os.getenv("MONGO_URI")
    client = MongoClient(mongo_uri)
    print("Connected to MongoDB on GCP VM!")

    db = client["status_updates"]
    print(db)
    collection = db["order_logs"]
    return collection

if __name__ == "__main__":
    collection = get_mongo_collection()
