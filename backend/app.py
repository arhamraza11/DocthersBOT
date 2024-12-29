import os
import re
from flask import Flask, request, jsonify
import google.generativeai as generativeai
from PIL import Image
from flask_cors import CORS
from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer
from PyPDF2 import PdfReader  # For PDF reading

app = Flask(__name__)
CORS(app)

# Configure the Google Gemini API
api_key = os.getenv("Gemini_Api_Key")
generativeai.configure(api_key=api_key)

# Define a reasonable token limit (adjust as needed)
TOKEN_LIMIT = 4096

# Initialize conversation history
conversation_history = []

# Initialize claim creation state
claim_creation_state = {
    'active': False,
    'claim_info': {
        'what_for': '',
        'claim_type': '',
        'amount': ''
    }
}

user_info_context = {
    "id": 87157,
    "cnic": "4240135849851",
    "name": "Arham Raza",
    "contact_no": "0312-1758206",
    "email": "null",
    "designation": "Orderbooker",
    "date_of_birth": "1992-01-17",
    "policies": [
        {
            "id": 268140,
            "start_date": "2024-06-01",
            "expiry_date": "2025-05-31",
            "available_limit": 24000,
            "policy_type_id": 1
        },
        {
            "id": 268141,
            "start_date": "2024-06-01",
            "expiry_date": "2025-05-31",
            "available_limit": 300000,
            "policy_type_id": 2
        }
    ],
    "dependents": [
        {
            "id": 221198,
            "name": "SHAZIA WAHID",
            "date_of_birth": "1988-03-24",
            "relationship_master_id": 5
        }
    ],
    "claims": [
        {
            "id": 43462490,
            "policy_id": 268140,
            "amount_claimed": 1000,
            "is_opd_claim": 1,
            "status": {
                "id": 43451291,
                "status_master_code": 0,
                "master": {
                    "name": "Pending For Checker"
                }
            }
        }
    ]
}

# Configure Qdrant client to use remote cluster
QDRANT_API_URL = os.getenv("QDRANT_API_URL")# Replace with your actual Qdrant cluster URL
API_KEY = os.getenv("QDRANT_API_KEY")  # Replace with your Qdrant API key
qdrant_client = QdrantClient(
    url=QDRANT_API_URL,
    api_key=API_KEY
)

# Initialize the sentence transformer model
encoder = SentenceTransformer("all-MiniLM-L6-v2")



# Function to index medical PDF documents in Qdrant



# Function to retrieve similar documents based on a query
collection_name='medical_documents'
model = SentenceTransformer('all-MiniLM-L6-v2')
def search_pdf(query):
    query_embedding = model.encode(query)
    search_result = qdrant_client.search(
        collection_name=collection_name,
        query_vector=query_embedding,
        limit=1
    )
    return search_result

# Function to generate a response based on the medical document context
def generate_medical_response(query, search_results):
    model = generativeai.GenerativeModel("gemini-1.5-flash")
    context = "\n\n".join([f"Document Excerpt: {hit.payload['page_text'][:300]}" for hit in search_results])
    user_context_info = (
                    f"User Info: Name: {user_info_context['name']}, "
                    f"Contact No: {user_info_context['contact_no']}, "
                    f"Designation: {user_info_context['designation']}, "
                    f"Policies: {user_info_context['policies']}, "
                    f"Dependents: {user_info_context['dependents']}, "
                    f"Claims: {user_info_context['claims']} "
                )
    full_prompt = f"Respond as if you are from the company DoctHers. Regards should always end from DoctHers Bot .if there is context so use context to answer the user in a professional manner. do not give respond other than claims user info and other things.{query}"+f"\n\nUser query: {query}\n\nContext:\n{context}\n\nResponse:"+f"\n\nUser Details Info:\n{user_context_info}\n\nDoctHers Bot"
   

    # Generate response using LLM (Google Gemini API)
    response = model.generate_content([full_prompt])
    return response.text.strip()

# Function to determine if the text indicates a claim request
def is_claim_request(text):
    model = generativeai.GenerativeModel("gemini-1.5-flash")
    prompt = f"Determine if the following text indicates a claim request means user is asking for creating a claim then only Return single word 'true' if it does, otherwise return false. Text: {text}"
    response = model.generate_content([prompt])
    return "true" in response.text.lower()

@app.route('/generate-response', methods=['POST'])
def generate_response():
    global conversation_history, claim_creation_state, user_info_context
    
    try:
        # Debugging: Print all incoming form data
        print("Form Data:", request.form)
        print("Files:", request.files)

        prompt = request.form.get('text', '')
        image = request.files.get('image')

        if not prompt and not image:
            return jsonify({'response': 'No input provided.'})

        if claim_creation_state['active']:
            claim_info = claim_creation_state['claim_info']
            if not claim_info['what_for']:
                response_text = 'What are you making the claim for?'
                claim_creation_state['claim_info']['what_for'] = prompt
            elif not claim_info['claim_type']:
                response_text = 'What type of claim do you want?'
                claim_creation_state['claim_info']['claim_type'] = prompt
            elif not claim_info['amount']:
                response_text = 'Please enter the total requested amount.'
                claim_creation_state['claim_info']['amount'] = prompt
            else:
                claim_creation_state['active'] = False
                claim_id = len(user_info_context['claims']) + 1
                user_info_context['claims'].append({
                    "id": claim_id,
                    "policy_id": user_info_context['policies'][0]['id'],  # Example policy
                    "amount_claimed": claim_creation_state['claim_info']['amount'],
                    "is_opd_claim": 1,
                    "status": {
                        "id": 43451291,
                        "status_master_code": 0,
                        "master": {
                            "name": "Pending For Checker"
                        }
                    }
                })
                claim_creation_state['claim_info'] = {
                    'what_for': '',
                    'claim_type': '',
                    'amount': ''
                }
                response_text = 'Claim created successfully!'
        else:
            # First, check if the prompt relates to a claim request
            if is_claim_request(prompt):
                claim_creation_state['active'] = True
                response_text = 'I can help you with creating a claim. Please provide the details to continue.'
            else:
                # Retrieve similar documents from Qdrant based on the user's query
                search_results = search_pdf(prompt)

                if search_results:
                    print(search_results)
                    response_text = generate_medical_response(prompt, search_results)
                else:
                    print(search_results)
                    response_text = generate_medical_response(prompt,"")

        return jsonify({'response': response_text})

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'response': 'An error occurred while processing your request.'}), 500

if __name__ == "__main__":
    # Example: Index a sample document
    
    app.run(debug=True)
