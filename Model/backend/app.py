# backend/app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import io
import base64
import docx
import torch # Still needed for tensor operations, but won't use CUDA
from transformers import AutoModelForCausalLM, AutoTokenizer
import os
import re

# --- Flask App Setup ---
app = Flask(__name__)
# Enable CORS for communication with your frontend (adjust origins in production)
CORS(app, resources={r"/*": {"origins": "*"}}) 

# --- LLaMA 3.1 Model Configuration ---
LLAMA_MODEL_ID = "meta-llama/Meta-Llama-3.1-8B-Instruct"

# --- Global Variables for Model ---
tokenizer = None
model = None
model_loaded = False
# Define the device explicitly as CPU
DEVICE = "cpu"

def load_llama_model():
    """
    Loads the LLaMA 3.1 model and tokenizer for CPU inference.
    This function will be called once when the Flask app starts.
    Requires HUGGING_FACE_HUB_TOKEN environment variable to be set.
    """
    global tokenizer, model, model_loaded
    if model_loaded:
        print("Model already loaded.")
        return

    print(f"Loading LLaMA 3.1 model for CPU: {LLAMA_MODEL_ID}...")
    try:
        # Check for Hugging Face token
        hf_token = os.environ.get("HUGGING_FACE_HUB_TOKEN")
        if not hf_token:
            raise ValueError("HUGGING_FACE_HUB_TOKEN environment variable not set. Please set it.")

        tokenizer = AutoTokenizer.from_pretrained(LLAMA_MODEL_ID, token=hf_token)
        model = AutoModelForCausalLM.from_pretrained(
            LLAMA_MODEL_ID,
            # No torch_dtype=torch.bfloat16 or device_map="auto" for CPU
            low_cpu_mem_usage=True, # Still useful for reducing CPU RAM during loading
            token=hf_token
        ).to(DEVICE) # Explicitly move model to CPU after loading

        model.eval() # Set model to evaluation mode
        model_loaded = True
        print(f"LLaMA 3.1 model loaded successfully on {DEVICE}.")
    except Exception as e:
        print(f"Error loading LLaMA model: {e}")
        # Exit or raise error, as the app won't function without the model
        exit(1)

def read_docx_from_bytes(docx_bytes):
    """
    Reads text from a .docx file provided as bytes.
    """
    try:
        doc = docx.Document(io.BytesIO(docx_bytes))
        full_text = []
        for para in doc.paragraphs:
            full_text.append(para.text)
        return "\n".join(full_text)
    except Exception as e:
        print(f"Error reading DOCX: {e}")
        raise ValueError("Could not read DOCX file.")

def generate_llama_report(resume_text):
    """
    Generates a bias-free HR report using the loaded LLaMA 3.1 model.
    """
    if not model_loaded:
        raise RuntimeError("LLaMA model not loaded.")

    messages = [
        {"role": "system", "content": "You are an expert HR AI assistant specializing in bias-free resume screening. Your task is to extract and summarize ONLY objective, professional information from resumes: qualifications, experience, and skills. It is IMPERATIVE that you COMPLETELY OMIT any and all personal or demographic details that could introduce bias. Maintain a strictly professional, neutral, and concise tone. Your output should be a clear, structured report."},
        {"role": "user", "content": f"""
        Analyze the following resume content and provide a summary for HR review.

        STRICT EXCLUSION RULES (Do NOT include these under ANY circumstances):
        - Candidate's Name (first, last, full names, initials, nicknames).
        - Any personal identifying information.
        - Gender (pronouns like he/she, or terms like male/female, woman/man, etc.).
        - Age, Date of Birth, or any age-related references (e.g., "graduated in X", "born in 19XX").
        - Ethnicity, Race, Religion, or Nationality.
        - Marital Status or family information.
        - Contact information (email, phone number, physical address, personal social media links, personal websites).
        - Photos or image descriptions.
        - Any political affiliations, non-professional awards, or hobbies.
        - Any information that is not directly related to professional qualifications, experience, or demonstrable skills.

        Focus ONLY on the following professional categories:
        - Academic Qualifications (degrees, institutions, major fields).
        - Work Experience (company names, job titles, key responsibilities, quantifiable achievements/impact).
        - Technical and Professional Skills (programming languages, software, tools, methodologies, and relevant professional soft skills like problem-solving, communication, teamwork).

        Format the report clearly with distinct headings: "Qualifications", "Experience", and "Skills". Use bullet points or clear paragraphs.

        Resume Content:
        {resume_text}

        Candidate Report (Bias-Free):
        """}
    ]

    try:
        input_text = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )

        # Tokenize the input text and ensure it's on the specified DEVICE (CPU)
        model_inputs = tokenizer(input_text, return_tensors="pt").to(DEVICE)

        generated_ids = model.generate(
            **model_inputs,
            max_new_tokens=700,
            do_sample=True,
            temperature=0.4,
            top_p=0.9,
            num_return_sequences=1,
            pad_token_id=tokenizer.eos_token_id
        )
        
        generated_report = tokenizer.batch_decode(generated_ids[:, model_inputs["input_ids"].shape[1]:], skip_special_tokens=True)[0]
        generated_report = generated_report.replace(tokenizer.eos_token, "").strip()

        return generated_report
    except Exception as e:
        print(f"Error during LLaMA generation: {e}")
        raise RuntimeError(f"Failed to generate report: {e}")

# --- API Endpoint ---
@app.route('/process_resume', methods=['POST'])
def process_resume():
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    base64_file_content = data.get('fileContent')
    file_name = data.get('fileName')

    if not base64_file_content:
        return jsonify({"error": "No file content provided"}), 400

    if not file_name.endswith('.docx'):
        return jsonify({"error": "Only .docx files are supported"}), 400

    try:
        docx_bytes = base64.b64decode(base64_file_content)
        raw_resume_text = read_docx_from_bytes(docx_bytes)
        final_report = generate_llama_report(raw_resume_text)
        return jsonify({"report": final_report}), 200

    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except RuntimeError as re:
        return jsonify({"error": str(re)}), 500
    except Exception as e:
        print(f"Unhandled error: {e}")
        return jsonify({"error": "An unexpected error occurred on the server."}), 500

# --- App Initialization ---
if __name__ == '__main__':
    # Load the model when the application starts
    load_llama_model()
    # Run the Flask app
    app.run(host='0.0.0.0', port=5000, debug=False)