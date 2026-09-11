from dotenv import load_dotenv
load_dotenv()

from app.services.vector_service import get_index

if __name__ == "__main__":
    index = get_index()
    print(index.describe_index_stats())
