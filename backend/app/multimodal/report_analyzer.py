
import os
import json
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
 
from app.multimodal.image_processor import analyze_image
from app.multimodal.ocr import extract_text
 
load_dotenv()
 
ANALYSIS_PROMPT = """You are summarizing a medical lab report or prescription for
hospital staff review.
 
You are given visual analysis and/or OCR text extracted from the document below.
Use ONLY this content. Do not add medical knowledge, do not diagnose, and do not
generate your own treatment recommendations.
 
Visual analysis:
{vision_text}
 
OCR extracted text:
{ocr_text}
 
Produce a summary with exactly two sections:
 
Observations: list only what is explicitly stated or visible in the source
(values, findings, markings, written notes).
 
Recommendations: list only what the report or doctor explicitly wrote as next
steps, advice, or instructions. If no recommendation is written in the source,
state "No recommendations were written in the source document" — do not invent one.
 
Respond ONLY with valid JSON in this format:
{{"observations": ["..."], "recommendations": ["..."]}}
"""
 
 
def analyze_report(image_bytes: bytes = None, mime_type: str = "image/jpeg", use_ocr: bool = True) -> dict:
    vision_text = ""
    ocr_text = ""
 
    if image_bytes:
        vision_text = analyze_image(image_bytes, mime_type=mime_type)
        if use_ocr:
            ocr_text = extract_text(image_bytes)
 
    if not vision_text and not ocr_text:
        return {
            "observations": [],
            "recommendations": [],
            "notes": "No image or text provided for analysis.",
        }
 
    llm = ChatGroq(model="openai/gpt-oss-20b", temperature=0)
    prompt = ChatPromptTemplate.from_template(ANALYSIS_PROMPT)
    chain = prompt | llm
 
    response = chain.invoke({
        "vision_text": vision_text or "Not available.",
        "ocr_text": ocr_text or "Not available.",
    })
 
    try:
        result = json.loads(response.content)
    except json.JSONDecodeError:
        result = {
            "observations": [],
            "recommendations": [],
            "notes": "Could not parse structured output.",
        }
 
    result["vision_analysis_used"] = bool(vision_text)
    result["ocr_used"] = bool(ocr_text)
    return result
 
 
if __name__ == "__main__":
    test_path = os.path.join("data", "images", "sample.jpg")
    if not os.path.exists(test_path):
        print(f"Put a test image at {test_path} to run this test.")
    else:
        with open(test_path, "rb") as f:
            image_bytes = f.read()
        result = analyze_report(image_bytes)
        print(json.dumps(result, indent=2))
 