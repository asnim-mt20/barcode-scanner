from pymongo import MongoClient

def get_mongo_collection():
    client = MongoClient("mongodb://localhost:27017/")
    print("Connected to MongoDB!")

    db = client["status_updates"] #create db
    print(db)
    collection = db["order_logs"] #necessary to create collection when creating a database
    return collection

#To include code that should execute only when the script is run directly not as an import module
if __name__ == "__main__":
    collection = get_mongo_collection()