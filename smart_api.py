import requests
import ollama

def get_openapi_spec():
    url = "http://localhost:8000/openapi.json"
    response = requests.get(url)
    return response.json()

def extract_required_fields(api_spec, endpoint, method="post"):
    """Extract required fields and their types from OpenAPI spec."""
    try:
        # Extract the content type from the OpenAPI spec
        content_types = api_spec["paths"][endpoint][method]["requestBody"]["content"]
        content_type = next(iter(content_types))  # Get the first content type (e.g., application/x-www-form-urlencoded or application/json)
        schema = content_types[content_type]["schema"]
        required_fields = schema.get("required", [])
        properties = schema.get("properties", {})
        
        field_details = {field: properties[field]["type"] for field in required_fields}
        return field_details, content_type  # Return both field details and content type
    except KeyError:
        return {}, None

# import openai  # Comment out the OpenAI import

def generate_user_questions(field_details):
    """Use LLM to generate questions for the user based on API field requirements."""
    prompt = f"""
    Given the following API request schema:

    {field_details}

    Act as an interactive API assistant. Guide the user step by step by asking for each required field in a conversational way.
    Ask clear and concise questions for each field type (e.g., if it's an integer, specify that).

    Wait for the user's input before moving to the next question.
    """
    response = ollama.generate(
        model="llama2:7b",  # Use the appropriate model name supported by Ollama
        prompt=prompt
    )
    return response["response"]  # Adjust based on Ollama's response structure

def collect_user_inputs(field_details):
    """Ask the user for required inputs dynamically."""
    questions = generate_user_questions(field_details)
    print(questions)

    user_inputs = {}
    for field, field_type in field_details.items():
        user_inputs[field] = input(f"{field} ({field_type}): ")

    return user_inputs

def extract_required_headers(api_spec, endpoint, method="post"):
    """Extract required headers from OpenAPI spec."""
    try:
        headers = api_spec["paths"][endpoint][method].get("parameters", [])
        required_headers = {
            param["name"]: param.get("schema", {}).get("type", "string")
            for param in headers
            if param["in"] == "header" and param.get("required", False)
        }
        return required_headers
    except KeyError:
        return {}

def call_api(api_url, payload, headers=None, content_type="application/json"):
    """Invoke the API with the collected payload and headers."""
    if headers is None:
        headers = {}
    # Set the Content-Type header based on the content type
    headers["Content-Type"] = content_type
    
    # Send the payload in the appropriate format
    if content_type == "application/x-www-form-urlencoded":
        data = "&".join([f"{key}={value}" for key, value in payload.items()])
        response = requests.post(api_url, data=data, headers=headers)
    else:  # Default to JSON
        response = requests.post(api_url, json=payload, headers=headers)
    
    return response.json()

def interpret_response_with_llm(response_data):
    """Interpret the API response using LLM."""
    prompt = f"Explain this API response in simple terms: {response_data}"
    response = ollama.generate(
        model="llama2:7b",  # Use the appropriate model name supported by Ollama
        prompt=prompt
    )
    return response["response"]  # Adjust based on Ollama's response structure

def extract_missing_fields_from_response(api_response):
    """Extract missing fields from the API response."""
    prompt = f"""
    Given the following API response:

    {api_response}

    Extract the list of missing fields that are required by the API. Return only the list of field names as a Python list, formatted exactly like this: ["field1", "field2", "field3"].
    Do not include any additional text or explanations.
    """
    response = ollama.generate(
        model="llama2:7b",  # Use the appropriate model name supported by Ollama
        prompt=prompt
    )
    try:
        # Extract the list of missing fields from the response
        missing_fields = eval(response["response"])  # Convert the string response to a list
        return missing_fields
    except (SyntaxError, NameError):
        # If the response is not a valid Python list, fallback to manual extraction
        missing_fields = []
        for error in api_response.get("detail", []):
            if "missing" in error.get("type", ""):
                field = error.get("loc", [])[-1]  # Extract the field name from the error location
                if field:
                    missing_fields.append(field)
        return missing_fields

def main():
    # Fetch OpenAPI spec
    api_spec = get_openapi_spec()
    
    # Extract required fields and content type from a specific API endpoint
    endpoint = "/api/login"
    method = "post"
    required_fields, content_type = extract_required_fields(api_spec, endpoint, method)
    required_headers = extract_required_headers(api_spec, endpoint, method)

    print("Required Fields:", required_fields)
    print("Content Type:", content_type)
    print("Required Headers:", required_headers)
    
    # Collect user inputs dynamically
    user_payload = collect_user_inputs(required_fields)
    
    # Collect headers dynamically
    headers = {}
    for header, header_type in required_headers.items():
        headers[header] = input(f"{header} ({header_type}): ")
    
    # Call the API with collected payload, headers, and content type
    api_response = call_api(f"http://localhost:8000{endpoint}", user_payload, headers, content_type)
    
    # Check if the API response indicates missing fields
    if "detail" in api_response and any("missing" in error["type"] for error in api_response["detail"]):
        print("API Response indicates missing fields.")
        missing_fields = extract_missing_fields_from_response(api_response)
        print("Missing Fields:", missing_fields)
        
        # Collect missing fields from the user
        for field in missing_fields:
            user_payload[field] = input(f"{field}: ")
        
        # Resend the request with the updated payload
        print("user_payload", user_payload)
        print("headers", headers)
        api_response = call_api(f"http://localhost:8000{endpoint}", user_payload, headers, content_type)

        print("api_response", api_response)
    
    # Let LLM explain the response
    interpreted_response = interpret_response_with_llm(api_response)
    
    print("Final Response:", interpreted_response)

    # Extract the bearer token from the login response
    if "access_token" in api_response:
        bearer_token = api_response["access_token"]
        print("Bearer Token:", bearer_token)
        
        # Call the subsequent API with the bearer token
        jobs_endpoint = "/jobs"
        jobs_headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {bearer_token}"
        }
        jobs_response = requests.get(f"http://localhost:8000{jobs_endpoint}", headers=jobs_headers)
        
        print("jobs_response", jobs_response.json())
        # Interpret the jobs API response
        interpreted_jobs_response = interpret_response_with_llm(jobs_response.json())
        print("Jobs API Response:", interpreted_jobs_response)
    else:
        print("No access token found in the login response.")

if __name__ == "__main__":
    main()

