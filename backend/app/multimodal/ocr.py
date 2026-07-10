import os
import json
import numpy as np
from PIL import Image
import io
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
 
load_dotenv()
 
_reader = None
 
 
def get_reader():
    """Lazy-load EasyOCR reader since it's slow to initialize."""
    global _reader
    if _reader is None:
        import easyocr
        _reader = easyocr.Reader(["en"], gpu=False)
    return _reader
 
 
def extract_text(image_bytes: bytes) -> str:
    reader = get_reader()
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    image_array = np.array(image)
 
    results = reader.readtext(image_array)
    lines = [text for (_, text, confidence) in results if confidence > 0.3]
    return "\n".join(lines)
 
 
STRUCTURE_PROMPT = """The following text was extracted from a doctor's prescription
using OCR. It may contain errors or be incomplete.
 
Extract only what is explicitly written. Do not infer or guess medicines, dosages,
or frequencies that are not clearly present in the text.
 
Respond ONLY with valid JSON in this format:
{{"medicines": [{{"name": "...", "dosage": "...", "frequency": "..."}}], "notes": "..."}}
 
If a field is not present for a medicine, use null. If nothing readable was found,
return an empty medicines list and explain in notes.
 
OCR Text:
{ocr_text}
"""
 
 
def structure_prescription(ocr_text: str) -> dict:
    if not ocr_text.strip():
        return {"medicines": [], "notes": "No readable text found in image."}
 
    llm = ChatGroq(model="openai/gpt-oss-20b", temperature=0)
    prompt = ChatPromptTemplate.from_template(STRUCTURE_PROMPT)
    chain = prompt | llm
 
    response = chain.invoke({"ocr_text": ocr_text})
 
    try:
        return json.loads(response.content)
    except json.JSONDecodeError:
        return {"medicines": [], "notes": "Could not parse structured output. Raw OCR text: " + ocr_text}
 
 
def process_prescription(image_bytes: bytes) -> dict:
    raw_text = extract_text(image_bytes)
    structured = structure_prescription(raw_text)
    structured["raw_ocr_text"] = raw_text
    return structured
 
 
if __name__ == "__main__":
    test_path = os.path.join("data", "images", "prescription_sample.jpg")
    if not os.path.exists(test_path):
        print(f"Put a test prescription image at {test_path} to run this test.")
    else:
        with open(test_path, "rb") as f:
            image_bytes = f.read()
        result = process_prescription(image_bytes)
        print(json.dumps(result, indent=2))
 