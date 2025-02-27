import requests
import ollama
import json

def get_openapi_spec():
    url = "http://localhost:8000/openapi.json"
    response = requests.get(url)
    return response.json()

def extract_required_fields(api_spec, endpoint, method=None):
    """Extract required fields and their types from OpenAPI spec."""
    try:
        # If method is not provided, determine it from the OpenAPI spec
        if method is None:
            available_methods = list(api_spec["paths"][endpoint].keys())
            # Filter out non-HTTP methods (like parameters, summary, etc.)
            http_methods = [m for m in available_methods if m.lower() in ["get", "post", "put", "delete", "patch", "options", "head"]]
            if not http_methods:
                return {}, None, None
            method = http_methods[0]  # Use the first available method
        
        # Check if the endpoint has a requestBody
        if "requestBody" in api_spec["paths"][endpoint][method]:
            content_types = api_spec["paths"][endpoint][method]["requestBody"]["content"]
            content_type = next(iter(content_types))  # Get the first content type
            schema = content_types[content_type]["schema"]
            required_fields = schema.get("required", [])
            properties = schema.get("properties", {})
            
            field_details = {field: properties[field]["type"] for field in required_fields}
            return field_details, content_type, method
        else:
            # No requestBody, so no required fields
            return {}, None, method
    except KeyError:
        return {}, None, method

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

def extract_required_headers(api_spec, endpoint, method=None):
    """Extract required headers from OpenAPI spec."""
    try:
        # If method is not provided, determine it from the OpenAPI spec
        if method is None:
            available_methods = list(api_spec["paths"][endpoint].keys())
            # Filter out non-HTTP methods
            http_methods = [m for m in available_methods if m.lower() in ["get", "post", "put", "delete", "patch", "options", "head"]]
            if not http_methods:
                return {}
            method = http_methods[0]  # Use the first available method
            
        headers = api_spec["paths"][endpoint][method].get("parameters", [])
        required_headers = {
            param["name"]: param.get("schema", {}).get("type", "string")
            for param in headers
            if param["in"] == "header" and param.get("required", False)
        }
        return required_headers
    except KeyError:
        return {}

def call_api(api_url, payload=None, headers=None, content_type="application/json", method="post"):
    """Invoke the API with the collected payload and headers."""
    if headers is None:
        headers = {}
    
    # Set the Content-Type header based on the content type (if payload exists)
    if payload and content_type:
        headers["Content-Type"] = content_type
    
    # Make the appropriate HTTP request based on the method
    method = method.lower()
    if method == "get":
        response = requests.get(api_url, params=payload, headers=headers)
    elif method == "post":
        # Send the payload in the appropriate format
        if content_type == "application/x-www-form-urlencoded":
            data = "&".join([f"{key}={value}" for key, value in payload.items()])
            response = requests.post(api_url, data=data, headers=headers)
        else:  # Default to JSON
            response = requests.post(api_url, json=payload, headers=headers)
    elif method == "put":
        response = requests.put(api_url, json=payload, headers=headers)
    elif method == "delete":
        response = requests.delete(api_url, json=payload, headers=headers)
    elif method == "patch":
        response = requests.patch(api_url, json=payload, headers=headers)
    else:
        raise ValueError(f"Unsupported HTTP method: {method}")
    
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

def extract_job_ids(jobs_response):
    """Extract job IDs from the jobs API response."""
    job_ids = []
    try:
        # Check if the response is a list of jobs
        if isinstance(jobs_response, list):
            for job in jobs_response:
                if "id" in job:
                    job_ids.append(job["id"])
        # Check if the response is a dictionary with a list of jobs
        elif isinstance(jobs_response, dict) and "jobs" in jobs_response:
            for job in jobs_response["jobs"]:
                if "id" in job:
                    job_ids.append(job["id"])
    except (TypeError, KeyError):
        pass
    
    return job_ids

def main():
    # Fetch OpenAPI spec
    api_spec = get_openapi_spec()
    
    # Extract required fields and content type from a specific API endpoint
    endpoint = "/api/login"
    required_fields, content_type, method = extract_required_fields(api_spec, endpoint)
    required_headers = extract_required_headers(api_spec, endpoint, method)

    print(f"Endpoint: {endpoint}")
    print(f"HTTP Method: {method.upper()}")
    print(f"Required Fields: {required_fields}")
    print(f"Content Type: {content_type}")
    print(f"Required Headers: {required_headers}")
    
    # Collect user inputs dynamically (only if there are required fields)
    user_payload = {}
    if required_fields:
        user_payload = collect_user_inputs(required_fields)
    
    # Collect headers dynamically
    headers = {}
    for header, header_type in required_headers.items():
        headers[header] = input(f"{header} ({header_type}): ")
    
    # Call the API with collected payload, headers, and content type
    api_response = call_api(f"http://localhost:8000{endpoint}", user_payload, headers, content_type, method)
    
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
        api_response = call_api(f"http://localhost:8000{endpoint}", user_payload, headers, content_type, method)

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
        # Extract the method for the jobs endpoint
        _, _, jobs_method = extract_required_fields(api_spec, jobs_endpoint)
        jobs_method = jobs_method or "get"  # Default to GET if method not found
        
        jobs_headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {bearer_token}"
        }
        
        # Call the jobs API with the appropriate method
        jobs_response = requests.request(
            method=jobs_method.upper(),
            url=f"http://localhost:8000{jobs_endpoint}",
            headers=jobs_headers
        )
        
        jobs_data = jobs_response.json()
        print(f"jobs_response ({jobs_method.upper()}):", jobs_data)
        
        # Extract job IDs from the response
        job_ids = extract_job_ids(jobs_data)
        
        if job_ids:
            print("\nAvailable Job IDs:")
            for job_id in job_ids:
                print(f"- Job ID: {job_id}")
            
            # Ask the user to select a job to update
            selected_job_id = input("\nEnter the ID of the job you want to update: ")
            
            # Construct the endpoint for updating job status
            job_status_endpoint = f"/jobs/{selected_job_id}/status"
            
            # Extract required fields and method for the job status update endpoint
            status_fields, status_content_type, status_method = extract_required_fields(api_spec, job_status_endpoint)
            
            if not status_fields:
                # If the endpoint is not found in the OpenAPI spec, use default values
                status_fields = {"status": "string"}
                status_content_type = "application/json"
                status_method = "put"
            
            print(f"\nUpdating Job Status for Job ID: {selected_job_id}")
            print(f"HTTP Method: {status_method.upper()}")
            print(f"Required Fields: {status_fields}")
            
            # Collect status update inputs from the user
            status_payload = collect_user_inputs(status_fields)
            
            # Set up headers for the status update request
            status_headers = {
                "accept": "application/json",
                "Authorization": f"Bearer {bearer_token}",
                "Content-Type": status_content_type
            }
            
            # Call the job status update API
            status_response = call_api(
                f"http://localhost:8000{job_status_endpoint}",
                status_payload,
                status_headers,
                status_content_type,
                status_method
            )
            
            print("Status Update Response:", status_response)
            
            # Interpret the status update response
            interpreted_status_response = interpret_response_with_llm(status_response)
            print("Status Update Interpretation:", interpreted_status_response)
        else:
            print("No job IDs found in the response.")
        
        # Interpret the jobs API response
        interpreted_jobs_response = interpret_response_with_llm(jobs_data)
        print("Jobs API Response:", interpreted_jobs_response)
    else:
        print("No access token found in the login response.")

if __name__ == "__main__":
    main()

