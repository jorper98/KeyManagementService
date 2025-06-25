import os
import json
import requests
import sys # Import sys for flushing stdout
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__)
CORS(app) # Enable CORS for frontend requests

# Set debug mode explicitly for more verbose output during development
app.debug = True

# --- CRITICAL STARTUP DIAGNOSTICS ---
# Print environment variables directly at the start of the script's execution
print(f"--- app.py Startup Environment Check ---")
print(f"ENV KEYSTORE_API_URL: {os.environ.get('KEYSTORE_API_URL', 'NOT SET')}")
print(f"ENV KEYSTORE_JWT_TOKEN: {'SET' if os.environ.get('KEYSTORE_JWT_TOKEN') else 'NOT SET'}") # Avoid printing raw token
print(f"ENV GENERATIVE_AI_KEY_NAME: {os.environ.get('GENERATIVE_AI_KEY_NAME', 'NOT SET')}")
print(f"ENV GENERATIVE_AI_MODEL: {os.environ.get('GENERATIVE_AI_MODEL', 'NOT SET')}")
sys.stdout.flush() # Force print to flush immediately
print(f"--- End app.py Startup Environment Check ---")


# Configuration for Keystore and Generative AI API - loaded from environment variables
KEYSTORE_API_BASE = os.environ.get('KEYSTORE_API_URL', 'http://keystore:5000') # Defaults to internal Docker service name
KEYSTORE_JWT_TOKEN = os.environ.get('KEYSTORE_JWT_TOKEN') # JWT for this app to access Keystore
GENERATIVE_AI_KEY_NAME = os.environ.get('GENERATIVE_AI_KEY_NAME') # Name of the key in Keystore
GENERATIVE_AI_MODEL = os.environ.get('GENERATIVE_AI_MODEL', 'gemini-2.0-flash') # Default LLM model

# CRITICAL WARNINGS based on environment setup
if not KEYSTORE_JWT_TOKEN:
    print("CRITICAL WARNING: KEYSTORE_JWT_TOKEN environment variable not set. Secure key retrieval will fail.")
    sys.stdout.flush()
if not GENERATIVE_AI_KEY_NAME:
    print("CRITICAL WARNING: GENERATIVE_AI_KEY_NAME environment variable not set. Secure key retrieval will fail.")
    sys.stdout.flush()

# In-memory cache for the Generative AI API Key
_cached_generative_ai_api_key = None

def get_generative_ai_api_key_securely():
    """
    Retrieves the Generative AI API Key from the Keystore service.
    This function should only be called by the backend service.
    """
    global _cached_generative_ai_api_key

    if _cached_generative_ai_api_key:
        print("Using cached Generative AI API Key.")
        sys.stdout.flush()
        return _cached_generative_ai_api_key

    # Re-check configs before API call
    if not KEYSTORE_JWT_TOKEN:
        print("Error in get_generative_ai_api_key_securely: KEYSTORE_JWT_TOKEN is not set in environment.")
        sys.stdout.flush()
        return None
    if not GENERATIVE_AI_KEY_NAME:
        print("Error in get_generative_ai_api_key_securely: GENERATIVE_AI_KEY_NAME is not set in environment.")
        sys.stdout.flush()
        return None

    try:
        headers = {
            'Authorization': f'Bearer {KEYSTORE_JWT_TOKEN}',
            'Content-Type': 'application/json'
        }
        keystore_url = f"{KEYSTORE_API_BASE}/keys/{GENERATIVE_AI_KEY_NAME}"
        
        print(f"Attempting to retrieve Generative AI API Key from Keystore at URL: {keystore_url}")
        sys.stdout.flush()
        
        response = requests.get(keystore_url, headers=headers, timeout=10)
        
        print(f"Keystore response status code: {response.status_code}")
        sys.stdout.flush()

        if not response.ok:
            error_details = response.text
            print(f"Error response from Keystore: {error_details}")
            try:
                error_json = response.json()
                print(f"Keystore error JSON: {error_json.get('error', 'N/A')}")
            except json.JSONDecodeError:
                pass
            sys.stdout.flush()
            raise requests.exceptions.RequestException(f"Keystore returned non-2xx status: {response.status_code}")

        key_data = response.json()
        api_key = key_data.get('api_key')

        if not api_key:
            print("Error: 'api_key' field not found or is empty in successful Keystore response.")
            sys.stdout.flush()
            return None
        
        _cached_generative_ai_api_key = api_key
        print("Successfully retrieved Generative AI API Key from Keystore.")
        sys.stdout.flush()
        return api_key

    except requests.exceptions.ConnectionError as e:
        print(f"Connection Error: Could not connect to Keystore service at {KEYSTORE_API_BASE}. Is it running and accessible from inside this container?")
        print(f"Details: {e}")
        sys.stdout.flush()
        return None
    except requests.exceptions.Timeout as e:
        print(f"Timeout Error: Request to Keystore service timed out at {KEYSTORE_API_BASE}.")
        print(f"Details: {e}")
        sys.stdout.flush()
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error retrieving key from Keystore: {e}. Full traceback:")
        import traceback
        traceback.print_exc(file=sys.stdout) # Print full traceback
        sys.stdout.flush()
        return None
    except json.JSONDecodeError:
        print("Error: Could not decode JSON response from Keystore. Response was not valid JSON.")
        print(f"Raw Keystore response text: {response.text}")
        sys.stdout.flush()
        return None
    except Exception as e:
        print(f"An unexpected error occurred during key retrieval in get_generative_ai_api_key_securely: {e}. Full traceback:")
        import traceback
        traceback.print_exc(file=sys.stdout) # Print full traceback
        sys.stdout.flush()
        return None

@app.route('/')
def serve_index():
    """Serve the main HTML file for the chatbot frontend."""
    return send_from_directory('.', 'index.html')

@app.route('/style.css')
def serve_css():
    """Serve the CSS file for the chatbot frontend."""
    return send_from_directory('.', 'style.css')

@app.route('/chat', methods=['POST'])
def chat():
    """
    Chat endpoint. Retrieves Generative AI key securely and calls the LLM.
    """
    print(f"Received chat request from frontend: {request.json}")
    sys.stdout.flush()

    data = request.get_json()
    user_prompt = data.get('prompt')

    if not user_prompt:
        print("Error: No prompt provided in request.")
        sys.stdout.flush()
        return jsonify({'error': 'No prompt provided'}), 400

    # Retrieve the Generative AI API key securely (from Keystore via backend)
    generative_ai_api_key = get_generative_ai_api_key_securely()

    if not generative_ai_api_key:
        print("Generative AI API Key not obtained, returning 500 to frontend.")
        sys.stdout.flush()
        return jsonify({'error': 'Generative AI API Key not available. Check Keystore configuration or connectivity.'}), 500

    try:
        # Construct the chat history for the LLM API call
        chat_history = [
            { "role": "user", "parts": [ { "text": user_prompt } ] }
        ]

        llm_payload = {
            "contents": chat_history,
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 200,
            },
        }
        
        llm_api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{GENERATIVE_AI_MODEL}:generateContent?key={generative_ai_api_key}"
        print(f"Calling LLM API: {llm_api_url}")
        sys.stdout.flush()
        llm_response = requests.post(llm_api_url, headers={'Content-Type': 'application/json'}, json=llm_payload, timeout=20)
        llm_response.raise_for_status()

        llm_result = llm_response.json()

        if llm_result.get('candidates') and llm_result['candidates'][0].get('content') and llm_result['candidates'][0]['content'].get('parts'):
            bot_response_text = llm_result['candidates'][0]['content']['parts'][0]['text']
            print("Successfully received response from LLM.")
            sys.stdout.flush()
            return jsonify({'response': bot_response_text})
        else:
            print(f"Unexpected LLM response structure: {llm_result}")
            sys.stdout.flush()
            return jsonify({'error': 'Could not parse LLM response'}), 500

    except requests.exceptions.ConnectionError as e:
        print(f"Connection Error: Could not connect to Generative AI API. Details: {e}")
        sys.stdout.flush()
        return jsonify({'error': f'Failed to communicate with Generative AI API: {e}'}), 500
    except requests.exceptions.Timeout as e:
        print(f"Timeout Error: Request to Generative AI API timed out. Details: {e}")
        sys.stdout.flush()
        return jsonify({'error': f'Failed to communicate with Generative AI API: {e}'}), 500
    except requests.exceptions.RequestException as e:
        print(f"Error communicating with Generative AI API: {e}. Full traceback:")
        import traceback
        traceback.print_exc(file=sys.stdout)
        sys.stdout.flush()
        return jsonify({'error': f'Failed to communicate with Generative AI API: {e}'}), 500
    except json.JSONDecodeError:
        print("Error: Could not decode JSON response from Generative AI API. Response was not valid JSON.")
        print(f"Raw LLM response text: {llm_response.text}")
        sys.stdout.flush()
        return None
    except Exception as e:
        print(f"An unexpected error occurred during chat generation: {e}")
        import traceback
        traceback.print_exc(file=sys.stdout)
        sys.stdout.flush()
        return jsonify({'error': 'Internal server error during chat generation'}), 500

if __name__ == '__main__':
    print("Starting SampleApp2 Chatbot Backend...")
    sys.stdout.flush()
    print(f"Keystore API Base: {KEYSTORE_API_BASE}")
    print(f"Generative AI Key Name: {GENERATIVE_AI_KEY_NAME}")
    print(f"Generative AI Model: {GENERATIVE_AI_MODEL}")
    sys.stdout.flush()
    app.run(debug=True, host='0.0.0.0', port=5001)
