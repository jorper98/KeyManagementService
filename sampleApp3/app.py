# app.py v0.7.1
#
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

# Dynamically load all defined LLM options
LLM_OPTIONS = []
i = 1
while True:
    model_name_env = f'GENERATIVE_AI_MODEL_{i:02d}'
    key_name_env = f'GENERATIVE_AI_KEY_NAME_{i:02d}'
    type_env = f'GENERATIVE_AI_TYPE_{i:02d}' 
    
    model_name = os.environ.get(model_name_env)
    key_name = os.environ.get(key_name_env)
    model_type = os.environ.get(type_env) 
    
    if model_name and key_name and model_type: 
        LLM_OPTIONS.append({
            'id': f'llm_option_{i:02d}',
            'name': model_name,
            'key_name': key_name,
            'type': model_type.lower() 
        })
        logger.info(f"Loaded LLM Option: {model_name_env}={model_name}, {key_name_env}={key_name}, {type_env}={model_type}")
        i += 1
    else:
        # Stop if we hit a missing part of a numbered LLM config
        if model_name or key_name or model_type:
            logger.warning(f"Incomplete LLM Option {i:02d} detected. Missing MODEL, KEY_NAME, or TYPE. Stopping LLM option loading.")
        break

if not LLM_OPTIONS:
    logger.critical("No LLM options found in environment variables (e.g., GENERATIVE_AI_MODEL_01, GENERATIVE_AI_KEY_NAME_01, GENERATIVE_AI_TYPE_01). Chatbot will not function.")

# Default to the first loaded LLM option if DEFAULT_GENERATIVE_AI_MODEL is not set
DEFAULT_GENERATIVE_AI_MODEL = os.environ.get('DEFAULT_GENERATIVE_AI_MODEL', LLM_OPTIONS[0]['name'] if LLM_OPTIONS else 'gemini-1.5-flash-latest')

logger.info(f"ENV LLM_TEMPERATURE (Default): {os.environ.get('LLM_TEMPERATURE', 'NOT SET')}")
logger.info(f"ENV LLM_MAX_OUTPUT_TOKENS (Default): {os.environ.get('LLM_MAX_OUTPUT_TOKENS', 'NOT SET')}")
logger.info(f"--- End app.py Startup Environment Check ---")


# Configuration for Keystore and Generative AI API - loaded from environment variables
KEYSTORE_API_BASE = os.environ.get('KEYSTORE_API_URL', 'http://keystore:5000')
KEYSTORE_JWT_TOKEN = os.environ.get('KEYSTORE_JWT_TOKEN')

# LLM Generation Parameters from Environment Variables (used as defaults if not overridden by frontend)
DEFAULT_LLM_TEMPERATURE = float(os.environ.get('LLM_TEMPERATURE', 0.7))
DEFAULT_LLM_MAX_OUTPUT_TOKENS = int(os.environ.get('LLM_MAX_OUTPUT_TOKENS', 200))

# CRITICAL WARNINGS based on environment setup
if not KEYSTORE_JWT_TOKEN:
    logger.critical("KEYSTORE_JWT_TOKEN environment variable not set. Secure key retrieval will fail.")

_cached_generative_ai_api_key = {} # Use a dictionary to cache keys per key_name

def get_generative_ai_api_key_securely(key_name):
    global _cached_generative_ai_api_key
    if key_name in _cached_generative_ai_api_key:
        logger.info(f"Using cached Generative AI API Key for {key_name}.")
        return _cached_generative_ai_api_key[key_name]
    
    if not KEYSTORE_JWT_TOKEN:
        logger.error("Error in get_generative_ai_api_key_securely: KEYSTORE_JWT_TOKEN is not set in environment.")
        return None
    if not key_name:
        logger.error("Error in get_generative_ai_api_key_securely: key_name is not provided.")
        return None
    try:
        headers = {
            'Authorization': f'Bearer {KEYSTORE_JWT_TOKEN}',
            'Content-Type': 'application/json'
        }
        keystore_url = f"{KEYSTORE_API_BASE}/keys/{key_name}"
        logger.info(f"Attempting to retrieve Generative AI API Key '{key_name}' from Keystore at URL: {keystore_url}")
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
        _cached_generative_ai_api_key[key_name] = api_key
        logger.info(f"Successfully retrieved Generative AI API Key for '{key_name}' from Keystore.")
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

@app.route('/llm-options', methods=['GET'])
def get_llm_options():
    """Returns the list of available LLM models and their names."""
    # We only expose 'id' and 'name' to the frontend, type and key_name are backend concerns
    options_for_frontend = [{'id': opt['id'], 'name': opt['name']} for opt in LLM_OPTIONS]
    return jsonify({
        'options': options_for_frontend,
        'default_model': DEFAULT_GENERATIVE_AI_MODEL
    })

@app.route('/llm-defaults', methods=['GET'])
def get_llm_defaults():
    """Returns the default LLM temperature and max output tokens configured on the backend."""
    return jsonify({
        'default_temperature': DEFAULT_LLM_TEMPERATURE,
        'default_max_output_tokens': DEFAULT_LLM_MAX_OUTPUT_TOKENS
    })

# Simple word count based token estimator (approximation)
def estimate_tokens_simple(text):
    if not text:
        return 0
    return len(text.split())

# Max context window sizes (approximate, adjust based on actual model limits)
# These are crucial for managing conversation history
MAX_CONTEXT_TOKENS = {
    "gemini-1.5-flash-latest": 1000000, # Large context, but manage for practical use
    "gemini-1.5-pro-latest": 1000000,
    "gpt-3.5-turbo": 16385, # Actual context depends on version
    "gpt-4o-mini": 128000,
    "mistralai/mistral-7b-instruct": 8192, # Common for Mistral-7B
    "deepseek-ai/deepseek-coder": 16384, # Common for DeepSeek Coder
    # Add other models and their context windows here
}
DEFAULT_MAX_CONTEXT_WINDOW = 4000 # A reasonable default if model not found in map


@app.route('/chat', methods=['POST'])
def chat():
    logger.debug(f"Received chat request from frontend: {request.json}") 
    data = request.get_json()
    user_prompt = data.get('prompt')
    selected_llm_id = data.get('selectedLlmId')
    chat_history_from_frontend = data.get('history', []) 

    if not user_prompt:
        logger.warning("No prompt provided in request.")
        return jsonify({'error': 'No prompt provided'}), 400

    # Determine which LLM model and key to use based on selected_llm_id
    selected_llm_config = next((opt for opt in LLM_OPTIONS if opt['id'] == selected_llm_id), None)
    
    if not selected_llm_config:
        logger.error(f"Invalid LLM ID received: {selected_llm_id}. Attempting to fallback to default model: {DEFAULT_GENERATIVE_AI_MODEL}")
        selected_llm_config = next((opt for opt in LLM_OPTIONS if opt['name'] == DEFAULT_GENERATIVE_AI_MODEL), None)
        if not selected_llm_config and LLM_OPTIONS:
            selected_llm_config = LLM_OPTIONS[0] # Fallback to the first available if default not found
        
        if not selected_llm_config:
            logger.critical("No valid LLM configuration could be determined after fallback. Cannot process chat request.")
            return jsonify({'error': 'No valid LLM configuration available.'}), 500


    current_generative_ai_model = selected_llm_config['name']
    current_generative_ai_key_name = selected_llm_config['key_name']
    current_generative_ai_type = selected_llm_config['type'] 

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
            if max_val >= 1: 
                max_output_tokens_param = max_val
            else:
                logger.warning(f"Invalid maxOutputTokens value from frontend: {data['maxOutputTokens']}. Using default: {DEFAULT_LLM_MAX_OUTPUT_TOKENS}")
        except (ValueError, TypeError):
            logger.warning(f"Non-integer maxOutputTokens value from frontend: {data['maxOutputTokens']}. Using default: {DEFAULT_LLM_MAX_OUTPUT_TOKENS}")

    generative_ai_api_key = get_generative_ai_api_key_securely(current_generative_ai_key_name)

    if not generative_ai_api_key:
        logger.error(f"Generative AI API Key for '{current_generative_ai_key_name}' not obtained, returning 500 to frontend.")
        return jsonify({'error': f'Generative AI API Key for {current_generative_ai_key_name} not available. Check Keystore configuration or connectivity.'}), 500

    try:
        llm_payload = {}
        llm_url = ""
        llm_headers = {'Content-Type': 'application/json'} 

        final_temperature_for_api = temperature_param 

        # --- CONTEXT MANAGEMENT ---
        # Get the max context window for the current model, use a default if not found
        model_context_window = MAX_CONTEXT_TOKENS.get(current_generative_ai_model, DEFAULT_MAX_CONTEXT_WINDOW)
        
        # Estimate prompt tokens for the current user input
        current_prompt_tokens = estimate_tokens_simple(user_prompt)

        llm_chat_history = []
        context_tokens_sum = 0
        
        # Iterate history in reverse to prioritize recent messages
        for msg in reversed(chat_history_from_frontend):
            msg_content = msg.get('content', '')
            msg_role = msg.get('role')
            if msg_content and msg_role:
                msg_tokens = estimate_tokens_simple(msg_content)
                # Keep messages as long as total context + current prompt + expected response tokens are within limit
                # We subtract max_output_tokens_param because that's what we expect the model to generate
                # and current_prompt_tokens because that's the current turn's input
                if (context_tokens_sum + msg_tokens + current_prompt_tokens + max_output_tokens_param) < model_context_window:
                    # Prepend to build history in chronological order for the API call
                    llm_chat_history.insert(0, {'role': msg_role, 'content': msg_content})
                    context_tokens_sum += msg_tokens
                else:
                    logger.warning(f"Truncated chat history for model '{current_generative_ai_model}'. Context window limit reached. Dropping older message: {msg_content[:50]}...")
                    break # Stop adding older messages

        # Add the current user prompt to the history sent to the LLM
        # This is added after truncation logic, as it's always part of the current turn
        llm_chat_history.append({"role": "user", "content": user_prompt})


        # Determine the correct API call structure based on the GENERATIVE_AI_TYPE
        if current_generative_ai_type == "gemini":
            # Gemini expects 'parts' within a 'content' object for each turn.
            # Convert simple history format to Gemini's format.
            formatted_gemini_history = []
            for entry in llm_chat_history:
                formatted_gemini_history.append({
                    "role": "user" if entry['role'] == "user" else "model", # Gemini uses 'model' for assistant
                    "parts": [{"text": entry['content']}]
                })

            llm_payload = {
                "contents": formatted_gemini_history,
                "generationConfig": {
                    "temperature": temperature_param, # For Gemini, use the original temperature_param
                    "maxOutputTokens": max_output_tokens_param,
                },
            }
            llm_url = f"https://generativelanguage.googleapis.com/v1beta/models/{current_generative_ai_model}:generateContent?key={generative_ai_api_key}"
            
        elif current_generative_ai_type == "openai" or current_generative_ai_type == "openrouter":
            # OpenAI and OpenRouter expect 'messages' array with 'role' and 'content'
            # The history is already in a compatible format.
            
            # Determine correct max tokens parameter name for specific OpenAI models
            max_tokens_param_name = "max_tokens" 
            if current_generative_ai_model.lower() == "o4-mini-2025-04-16" or \
               current_generative_ai_model.lower() == "gpt-4o-mini": 
                max_tokens_param_name = "max_completion_tokens"

            # Check for specific OpenAI models that only support default temperature (1.0)
            if current_generative_ai_type == "openai" and current_generative_ai_model.lower() == "o4-mini-2025-04-16": 
                if temperature_param != 1.0:
                    logger.warning(f"Model {current_generative_ai_model} only supports temperature 1.0. Overriding user input {temperature_param} to 1.0 for API call.")
                    final_temperature_for_api = 1.0 
            
            llm_payload = {
                "model": current_generative_ai_model,
                "messages": llm_chat_history, # Use the prepared history
                "temperature": final_temperature_for_api, # Use the final_temperature_for_api
                max_tokens_param_name: max_output_tokens_param, 
            }
            llm_url = "https://api.openai.com/v1/chat/completions"
            if current_generative_ai_type == "openrouter":
                llm_url = "https://openrouter.ai/api/v1/chat/completions" # OpenRouter specific endpoint
                # Optional: Add OpenRouter specific headers if needed for tracking/analytics
                # llm_headers['HTTP-Referer'] = "http://localhost:5001" # Replace with your app's actual URL
                # llm_headers['X-Title'] = "SampleApp3-Chatbot"

            llm_headers['Authorization'] = f'Bearer {generative_ai_api_key}'

        else:
            logger.error(f"Unsupported LLM type specified in environment variable: '{current_generative_ai_type}'. Key='{current_generative_ai_key_name}', Model='{current_generative_ai_model}'")
            return jsonify({'error': 'Unsupported LLM type configured on the backend.'}), 500

        scrubbed_llm_url = llm_url
        if "key=" in scrubbed_llm_url:
            scrubbed_llm_url = scrubbed_llm_url.split("key=")[0] + "key=****"

        logger.info(f"Calling LLM API for model '{current_generative_ai_model}' (Type: {current_generative_ai_type}) to {scrubbed_llm_url} with T={final_temperature_for_api}, Max={max_output_tokens_param}")
        llm_response = requests.post(llm_url, headers=llm_headers, json=llm_payload, timeout=20)
        llm_response.raise_for_status()

        llm_result = llm_response.json()

        bot_response_text = "Could not parse LLM response."
        response_tokens = 0 
        prompt_tokens_api_response = 0 # Initialize prompt tokens from API usage

        # Parse response based on the determined LLM type and extract tokens
        if current_generative_ai_type == "openai" or current_generative_ai_type == "openrouter":
            if llm_result.get('choices') and llm_result['choices'][0].get('message') and llm_result['choices'][0]['message'].get('content'):
                bot_response_text = llm_result['choices'][0]['message']['content']
            
            # Extract tokens from usage object (OpenAI/OpenRouter standard)
            if llm_result.get('usage'):
                response_tokens = llm_result['usage'].get('completion_tokens', 0)
                # Some OpenRouter models might use 'output_tokens' or similar if completion_tokens is zero
                if response_tokens == 0: 
                     response_tokens = llm_result['usage'].get('output_tokens', 0)
                prompt_tokens_api_response = llm_result['usage'].get('prompt_tokens', 0)

        elif current_generative_ai_type == "gemini":
            if llm_result.get('candidates') and llm_result['candidates'][0].get('content') and llm_result['candidates'][0]['content'].get('parts'):
                bot_response_text = llm_result['candidates'][0]['content']['parts'][0]['text']
            
            # Extract tokens from usageMetadata (Gemini standard)
            if llm_result.get('usageMetadata'):
                prompt_tokens_api_response = llm_result['usageMetadata'].get('prompt_token_count', 0)
                # Gemini's candidates_token_count is the generated output length
                response_tokens = llm_result['usageMetadata'].get('candidates_token_count', 0)
            
            # Fallback to simple estimate if API didn't provide specific counts or structure changed
            if response_tokens == 0 and bot_response_text:
                response_tokens = estimate_tokens_simple(bot_response_text)
            if prompt_tokens_api_response == 0 and user_prompt: # estimate if prompt tokens not available from API
                prompt_tokens_api_response = estimate_tokens_simple(user_prompt)

        else:
            logger.warning(f"Unexpected LLM response structure or missing token info for model type {current_generative_ai_type}: {llm_result}")
            return jsonify({'error': 'Could not parse LLM response due to unexpected model type.'}), 500
        
        # Calculate total tokens (using API-provided prompt tokens if available, else estimated current_prompt_tokens)
        # Note: context_tokens_sum is based on simple estimate on backend
        total_tokens_used = context_tokens_sum + prompt_tokens_api_response + response_tokens

        if bot_response_text != "Could not parse LLM response." and bot_response_text != "Could not parse LLM response due to unexpected model type.":
            logger.info("Successfully received response from LLM.")
            return jsonify({
                'response': bot_response_text,
                'temperature': temperature_param, # Send original requested temperature to frontend
                'maxOutputTokens': max_output_tokens_param, 
                'modelUsed': current_generative_ai_model,
                'promptTokens': prompt_tokens_api_response, # Send API's reported prompt tokens
                'contextTokens': context_tokens_sum,         # Send backend's calculated context tokens
                'responseTokens': response_tokens,           # Send API's reported response tokens
                'totalTokens': total_tokens_used             # Send calculated total tokens
            })
        else:
            logger.warning(f"Unexpected LLM response structure for model {current_generative_ai_model}: {llm_result}")
            return jsonify({'error': 'Could not parse LLM response'}), 500

    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection Error: Could not connect to Generative AI API. Details: {e}")
        return jsonify({'error': f'Failed to communicate with Generative AI API.'}), 500
    except requests.exceptions.Timeout as e:
        logger.error(f"Timeout Error: Request to Generative AI API timed out. Details: {e}")
        return jsonify({'error': f'Failed to communicate with Generative AI API: Request timed out.'}), 500
    except requests.exceptions.RequestException as e:
        status_code = e.response.status_code if e.response is not None else 'N/A'
        response_text = e.response.text if e.response is not None else 'N/A'
        logger.error(f"Error communicating with Generative AI API (Status: {status_code}, Response: {response_text}). Full traceback:\n{traceback.format_exc()}")
        return jsonify({
            'error': f'Failed to communicate with Generative AI API: (HTTP Status {status_code}). Please check the server logs for more details.'
        }), 500
    except json.JSONDecodeError:
        logger.error(f"Error: Could not decode JSON response from Generative AI API. Response was not valid JSON. Raw LLM response text: {llm_response.text}")
        return jsonify({'error': 'Invalid JSON response from LLM API'}), 500
    except Exception as e:
        logger.error(f"An unexpected error occurred during chat generation: {e}. Full traceback:\n{traceback.format_exc()}")
        return jsonify({'error': 'Internal server error during chat generation'}), 500

if __name__ == '__main__':
    logger.info("Starting SampleApp3 Chatbot Backend...")
    logger.info(f"Keystore API Base: {KEYSTORE_API_BASE}")
    logger.info(f"Default Generative AI Model: {DEFAULT_GENERATIVE_AI_MODEL}")
    for opt in LLM_OPTIONS:
        logger.info(f"Available LLM Option: ID={opt['id']}, Model={opt['name']}, Key Name={opt['key_name']}, Type={opt['type']}")
    logger.info(f"LLM Temperature (configured): {DEFAULT_LLM_TEMPERATURE}")
    logger.info(f"LLM Max Output Tokens (configured): {DEFAULT_LLM_MAX_OUTPUT_TOKENS}")
    
    if app.debug:
        app.run(debug=True, host='0.0.0.0', port=5001)
    else:
        logger.info("Flask debug mode is OFF. Expecting Gunicorn to manage the server.")