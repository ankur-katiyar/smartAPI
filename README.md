# Smart API Assistant

## Overview
This project is a **Smart API Assistant** that automates the process of interacting with RESTful APIs. It dynamically extracts required fields and headers from an OpenAPI specification, prompts the user for input, and handles API requests and responses. Additionally, it uses a Language Model (LLM) to interpret API responses and guide the user through the process.

## Features
1. **Dynamic Field Extraction**: Extracts required fields and headers from the OpenAPI specification.
2. **User Interaction**: Prompts the user to input values for required fields and headers.
3. **API Invocation**: Sends requests to the API endpoint with the collected payload and headers.
4. **Error Handling**: Detects missing fields in the API response and prompts the user to provide them.
5. **LLM Integration**: Uses an LLM to interpret API responses and provide user-friendly explanations.
6. **Bearer Token Handling**: Extracts a bearer token from the login response and uses it for subsequent API calls.

## How It Works
1. The script fetches the OpenAPI specification from the server.
2. It extracts the required fields, headers, and content type for the specified endpoint.
3. It prompts the user to enter values for the required fields and headers.
4. It sends the initial request to the API endpoint.
5. If the API response indicates missing fields, it prompts the user to enter them and resends the request.
6. It extracts the bearer token from the login response and uses it to make subsequent API calls.
7. It interprets the API responses using the LLM and presents them to the user.

## Requirements
- Python 3.7+
- `requests` library
- `ollama` library

## Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/ankurkatiyar/smartAPI.git
   ```
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Setting Up Ollama
To use the LLM for interpreting API responses, you need to set up Ollama and download the model.

1. **Install Ollama**:
   - Follow the official [Ollama installation guide](https://ollama.ai/docs/installation) for your operating system.

2. **Download the Model**:
   - Run the following command to download the `llama2` model:
     ```bash
     ollama pull llama2
     ```
   - This will download the model and make it available for use.

3. **Start the Ollama Server**:
   - Ensure the Ollama server is running. You can start it with:
     ```bash
     ollama serve
     ```

4. **Verify the Model**:
   - You can test the model by running:
     ```bash
     ollama run llama2 "Hello, world!"
     ```
   - If you see a response, the model is ready to use.

## Usage
Run the script:
```bash
python smart_api.py
```

## License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

