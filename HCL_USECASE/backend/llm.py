from dotenv import load_dotenv
from langchain_groq import ChatGroq
import os

load_dotenv()

def get_llm():
    """Get the llm model"""
    
    api_key = os.getenv("GROQ_API_KEY")
    
    if not api_key:
        raise ValueError("No api key found")
    
    llm = ChatGroq(
        model="qwen/qwen3.8-27b",  # free + very capable
        temperature=0,
        api_key=api_key
    )
    print("LLM intialized")
    
    return llm

