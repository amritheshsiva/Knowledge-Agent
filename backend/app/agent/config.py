from dotenv import load_dotenv
from decouple import config
load_dotenv()
GROQ_API_KEY=config("GROQ_API_KEY")
GITHUB_TOKEN=config("GITHUB_TOKEN")
GITHUB_OWNER=config("GITHUB_OWNER")
GITHUB_REPO=config("GITHUB_REPO")
MODEL_NAME="meta-llama/llama-4-scout-17b-16e-instruct"
CHROMA_DB_PATH='chroma_db'
