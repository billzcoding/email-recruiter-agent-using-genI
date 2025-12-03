# Save this in 'agent_workflow.py'
import requests
# --- NEW IMPORTS FOR EMAIL ---
import os
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
# -----------------------------
from langchain.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_agent
from typing import Literal

# 1. Configuration (Port 8001 is fixed)
API_BASE_URL = "http://127.0.0.1:8001"

# --- Configuration for Mailtrap ---
# You MUST change this sender address to a valid or verified email address
SENDER_EMAIL = "your-support@example.com" 
# ----------------------------------

## Tool 1: Fetch Application Status
@tool
def get_user_status(user_id: int) -> str:
    """
    Retrieves the current application status for a given user ID from the mock API.
    Use this when the user asks for the status of an account.
    The input must be the user_id as an integer (e.g., 101).
    """
    endpoint = f"{API_BASE_URL}/users/{user_id}/status"
    
    try:
        response = requests.get(endpoint)
        response.raise_for_status() 
        data = response.json()
        
        return f"User {user_id} Status: {data.get('app_status', 'Status Unknown')}"
        
    except requests.exceptions.RequestException as e:
        return f"ERROR: Failed to connect to API or retrieve status. Details: {e}"

## Tool 2: Send Email (Mailtrap/SMTP Live Integration)
@tool
def send_user_email(recipient_email: str, subject: str, body: str) -> str:
    """
    Sends a real email to a user for communication using the Mailtrap SMTP service.
    
    Arguments:
    - recipient_email (str): The email address of the user.
    - subject (str): The subject line of the email.
    - body (str): The main content of the email.
    
    ALWAYS use this tool when the user specifically asks to 'send an email' or 'contact' a user.
    """
    # 1. Get credentials from environment variables
    smtp_server = os.getenv("MAILTRAP_HOST")
    login = os.getenv("MAILTRAP_LOGIN")
    password = os.getenv("MAILTRAP_PASSWORD")
    port = 587 # Standard port for TLS/STARTTLS
    
    # Check for missing credentials
    if not login or not password:
        return "ERROR: Mailtrap credentials (MAILTRAP_HOST/LOGIN/PASSWORD) are not set in environment variables."

    # 2. Construct the message
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = SENDER_EMAIL
    message["To"] = recipient_email
    message.attach(MIMEText(body, "plain"))

    # 3. Send the email using smtplib
    try:
        # Create a secure SSL context
        context = ssl.create_default_context()
        
        with smtplib.SMTP(smtp_server, port) as server:
            server.starttls(context=context) # Secure the connection
            server.login(login, password)   # Authenticate
            server.sendmail(SENDER_EMAIL, recipient_email, message.as_string()) # Send
            
        # Success message that goes back to the Agent as the Observation
        return f"SUCCESS: Real email sent to {recipient_email} with subject '{subject}' via Mailtrap. Check your Mailtrap Sandbox inbox."
        
    except smtplib.SMTPException as e:
        # SMTP errors indicate issues with credentials, host, or security settings
        return f"ERROR: SMTP failed to send email. Check Mailtrap credentials, SENDER_EMAIL, and network. Details: {e}"
    except Exception as e:
        return f"ERROR: General error during email sending. Details: {e}"


# 3. Initialize Model and Tools
model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
tools = [get_user_status, send_user_email]

# 4. Create the Agent
agent = create_agent(
    model, 
    tools=tools,
    system_prompt="You are a helpful customer service agent. Use the appropriate tool(s) to assist the user. Be concise and professional."
)

# 5. Invoke the Agent (Test Cases)
print("\n--- Test Case 1: Tool Selection (Status Check) ---")
status_question = "What is the application status for the account with ID 101?"
result_1 = agent.invoke(
    {"messages": [{"role": "user", "content": status_question}]}
)
print(f"Q1: {status_question}")
print(f"A1: {result_1['messages'][-1].content}")

print("\n--- Test Case 2: Tool Selection (Email Send) ---")
email_request = "Please send a quick email to bill@example.com with the subject 'Status Update' and body 'Your request has been processed.'"
result_2 = agent.invoke(
    {"messages": [{"role": "user", "content": email_request}]}
)
print(f"Q2: {email_request}")
print(f"A2: {result_2['messages'][-1].content}")