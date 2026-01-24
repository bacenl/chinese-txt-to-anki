"""API module for DeepSeek API interactions."""

import os

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

PROMPT_PATH = os.getenv("PROMPT_PATH")

def load_prompt_template() -> str:
    """Load the prompt template from prompt.txt file.
    
    Returns:
        Prompt template string.
        
    Raises:
        FileNotFoundError: If prompt.txt doesn't exist.
        
    Example:
        >>> template = load_prompt_template()
        >>> print(len(template))
    """
    if not os.path.exists(PROMPT_PATH):
        raise FileNotFoundError(
            f"Error: {PROMPT_PATH} not found. Please create this file with your prompt template."
        )
    
    with open(PROMPT_PATH, "r", encoding="utf-8") as f:
        return f.read()


def create_prompt(words: list[str]) -> str:
    """Create a formatted prompt for DeepSeek API.
    
    Args:
        words: List of Chinese words to analyze.
        
    Returns:
        Formatted prompt string for the API.
        
    Example:
        >>> prompt = create_prompt(["你好", "谢谢"])
        >>> print(len(prompt))
    """
    template = load_prompt_template()
    words_text = "\n".join(words)
    
    # Replace placeholder in template with actual words
    prompt = template.replace("{words}", words_text)
    
    return prompt


def call_deepseek_api(prompt: str, api_key: str) -> str:
    """Call DeepSeek API with the given prompt.
    
    Args:
        prompt: The prompt to send to the API.
        api_key: DeepSeek API key.
        
    Returns:
        API response content as string.
        
    Raises:
        Exception: If API call fails.
        
    Example:
        >>> response = call_deepseek_api("Explain 你好", "your-api-key")
        >>> print(response[:100])
    """
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "user", "content": prompt},
        ],
        stream=False,
    )

    return response.choices[0].message.content
