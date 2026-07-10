import os
import base64
from dotenv import load_dotenv
from groq import Groq
 
load_dotenv()
 
VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
 
ANALYSIS_PROMPT = """You are assisting hospital staff in reviewing a medical image
(such as a prescription, lab report, or scan).
 
Describe only what is visibly present in the image. Do not diagnose, recommend
treatment, or add medical advice beyond what is written or shown.
 
Provide:
1. Observations: what you can see in the image (text, values, markings, visible content)
2. Notes: anything unclear, illegible, or that needs human review
 
Do not generate your own medical recommendations."""
 
 
def encode_image(image_bytes: bytes) -> str:
    return base64.b64encode(image_bytes).decode("utf-8")
 
 
def analyze_image(image_bytes: bytes, mime_type: str = "image/jpeg") -> str:
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    base64_image = encode_image(image_bytes)
 
    completion = client.chat.completions.create(
        model=VISION_MODEL,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": ANALYSIS_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{base64_image}"
                        },
                    },
                ],
            }
        ],
        temperature=0,
        max_completion_tokens=1024,
    )
 
    return completion.choices[0].message.content
 
 
if __name__ == "__main__":
    test_path = os.path.join("data", "images", "sample.jpg")
    if not os.path.exists(test_path):
        print(f"Put a test image at {test_path} to run this test.")
    else:
        with open(test_path, "rb") as f:
            image_bytes = f.read()
        result = analyze_image(image_bytes)
        print(result)