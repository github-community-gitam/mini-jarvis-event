import os
from dotenv import load_dotenv
import requests

load_dotenv()
api_key = os.getenv('GROQ_API_KEY')
response = requests.get('https://api.groq.com/openai/v1/models', headers={'Authorization': f'Bearer {api_key}'})
print(response.json())
