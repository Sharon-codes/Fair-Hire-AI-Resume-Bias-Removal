import docx
from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
import spacy
import re

# Initialize models
nlp = spacy.load("en_core_web_sm")
ner_pipeline = pipeline("ner", model="dslim/bert-base-NER", tokenizer="dslim/bert-base-NER")
generator = pipeline("text-generation", model="distilgpt2")

def read_docx(file_path):
    """Read text from a .docx file."""
    doc = docx.Document(file_path)
    full_text = []
    for para in doc.paragraphs:
        full_text.append(para.text)
    return "\n".join(full_text)

def extract_entities(text):
    """Extract relevant entities using NER and filter out sensitive ones."""
    # Run NER
    ner_results = ner_pipeline(text)
    
    # Initialize storage for entities
    entities = {"name": [], "organization": [], "skills": [], "education": []}
    
    # Process NER results
    current_name = []
    for entity in ner_results:
        if entity["entity"].startswith("B-PER") or entity["entity"].startswith("I-PER"):
            current_name.append(entity["word"])
        elif current_name:
            entities["name"].append(" ".join(current_name).replace(" ##", ""))
            current_name = []
        if entity["entity"].startswith("B-ORG"):
            entities["organization"].append(entity["word"].replace(" ##", ""))

    # Use spaCy for additional extraction (skills, education)
    doc = nlp(text)
    for sent in doc.sents:
        if any(keyword in sent.text.lower() for keyword in ["education", "degree", "university", "college"]):
            entities["education"].append(sent.text.strip())
        if any(keyword in sent.text.lower() for keyword in ["skills", "proficient", "expertise"]):
            entities["skills"].append(sent.text.strip())

    # Clean up entities
    entities["name"] = list(set(entities["name"]))[:1]  # Keep first name detected
    entities["organization"] = list(set(entities["organization"]))
    entities["skills"] = list(set(entities["skills"]))
    entities["education"] = list(set(entities["education"]))

    return entities

def remove_sensitive_info(text):
    """Remove potentially discriminatory information."""
    # Keywords and patterns to remove
    sensitive_keywords = [
        r"\b(ethnicity|race|color|religion|gender|age|nationality|marital status)\b",
        r"\b(black|white|asian|hispanic|latino|christian|muslim|jewish|male|female)\b",
        r"\b(born on|date of birth|DOB)\b",
    ]
    for pattern in sensitive_keywords:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)
    return text

def generate_report(entities):
    """Generate a professional report using distilgpt2."""
    prompt = f"""
    Candidate Report

    Name: {entities['name'][0] if entities['name'] else 'Not Provided'}
    Qualifications: {', '.join(entities['education']) if entities['education'] else 'Not Provided'}
    Experience: {', '.join(entities['organization']) if entities['organization'] else 'Not Provided'}
    Skills: {', '.join(entities['skills']) if entities['skills'] else 'Not Provided'}

    Summarize the above information in a professional tone for HR review, focusing on qualifications, experience, and skills.
    """
    
    report = generator(prompt, max_length=200, num_return_sequences=1, truncation=True)[0]["generated_text"]
    return report

def process_resume(file_path, output_path):
    """Main function to process resume and generate report."""
    # Read and clean resume
    text = read_docx(file_path)
    cleaned_text = remove_sensitive_info(text)
    
    # Extract entities
    entities = extract_entities(cleaned_text)
    
    # Generate report
    report = generate_report(entities)
    
    # Save report
    with open(output_path, "w") as f:
        f.write(report)
    
    return report

if __name__ == "__main__":
    resume_path = r"C:\Users\Samsung\Downloads\Resume  (1).docx"  # Replace with your resume file path
    output_path = "candidate_report.txt"  # Output report file
    report = process_resume(resume_path, output_path)
    print("Report generated successfully at", output_path)
    print(report)