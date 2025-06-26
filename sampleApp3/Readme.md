# **SampleApp3 \- Advanced Multi-LLM Chatbot**

This is a sample applicaiton for the KeyStore Services, an API Key Self-hosted Management Services 


This is SampleApp3, an enhanced chatbot application designed to demonstrate interaction with multiple Large Language Models (LLMs) from different providers, manage conversational context, and provide real-time token usage statistics. It leverages a separate Keystore Service for secure API key management, ensuring sensitive credentials are not hardcoded in the application.


## **Features**

* **Multi-LLM Support:** Seamlessly switch between different LLMs (e.g., Google Gemini, OpenAI models, OpenRouter models like Mistral/DeepSeek) via a dropdown menu.  
* **Conversational Context:** The chatbot maintains a persistent conversation history, sending previous turns to the LLM for coherent dialogue.  
* **Dynamic LLM Parameters:** Adjust temperature and max output tokens directly from the UI, with initial values loaded from environment variables.  
* **Real-time Token Reporting:** Displays token counts for context, current prompt, and the LLM's response for each interaction.  
* **Secure API Key Management:** Integrates with an external Keystore Service to securely fetch API keys at runtime, preventing hardcoding.  
* **Dockerized Deployment:** Easy setup and deployment using Docker Compose.

## **Requirements**

Before you begin, ensure you have the following installed:

* **Docker and Docker Compose:** Essential for running the application in containers.  
  * [Install Docker Engine](https://docs.docker.com/engine/install/)  
  * [Install Docker Compose](https://docs.docker.com/compose/install/)  
* **Python 3.11+:** Although the application runs in Docker, understanding Python is beneficial for development.  
* **Git:** For cloning the repository.  
* **API Keys:**  
  * **Google Gemini API Key:** For gemini-1.5-flash-latest, gemini-1.5-pro-latest, etc. You can get one from [Google AI Studio](https://aistudio.google.com/app/apikey).  
  * **OpenAI API Key:** For gpt-3.5-turbo, gpt-4o-mini, etc. Obtain from [OpenAI Platform](https://platform.openai.com/api-keys).  
  * **OpenRouter API Key:** For models like mistralai/mistral-7b-instruct, deepseek-ai/deepseek-coder, etc. Get one from [OpenRouter.ai](https://openrouter.ai/).

## **Setup Instructions**

### **Prerequisite: Keystore Service**

This application relies on a separate **Keystore Service** (e.g., api-keystore mentioned in previous discussions) to securely retrieve API keys. Ensure your Keystore Service is running and accessible (e.g., at http://localhost:5000 or http://host.docker.internal:5000 if using Docker Desktop).

**Steps to use Keystore:**

1. **Start your Keystore Service.**  
2. **Add your LLM API keys** (Google Gemini, OpenAI, OpenRouter) to the Keystore. Give them meaningful names (e.g., MyGeminiAPIKey, MyOpenAIAPIKey, MyOpenRouterAPIKey).  
3. **Obtain a JWT Token** for your SampleApp3 application from the Keystore. This token will authenticate SampleApp3 when it requests keys from the Keystore.

### **Cloning the Repository**

First, clone this repository (or your project's equivalent directory structure) to your local machine:

git clone \<your-repository-url\>  
cd sampleApp3 \# or your project directory name

### **Environment Configuration (.env)**

Create a .env file in the root directory of your sampleApp3 application (the same directory as docker-compose.yml and app.py). You can use the provided .env-SAMPLE.txt as a template.

**Example .env file:**

\# Environment variables for sampleApp3 (Chatbot)

\# URL of your main Keystore Service  
\# For Docker Desktop on Windows/macOS, 'host.docker.internal' refers to the host machine.  
\# If Keystore is on a different server, use its public IP/domain.  
KEYSTORE\_API\_URL=http://host.docker.internal:5000

\# \!\!\! IMPORTANT: Get a valid JWT Token from your main Keystore app (http://localhost:5000)  
\# \!\!\! Log in as admin, go to Info tab, copy the token, and paste it here.  
\# \!\!\! This token will represent sampleApp3's access identity to your Keystore.  
KEYSTORE\_JWT\_TOKEN=\[ENTER\_YOUR\_JWT\_TOKEN\_FROM\_KEYSTORE\_HERE\]

\# \--- Generative AI Model Configurations \---  
\# Define multiple LLM options by numbering them.  
\# Ensure the KEY\_NAME corresponds to the exact name of the API Key you stored in your Keystore.  
\# GENERATIVE\_AI\_TYPE\_XX: Specify the API provider ('Gemini', 'OpenAI', 'OpenRouter')

\# LLM Option 1  
GENERATIVE\_AI\_MODEL\_01=gemini-1.5-flash-latest  
GENERATIVE\_AI\_KEY\_NAME\_01=MyGeminiAPIKey  
GENERATIVE\_AI\_TYPE\_01=Gemini

\# LLM Option 2 (Example: another Gemini model, check your quotas\!)  
GENERATIVE\_AI\_MODEL\_02=gemini-1.5-pro-latest  
GENERATIVE\_AI\_KEY\_NAME\_02=MyGeminiAPIKey \# Can reuse key if it's the same Google project  
GENERATIVE\_AI\_TYPE\_02=Gemini

\# LLM Option 3  
GENERATIVE\_AI\_MODEL\_03=gpt-3.5-turbo  
GENERATIVE\_AI\_KEY\_NAME\_03=MyOpenAIAPIKey  
GENERATIVE\_AI\_TYPE\_03=OpenAI

\# LLM Option 4 (Example: requires OpenAI Org verification)  
GENERATIVE\_AI\_MODEL\_04=gpt-4o-mini  
GENERATIVE\_AI\_KEY\_NAME\_04=MyOpenAIAPIKey  
GENERATIVE\_AI\_TYPE\_04=OpenAI

\# LLM Option 5 (OpenRouter \- Mistral)  
GENERATIVE\_AI\_MODEL\_05=mistralai/mistral-7b-instruct  
GENERATIVE\_AI\_KEY\_NAME\_05=MyOpenRouterAPIKey  
GENERATIVE\_AI\_TYPE\_05=OpenRouter

\# LLM Option 6 (OpenRouter \- DeepSeek)  
GENERATIVE\_AI\_MODEL\_06=deepseek-ai/deepseek-coder  
GENERATIVE\_AI\_KEY\_NAME\_06=MyOpenRouterAPIKey  
GENERATIVE\_AI\_TYPE\_06=OpenRouter

\# Optional: Default LLM to use if no selection is made or on initial load.  
\# Must match the 'MODEL\_XX' name of one of the options above.  
DEFAULT\_GENERATIVE\_AI\_MODEL=gemini-1.5-flash-latest

\# MODEL LIMITS: Default parameters if not specified by frontend.  
\# These will also be the initial values displayed in the UI.  
LLM\_TEMPERATURE=0.7  
LLM\_MAX\_OUTPUT\_TOKENS=750 \# Adjust as needed for desired response length and cost

**Important Notes for .env:**

* Replace \[ENTER\_YOUR\_JWT\_TOKEN\_FROM\_KEYSTORE\_HERE\] with your actual JWT token from the Keystore.  
* Ensure the KEY\_NAME values (e.g., MyGeminiAPIKey, MyOpenAIAPIKey, MyOpenRouterAPIKey) exactly match the names under which you stored your actual API keys in your Keystore Service.  
* The GENERATIVE\_AI\_MODEL\_XX names must match the exact identifiers provided by the respective LLM providers (e.g., gemini-1.5-flash-latest from Google, gpt-3.5-turbo from OpenAI, mistralai/mistral-7b-instruct from OpenRouter).

### **Building and Running with Docker Compose**

Navigate to the root directory of your sampleApp3 application (where docker-compose.yml is located) and run:

docker compose up \--build \-d

* docker compose up: Starts the services defined in docker-compose.yml.  
* \--build: Forces Docker to rebuild the image, picking up any changes in app.py, index.html, style.css, etc. (Crucial after any code modifications).  
* \-d: Runs the containers in detached mode (in the background).

To view the application logs (useful for debugging):

docker logs \-f sampleapp3-chatbot

To stop and remove the containers:

docker compose down

## **Usage**

Once the Docker containers are running successfully:

1. Open your web browser and navigate to http://localhost:5001.  
2. You should see the chatbot interface.  
3. **Select LLM:** Use the "Select LLM" dropdown to choose your desired model. The options will be populated dynamically from your .env configuration.  
4. **Adjust Parameters:** Modify the "Temp" (temperature) and "Max" (max output tokens) values. These will default to what you set in your .env.  
5. **Type Your Message:** Enter your message in the input field and click "Send" or press Enter.  
6. **Observe Response:** The bot's response will appear, along with:  
   * **Context tokens:** The number of tokens sent in the conversation history (excluding the current prompt).  
   * **Prompt tokens:** The number of tokens in your current message.  
   * **Response tokens:** The number of tokens generated by the LLM.  
   * **Total tokens:** The sum of context, prompt, and response tokens.  
   * **Model Used:** The name of the LLM that generated the response.  
7. **Conversational Context:** Continue the conversation, and you'll see the context token count grow as more turns are added. The application will automatically truncate older messages if the total token count approaches the model's context window limit.

## **Project Structure**

.  
├── .env-SAMPLE.txt             \# Template for environment variables  
├── .gitignore                  \# Files/directories to ignore in Git  
├── app.py                      \# Flask backend application (Python)  
├── docker-compose.yml          \# Docker Compose configuration  
├── dockerfile                  \# Dockerfile for building the Python app image  
├── index.html                  \# Frontend HTML for the chatbot UI  
├── requirements.txt            \# Python dependencies  
└── style.css                   \# CSS styling for the frontend

## **Troubleshooting**

* **Error loading configuration: Failed to load LLM default parameters: NOT FOUND or No LLMs available**:  
  * **Cause:** The backend Flask app could not start properly, or the /llm-defaults or /llm-options endpoints are not accessible.  
  * **Solution:**  
    1. Ensure you have run docker compose up \--build \-d after *every* code change.  
    2. Check docker logs sampleapp3-chatbot for any Python errors (e.g., SyntaxError, NameError). Fix any identified errors in app.py.  
    3. Verify your .env file is named exactly .env and is in the same directory as docker-compose.yml.  
    4. Ensure your KEYSTORE\_API\_URL is correct and your Keystore Service is running.  
* **Error communicating with Generative AI API: (HTTP Status 429\) (Quota Exceeded)**:  
  * **Cause:** You've hit the rate limits or daily quotas for your API key with Google Gemini.  
  * **Solution:** Wait for your quota to reset, or consider enabling billing/upgrading your plan on your Google Cloud Platform project.  
* **Error communicating with Generative AI API: (HTTP Status 404\) (Model Not Found / Organization Verification)**:  
  * **Cause:** For OpenAI models, this often means your OpenAI organization is not verified, or the specific model ID you're trying to use is not available to your account.  
  * **Solution:** Go to [platform.openai.com/settings/organization/general](https://platform.openai.com/settings/organization/general) and verify your organization. Alternatively, switch to a more generally available model like gpt-3.5-turbo in your .env.  
* **Error communicating with Generative AI API: (HTTP Status 400\) (Bad Request \- e.g., Unsupported parameter or Unsupported value)**:  
  * **Cause:** The parameters sent to the LLM API (e.g., temperature, max\_tokens) are not valid for that specific model or provider. This happened with o4-mini-2025-04-16 requiring max\_completion\_tokens and only supporting temperature=1.0.  
  * **Solution:** The app.py code already contains logic to handle these specific cases. Ensure you have the latest app.py version provided and have rebuilt your Docker image. If a new model introduces new parameter quirks, you'll need to extend the app.py logic to accommodate it.  
* **Response tokens always 0**:  
  * **Cause:** The backend failed to correctly extract the completion\_tokens from the LLM's API response.  
  * **Solution:** Ensure you have the latest app.py code, which includes improved logic for extracting usage data from both OpenAI/OpenRouter and Gemini responses. Rebuild and restart.

## **Future Enhancements**

* **More Accurate Token Counting:** Integrate official tokenization libraries (e.g., tiktoken for OpenAI/OpenRouter, Google's client libraries for Gemini's specific tokenizers) on the backend for highly accurate token counts across all models.  
* **Persistent Chat History (Beyond Session):** Implement a database (like Firestore, SQLite, or a simple file) to store chat history so it persists across browser refreshes or application restarts.  
* **User Management/Authentication:** If multiple users will use the app, add authentication to manage individual chat histories and settings.  
* **Streaming Responses:** Implement streaming API calls to display LLM responses word-by-word as they are generated, improving user experience.  
* **System Prompts:** Allow configuration of a system prompt (or "persona") for the chatbot.  
* **Advanced Context Management:** Implement more sophisticated context strategies (e.g., summarization of old turns) to fit more context into smaller windows.  
* **UI Improvements:** Add clear indicators for API errors directly in the chat bubbles, improve markdown rendering robustness, or allow users to clear chat history.