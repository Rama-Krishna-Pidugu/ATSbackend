import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

def clean_json_response(response):
    # Placeholder: implement any cleaning needed
    return response

def track_token_usage(user, model, input_tokens, output_tokens):
    # Placeholder: implement tracking if needed
    pass

def call_groq(prompt: str, user=None, temperature: float = 0.7, max_tokens: int = 1000):
    try:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not configured in environment")

        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=temperature,
            max_tokens=max_tokens
        )
        cleaned_response = clean_json_response(response.choices[0].message.content.strip())
        if user:
            track_token_usage(
                user=user,
                model="llama-3.3-70b-versatile",    
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens
            )
        return cleaned_response, {
            'input_tokens': response.usage.prompt_tokens,
            'output_tokens': response.usage.completion_tokens
        }
    except Exception as e:
        raise Exception(f"Error calling GROQ API: {str(e)}") 