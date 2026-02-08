import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.environ["UPSTAGE_API_KEY"],
    base_url="https://api.upstage.ai/v1",
)
