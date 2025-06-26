import os
import json
import requests
import sys
import logging
import traceback
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__)
CORS(app) # Enable CORS for frontend requests

app.debug = False # Set to False for production

logging.basicConfig(level=logging.INFO, stream=sys.stdout, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- CRITICAL STARTUP DIAGNOSTICS ---
logger.info(f"--- app.py Startup Environment Check ---")
logger.info(f"ENV KEYSTORE_API_URL: {os.environ.get('KEYSTORE_API_URL', 'NOT SET')}")
logger.info(f"ENV KEYSTORE_JWT_TOKEN: {'SET' if os.environ.get('KEYSTORE_JWT_TOKEN') else 'NOT SET'}")
logger.info(f"ENV GENERATIVE_AI_KEY_NAME: {os.environ.get('GENERATIVE_AI_KEY_NAME', 'NOT SET')}")
logger.info(f"ENV GENERATIVE_AI_MODEL: {os.environ.get('GENERATIVE_AI_MODEL', 'NOT SET')}")
logger.info(f"ENV LLM_TEMPERATURE (Default): {os.environ.get('LLM_TEMPERATURE', 'NOT SET')}") # Clarify default
logger.info(f"ENV LLM_MAX_OUTPUT_TOKENS (Default): {os.environ.get('LLM_MAX_OUTPUT_TOKENS', 'NOT SET')}") # Clarify default
logger.info(f"--- End app.py Startup Environment Check ---")


# Configuration for Keystore and Generative AI API - loaded from environment variables
KEYSTORE_API_BASE = os.environ.get('KEYSTORE_API_URL', 'http://keystore:5000')
KEYSTORE_JWT_TOKEN = os.environ.get('KEYSTORE_JWT_TOKEN')
GENERATIVE_AI_KEY_NAME = os.environ.get('GENERATIVE_AI_KEY_NAME')
GENERATIVE_AI_MODEL = os.environ.get('GENERATIVE_AI_MODEL', 'gemini-2.0-flash')

# LLM Generation Parameters from Environment Variables (used as defaults if not overridden by frontend)
DEFAULT_LLM_TEMPERATURE = float(os.environ.get('LLM_TEMPERATURE', 0.7))
DEFAULT_LLM_MAX_OUTPUT_TOKENS = int(os.environ.get('LLM_MAX_OUTPUT_TOKENS', 200))

# CRITICAL WARNINGS based on environment setup
if not KEYSTORE_JWT_TOKEN:
    logger.critical("KEYSTORE_JWT_TOKEN environment variable not set. Secure key retrieval will fail.")
if not GENERATIVE_AI_KEY_NAME:
    logger.critical("GENERATIVE_AI_KEY_NAME environment variable not set. Secure key retrieval will fail.")

_cached_generative_ai_api_key = None

def get_generative_ai_api_key_securely():
    global _cached_generative_ai_api_key
    if _cached_generative_ai_api_key:
        logger.info("Using cached Generative AI API Key.")
        return _cached_generative_ai_api_key
    if not KEYSTORE_JWT_TOKEN:
        logger.error("Error in get_generative_ai_api_key_securely: KEYSTORE_JWT_TOKEN is not set in environment.")
        return None
    if not GENERATIVE_AI_KEY_NAME:
        logger.error("Error in get_generative_ai_api_key_securely: GENERATIVE_AI_KEY_NAME is not set in environment.")
        return None
    try:
        headers = {
            'Authorization': f'Bearer {KEYSTORE_JWT_TOKEN}',
            'Content-Type': 'application/json'
        }
        keystore_url = f"{KEYSTORE_API_BASE}/keys/{GENERATIVE_AI_KEY_NAME}"
        logger.info(f"Attempting to retrieve Generative AI API Key from Keystore at URL: {keystore_url}")
        response = requests.get(keystore_url, headers=headers, timeout=10)
        logger.info(f"Keystore response status code: {response.status_code}")
        if not response.ok:
            error_details = response.text
            logger.error(f"Error response from Keystore: {error_details}")
            try:
                error_json = response.json()
                logger.error(f"Keystore error JSON: {error_json.get('error', 'N/A')}")
            except json.JSONDecodeError: pass
            raise requests.exceptions.RequestException(f"Keystore returned non-2xx status: {response.status_code}")
        key_data = response.json()
        api_key = key_data.get('api_key')
        if not api_key:
            logger.error("Error: 'api_key' field not found or is empty in successful Keystore response.")
            return None
        _cached_generative_ai_api_key = api_key
        logger.info("Successfully retrieved Generative AI API Key from Keystore.")
        return api_key
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection Error: Could not connect to Keystore service at {KEYSTORE_API_BASE}. Is it running and accessible from inside this container? Details: {e}")
        return None
    except requests.exceptions.Timeout as e:
        logger.error(f"Timeout Error: Request to Keystore service timed out at {KEYSTORE_API_BASE}. Details: {e}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error retrieving key from Keystore: {e}. Full traceback:\n{traceback.format_exc()}")
        return None
    except json.JSONDecodeError:
        logger.error(f"Error: Could not decode JSON response from Keystore. Response was not valid JSON. Raw Keystore response text: {response.text}")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred during key retrieval in get_generative_ai_api_key_securely: {e}. Full traceback:\n{traceback.format_exc()}")
        return None

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/style.css')
def serve_css():
    return send_from_directory('.', 'style.css')

@app.route('/chat', methods=['POST'])
def chat():
    logger.debug(f"Received chat request from frontend: {request.json}") 
    data = request.get_json()
    user_prompt = data.get('prompt')

    # NEW: Accept and validate temperature and maxOutputTokens from frontend
    # Use defaults if not provided or invalid
    temperature_param = DEFAULT_LLM_TEMPERATURE
    max_output_tokens_param = DEFAULT_LLM_MAX_OUTPUT_TOKENS

    if 'temperature' in data:
        try:
            temp_val = float(data['temperature'])
            if 0.0 <= temp_val <= 1.0:
                temperature_param = temp_val
            else:
                logger.warning(f"Invalid temperature value from frontend: {data['temperature']}. Using default: {DEFAULT_LLM_TEMPERATURE}")
        except (ValueError, TypeError):
            logger.warning(f"Non-numeric temperature value from frontend: {data['temperature']}. Using default: {DEFAULT_LLM_TEMPERATURE}")
    
    if 'maxOutputTokens' in data:
        try:
            max_val = int(data['maxOutputTokens'])
            if max_val >= 1: # Assuming minimum 1 token output
                max_output_tokens_param = max_val
            else:
                logger.warning(f"Invalid maxOutputTokens value from frontend: {data['maxOutputTokens']}. Using default: {DEFAULT_LLM_MAX_OUTPUT_TOKENS}")
        except (ValueError, TypeError):
            logger.warning(f"Non-integer maxOutputTokens value from frontend: {data['maxOutputTokens']}. Using default: {DEFAULT_LLM_MAX_OUTPUT_TOKENS}")

    if not user_prompt:
        logger.warning("No prompt provided in request.")
        return jsonify({'error': 'No prompt provided'}), 400

    generative_ai_api_key = get_generative_ai_api_key_securely()

    if not generative_ai_api_key:
        logger.error("Generative AI API Key not obtained, returning 500 to frontend.")
        return jsonify({'error': 'Generative AI API Key not available. Check Keystore configuration or connectivity.'}), 500

    try:
        chat_history = [
            { "role": "user", "parts": [ { "text": user_prompt } ] }
        ]

        llm_payload = {
            "contents": chat_history,
            "generationConfig": {
                "temperature": temperature_param,
                "maxOutputTokens": max_output_tokens_param,
            },
        }
        
        llm_api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{GENERATIVE_AI_MODEL}:generateContent?key={generative_ai_api_key}"
        logger.info(f"Calling LLM API for prompt: '{user_prompt[:50]}...' with T={temperature_param}, Max={max_output_tokens_param}")
        llm_response = requests.post(llm_api_url, headers={'Content-Type': 'application/json'}, json=llm_payload, timeout=20)
        llm_response.raise_for_status()

        llm_result = llm_response.json()

        if llm_result.get('candidates') and llm_result['candidates'][0].get('content') and llm_result['candidates'][0]['content'].get('parts'):
            bot_response_text = llm_result['candidates'][0]['content']['parts'][0]['text']
            logger.info("Successfully received response from LLM.")
            return jsonify({
                'response': bot_response_text,
                'temperature': temperature_param,      # Include in response
                'maxOutputTokens': max_output_tokens_param # Include in response
            })
        else:
            logger.warning(f"Unexpected LLM response structure: {llm_result}")
            return jsonify({'error': 'Could not parse LLM response'}), 500

    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection Error: Could not connect to Generative AI API. Details: {e}")
        return jsonify({'error': f'Failed to communicate with Generative AI API: {e}'}), 500
    except requests.exceptions.Timeout as e:
        logger.error(f"Timeout Error: Request to Generative AI API timed out. Details: {e}")
        return jsonify({'error': f'Failed to communicate with Generative AI API: {e}'}), 500
    except requests.exceptions.RequestException as e:
        logger.error(f"Error communicating with Generative AI API: {e}. Full traceback:\n{traceback.format_exc()}")
        return jsonify({'error': f'Failed to communicate with Generative AI API: {e}'}), 500
    except json.JSONDecodeError:
        logger.error(f"Error: Could not decode JSON response from Generative AI API. Response was not valid JSON. Raw LLM response text: {llm_response.text}")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred during chat generation: {e}. Full traceback:\n{traceback.format_exc()}")
        return jsonify({'error': 'Internal server error during chat generation'}), 500

if __name__ == '__main__':
    logger.info("Starting SampleApp2 Chatbot Backend...")
    logger.info(f"Keystore API Base: {KEYSTORE_API_BASE}")
    logger.info(f"Generative AI Key Name: {GENERATIVE_AI_KEY_NAME}")
    logger.info(f"Generative AI Model: {GENERATIVE_AI_MODEL}")
    logger.info(f"LLM Temperature (configured): {DEFAULT_LLM_TEMPERATURE}") # Log default
    logger.info(f"LLM Max Output Tokens (configured): {DEFAULT_LLM_MAX_OUTPUT_TOKENS}") # Log default
    
    if app.debug:
        app.run(debug=True, host='0.0.0.0', port=5001)
    else:
        logger.info("Flask debug mode is OFF. Expecting Gunicorn to manage the server.")
