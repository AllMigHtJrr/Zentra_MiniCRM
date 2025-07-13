import re
import logging
import aiofiles
import os
import signal
import time
from typing import Dict, Optional, Tuple
from PIL import Image
import io
import cv2
import numpy as np
import base64
import urllib.request
from io import BytesIO
from functools import wraps
import pytesseract

# PDF processing library
try:
    from pdf2image import convert_from_bytes
    PDF2IMAGE_AVAILABLE = True
except ImportError as e:
    PDF2IMAGE_AVAILABLE = False
    logging.warning(f"PDF2Image not available: {e}")
    logging.warning("Install PDF2Image: pip install pdf2image")

# OLM OCR Libraries
try:
    from transformers import AutoProcessor, Qwen2VLForConditionalGeneration
    import torch
    OLM_OCR_AVAILABLE = True
except ImportError as e:
    OLM_OCR_AVAILABLE = False
    logging.warning(f"OLM OCR libraries not available: {e}")
    logging.warning("Install OLM OCR libraries: pip install transformers torch opencv-python accelerate")

logger = logging.getLogger(__name__)

# Email validation regex pattern
EMAIL_PATTERN = r'[\w\.-]+@[\w\.-]+\.\w+'

def timeout_handler(signum, frame):
    """Handle timeout signal"""
    raise TimeoutError("Processing timed out")

def timeout(seconds):
    """Decorator to add timeout to functions"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if os.name == 'nt':  # Windows
                # Windows doesn't support signal.alarm, so we'll use a different approach
                return func(*args, **kwargs)
            else:
                # Set up timeout handler
                old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(seconds)
                try:
                    result = func(*args, **kwargs)
                finally:
                    signal.alarm(0)
                    signal.signal(signal.SIGALRM, old_handler)
                return result
        return wrapper
    return decorator

def validate_email(email: str) -> bool:
    """Validate email format using regex"""
    return bool(re.match(EMAIL_PATTERN, email))

def extract_email_from_text(text: str):
    match = re.search(r'[\w\.-]+@[\w\.-]+', text)
    return match.group(0) if match else None

def extract_name_from_text(text: str):
    lines = text.splitlines()
    for line in lines:
        if "name" in line.lower():
            return line.split(":")[-1].strip()
    for line in lines:
        if line.strip():
            return line.strip()
    return None

def extract_phone_from_text(text: str):
    match = re.search(r'(\+?\d{1,3}[-.\s]?)?(\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}', text)
    return match.group(0) if match else None

async def save_uploaded_file(file_content: bytes, filename: str) -> str:
    """Save uploaded file temporarily and return file path"""
    # Create uploads directory if it doesn't exist
    upload_dir = "uploads"
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
    
    file_path = os.path.join(upload_dir, filename)
    async with aiofiles.open(file_path, 'wb') as f:
        await f.write(file_content)
    
    return file_path

async def cleanup_temp_file(file_path: str):
    """Clean up temporary uploaded file"""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Cleaned up temporary file: {file_path}")
    except Exception as e:
        logger.error(f"Error cleaning up file {file_path}: {e}")

def preprocess_image(image_array: np.ndarray) -> np.ndarray:
    """Preprocess image for better OCR results"""
    # Convert to RGB if needed
    if len(image_array.shape) == 3 and image_array.shape[2] == 3:
        # Already RGB
        processed_img = image_array
    elif len(image_array.shape) == 3 and image_array.shape[2] == 4:
        # RGBA to RGB
        processed_img = cv2.cvtColor(image_array, cv2.COLOR_RGBA2RGB)
    elif len(image_array.shape) == 2:
        # Grayscale to RGB
        processed_img = cv2.cvtColor(image_array, cv2.COLOR_GRAY2RGB)
    else:
        processed_img = image_array
    
    return processed_img

def resize_image_to_1024(image: Image.Image) -> Image.Image:
    """Resize image so longest dimension is 1024 pixels"""
    width, height = image.size
    if width > height:
        new_width = 1024
        new_height = int(height * 1024 / width)
    else:
        new_height = 1024
        new_width = int(width * 1024 / height)
    
    return image.resize((new_width, new_height), Image.Resampling.LANCZOS)

def encode_image_to_base64(image: Image.Image) -> str:
    """Convert PIL image to base64 string"""
    img_buffer = BytesIO()
    image.save(img_buffer, format='PNG')
    img_str = base64.b64encode(img_buffer.getvalue()).decode()
    return img_str

def build_simple_prompt() -> str:
    """Build an optimized prompt for fast OLM OCR extraction"""
    return """Extract contact information from this document. Focus only on:
- Name
- Email
- Phone

Format: Name: [name], Email: [email], Phone: [phone]"""

def safe_generate_with_timeout(model, inputs, processor, max_timeout=15):
    """Safely generate text with aggressive timeout protection"""
    start_time = time.time()
    
    try:
        # Generate output with aggressive timeout protection
        with torch.no_grad():
            output = model.generate(
                **inputs,
                max_new_tokens=32,  # Very reduced for speed
                num_return_sequences=1,
                do_sample=False,
                pad_token_id=processor.tokenizer.eos_token_id,
                use_cache=True,
                repetition_penalty=1.0,
                # Remove all sampling parameters to avoid warnings
            )
        
        # Check if we're taking too long
        if time.time() - start_time > max_timeout:
            raise TimeoutError(f"Generation took longer than {max_timeout} seconds")
        
        return output
        
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        raise

def simple_fallback_extraction(file_content: bytes, filename: str) -> Dict[str, str]:
    """
    Simple fallback extraction when OLM OCR fails
    Uses basic text extraction and pattern matching
    """
    logger.info("🔄 Using simple fallback extraction")
    
    try:
        # Convert to PIL Image
        image = Image.open(BytesIO(file_content))
        
        # For now, return a basic structure that allows manual entry
        return {
            "name": "Manual Entry Required",
            "email": "manual@entry.required",
            "phone": "Manual Entry Required",
            "raw_text": "OCR processing completed with fallback. Please review and edit the extracted information.",
            "processing_time": 0.1,
            "model_load_time": 0.0,
            "fallback": True,
            "message": "OCR processing took too long. Please enter information manually or try with a smaller image."
        }
        
    except Exception as e:
        logger.error(f"Fallback extraction failed: {e}")
        return {
            "name": "Extraction Failed",
            "email": "failed@extraction.com",
            "phone": "Failed",
            "error": str(e),
            "processing_time": 0.1,
            "fallback": True,
            "message": "OCR processing failed. Please enter information manually."
        }

def validate_workflow_structure(nodes: list, edges: list) -> Tuple[bool, str]:
    """
    Validate workflow structure
    - Ensure Lead Created is always the trigger
    - Allow only up to 3 action nodes
    - Validate connected nodes
    """
    if not nodes:
        return False, "No nodes provided"
    
    # Check for trigger node
    trigger_nodes = [node for node in nodes if node.get('type') == 'trigger']
    if not trigger_nodes:
        return False, "No trigger node found"
    
    # Check if Lead Created is the trigger
    lead_created_trigger = any(
        node.get('type') == 'trigger' and 
        node.get('data', {}).get('label') == 'Lead Created'
        for node in nodes
    )
    if not lead_created_trigger:
        return False, "Lead Created trigger is required"
    
    # Count action nodes
    action_nodes = [node for node in nodes if node.get('type') == 'action']
    if len(action_nodes) > 3:
        return False, "Maximum 3 action nodes allowed"
    
    # Validate connected nodes
    node_ids = {node['id'] for node in nodes}
    for edge in edges:
        if edge.get('source') not in node_ids or edge.get('target') not in node_ids:
            return False, f"Edge references non-existent node: {edge.get('source')} -> {edge.get('target')}"
    
    return True, "Workflow structure is valid"

def get_workflow_action_description(node_data: dict) -> str:
    """Get human-readable description of workflow action"""
    label = node_data.get('label', 'Unknown')
    
    if 'email' in label.lower():
        return f"Email triggered: {label}"
    elif 'status' in label.lower():
        return f"Status changed to: {label}"
    elif 'sms' in label.lower():
        return f"SMS triggered: {label}"
    elif 'wait' in label.lower():
        return f"Wait action: {label}"
    else:
        return f"Action executed: {label}"

def sanitize_text(text: str) -> str:
    """Sanitize text input by trimming whitespace and normalizing"""
    return text.strip() if text else ""

def generate_unique_id() -> int:
    """Generate unique ID for leads"""
    import time
    return int(time.time() * 1000) 

def tesseract_ocr(file_content: bytes, filename: str) -> dict:
    try:
        text = ""
        if filename.lower().endswith('.pdf'):
            # Check if PDF processing is available
            if not PDF2IMAGE_AVAILABLE or 'convert_from_bytes' not in globals():
                return {
                    "name": None,
                    "email": None,
                    "phone": None,
                    "raw_text": "",
                    "confidence": 0.0,
                    "source": "Document",
                    "error": "PDF processing not available. Please install pdf2image: pip install pdf2image"
                }
            
            # Convert PDF to images
            images = convert_from_bytes(file_content)
            for image in images:
                text += pytesseract.image_to_string(image) + "\n"
        else:
            image = Image.open(BytesIO(file_content))
            text = pytesseract.image_to_string(image)
        name = extract_name_from_text(text)
        email = extract_email_from_text(text)
        phone = extract_phone_from_text(text)
        return {
            "name": name,
            "email": email,
            "phone": phone,
            "raw_text": text,
            "confidence": 1.0,
            "source": "Document"
        }
    except Exception as e:
        return {
            "name": None,
            "email": None,
            "phone": None,
            "raw_text": "",
            "confidence": 0.0,
            "source": "Document",
            "error": str(e)
        } 