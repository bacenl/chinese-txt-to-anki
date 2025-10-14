import argparse
from dotenv import load_dotenv
import os
import sys
import requests
from pathlib import Path
from openai import OpenAI
import subprocess
import json

load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
TXT_PATH = os.getenv("TXT_PATH")
MD_PATH = os.getenv("MD_PATH")
ANKI_PATH = os.getenv("ANKI_PATH")

def parse_arguments():
    parser = argparse.ArgumentParser(description='Generate Anki cards from Chinese words')
    parser.add_argument(
        '--no-api', 
        '-na',
        action='store_true',
        help='Skip DeepSeek API call (use existing markdown file)'
    )
    parser.add_argument(
        '--input', 
        '-i',
        default=TXT_PATH,
        help=f'Input file with Chinese words (default: { TXT_PATH })'
    )
    parser.add_argument(
        '--output', 
        '-o',
        default=ANKI_PATH,
        help=f'Output Anki package name (default: { ANKI_PATH })'
    )
    parser.add_argument(
        '--markdown',
        '-md',
        default=MD_PATH, 
        help=f'Markdown file to use/generate (default: { MD_PATH })'
    )

    return parser.parse_args()
    
def read_txt_file(input_path=TXT_PATH):
    with open(input_path, "r", encoding="utf-8") as file:
        words = [line.strip() for line in file if line.strip()]
    return words

def create_prompt(words):
    words_text = "\n".join(words)
    prompt = f"""I want to understand the following Chinese word(s) in deep, cultural, and practical context:

{words_text}

Please analyze each word using the following structured framework:

    0. **Word**
    *   Provide the word
    *   Provide the pinyin (on a separate line)
    *   State the word type (noun, verb, adjectival verb, adjective, adverb, etc.)
    *   Prepend with ## 

1.  **Core Meaning & Character Breakdown:**
    *   Provide the pinyin and core English translation(s).
    *   Deconstruct the character(s) etymologically and visually. Explain the radicals and components and what they contribute to the overall meaning.

2.  **Key Dimensions & Nuances:**
    *   Go beyond the dictionary definition. Explain the word's philosophical, emotional, or social connotations.
    *   If applicable, mention its origin (e.g., Classical Chinese, Buddhist influence, modern slang).

3.  **Usage in Everyday Life:**
    *   Provide common words, phrases, or idioms that use this character.
    *   Give a short, practical example sentence for each, with pinyin and English translation.
    *   Explain the context or feeling these phrases evoke.

4.  **A Guiding Philosophy:**
    *   Summarize the core concept behind the word. How can one use this concept as a lens for viewing life, relationships, or society? Offer an analogy if helpful.

Analyze each word on the list individually and thoroughly.
ONLY RESPOND WITH THE ANSWERS TO THE QUERY. DO NOT PROVIDE ANY OTHER STATEMENTS.

Example
## 混账 

(hùnzhàng)
Noun

**1. Core Meaning & Character Breakdown:**
- **Translation:** Scoundrel; bastard; son of a bitch (a severe insult).
- **Breakdown:**
    - **混 (hùn):** 'To mix,' 'to confuse,' 'muddled.' Carries a sense of being irresponsible, muddle-headed, or just getting by (e.g., 混日子, to idle away one's life).
    - **账 (zhàng):** 'Account,' 'bill,' 'debt.' In historical context, keeping accurate accounts was a matter of honor and trust.

**2. Key Dimensions & Nuances:**
- This is a powerful curse word. It originally implied someone who has muddled their accounts—a dishonest, untrustworthy person who doesn't keep their word. It's now a general-purpose insult questioning someone's character and moral standing, often with a connotation of anger and contempt.

**3. Usage in Everyday Life:**
- It's used as a direct insult or an exclamation of fury.
    - **Phrase:** 你这个混账！ (Nǐ zhège hùnzhàng!)
    - **Example:** '你竟敢骗我，混账！' (Nǐ jìng gǎn piàn wǒ, hùnzhàng!) - 'How dare you cheat me, you bastard!'
    - **Feeling:** Intense anger, betrayal, and deep disrespect.

**4. A Guiding Philosophy:**
- It reflects a cultural emphasis on integrity and trust, especially in financial and social obligations. To call someone 混账 is to say they have violated the fundamental trust that holds relationships together.
"""
    return prompt

def call_deepseek_api(prompt):
    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            # {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": prompt},
        ],
        stream=False
    )

    return response.choices[0].message.content

def save_md_file(file_content, md_path=MD_PATH):
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(file_content)

def generate_anki_deck(md_file=MD_PATH, output_file=ANKI_PATH):
    try:
        result = subprocess.run([
            'mdanki', 
            md_file, 
            output_file,
            '--deck', 'Chinese Vocabulary'
        ], shell=True, capture_output=True, text=True, check=True)

        print("Anki Cards Generated Successfully!")
        return True

    except subprocess.CalledProcessError as e:
        print(f"Error generating Anki package: {e}")
        print(f"stderr: {e.stderr}")
        return False

    except FileNotFoundError:
        print("Error: mdanki not found. Make sure Node.js is installed and run: npm install")
        return False

def main():
    args = parse_arguments()

    if args.no_api:
        # Skip API call, use existing markdown file
        print("Skipping DeepSeek API call (--no-api flag used)")
        if not os.path.exists(args.markdown):
            print(f"Error: Markdown file {args.markdown} not found")
            sys.exit(1)
        md_filename = args.markdown
    else:
        # Generate prompt and call API (your existing code)
        chinese_words = read_txt_file(args.input)
        print(f"loaded {len(chinese_words)} chinese words")

        prompt = create_prompt(chinese_words)
        print("Calling DeepSeek API...")
        
        if not DEEPSEEK_API_KEY:
            print("Error: Please set DEEPSEEK_API_KEY environment variable")
            sys.exit(1)
            
        markdown_content = call_deepseek_api(prompt)
        print("Received response from Deepseek!")
        
        if markdown_content:
            save_md_file(markdown_content, args.markdown)
            print(f"Markdown file saved: {args.markdown}")
        else:
            print("Failed to get response from DeepSeek API")
            sys.exit(1)

    # Generate Anki package (always do this)
    print("Generating Anki package...")
    if generate_anki_deck(args.markdown, args.output):
        print("Pipeline completed successfully!")
        print(f"Anki package created: {args.output}")
    else:
        print("Failed to generate Anki package")

if __name__ == "__main__":
    main()
