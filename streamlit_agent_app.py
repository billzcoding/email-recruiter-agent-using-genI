# Save this as 'streamlit_agent_app.py'

import streamlit as st
import requests
import os
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from langchain.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_agent

# --- CONFIGURATION ---
API_BASE_URL = "http://127.0.0.1:8001"
SENDER_EMAIL = "your-support@example.com"  # IMPORTANT: CHANGE THIS

st.set_page_config(page_title="LangChain Gemini Agent Demo", layout="wide")
st.title("🤖 Multi-Tool Gemini Agent")
st.caption("Demonstrating intelligent tool selection (FastAPI & Mailtrap)")

# --- TOOL DEFINITIONS ---

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
        return f"ERROR: Failed to connect to API on port 8001. Details: {e}"

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
    smtp_server = os.getenv("MAILTRAP_HOST")
    login = os.getenv("MAILTRAP_LOGIN")
    password = os.getenv("MAILTRAP_PASSWORD")
    port = 587
    
    if not login or not password:
        return "ERROR: Mailtrap credentials are not set (check environment variables)."

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = SENDER_EMAIL
    message["To"] = recipient_email
    message.attach(MIMEText(body, "plain"))

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(smtp_server, port) as server:
            server.starttls(context=context)
            server.login(login, password)
            server.sendmail(SENDER_EMAIL, recipient_email, message.as_string())
            
        return f"SUCCESS: Real email sent to {recipient_email} via Mailtrap. Check your Mailtrap Sandbox inbox."
        
    except smtplib.SMTPException as e:
        return f"ERROR: SMTP failed to send email. Check Mailtrap settings/sender email. Details: {e}"
    except Exception as e:
        return f"ERROR: General error during email sending. Details: {e}"


# --- AGENT INITIALIZATION ---

@st.cache_resource
def setup_agent():
    """Initializes the Gemini model and the Agent once."""
    try:
        # The ChatGoogleGenerativeAI object automatically looks for GEMINI_API_KEY
        model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
    except Exception as e:
        st.error(f"Error initializing Gemini Model. Is GEMINI_API_KEY set? Error: {e}")
        return None

    tools = [get_user_status, send_user_email]
    
    agent = create_agent(
        model, 
        tools=tools,
        system_prompt="You are a helpful customer service agent. Use the appropriate tool(s) to assist the user. If you use a tool, always summarize the tool's result clearly. Be concise and professional."
    )
    return agent

# --- AGENT EXECUTION LOOP ---

def run_agent(question, agent_instance):
    """Executes the agent and streams the steps to the Streamlit interface."""
    with st.spinner("Agent is reasoning and executing steps..."):
        # We use stream for a richer interface experience
        full_response = ""
        # The agent.stream returns the state at each step of the ReAct loop
        for chunk in agent_instance.stream({"messages": [{"role": "user", "content": question}]}, stream_mode="values"):
            
            # Check for messages (the final response or tool call observation)
            if "messages" in chunk and chunk["messages"]:
                latest_message = chunk["messages"][-1]
                
                # If the message is a final answer
                if hasattr(latest_message, 'content') and latest_message.content:
                    full_response = latest_message.content
                
                # If the message is a tool call/observation (intermediate step)
                elif hasattr(latest_message, 'tool_calls') and latest_message.tool_calls:
                    st.info(f"**🤖 Agent Action:** Calling **{latest_message.tool_calls[0]['name']}** with arguments: {latest_message.tool_calls[0]['args']}")
                
                # The final result should always be in the last content chunk,
                # but this catches any intermediate steps not fully captured above
                
        return full_response

# --- STREAMLIT MAIN APP ---

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Setup the agent (runs only once)
agent = setup_agent()

# Handle user input
if agent and (prompt := st.chat_input("Ask the Agent about status (e.g., ID 101) or to send an email.")):
    
    # 1. Display user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Run the agent and display the response
    with st.chat_message("assistant"):
        final_answer = run_agent(prompt, agent)
        st.session_state.messages.append({"role": "assistant", "content": final_answer})
        st.markdown(final_answer)

# Sidebar for Instructions/Credentials
st.sidebar.header("Workshop Instructions")
st.sidebar.markdown(
    """
    This agent uses **Gemini 2.5 Flash** to decide between two tools:
    
    1.  **FastAPI Status:** (Retrieves data from a running API on :8001).
    2.  **Mailtrap Email:** (Sends a real email using SMTP credentials).
    
    ---
    
    ### ⚙️ Prerequisites
    1.  **FastAPI Server:** Must be running on `http://127.0.0.1:8001`.
    2.  **Environment Variables:** Must be set in the terminal you use to launch Streamlit:
        * `export GEMINI_API_KEY="..."`
        * `export MAILTRAP_HOST="..."`
        * `export MAILTRAP_LOGIN="..."`
        * `export MAILTRAP_PASSWORD="..."`
    
    ---
    
    ### 💬 Example Queries
    * `What is the status for ID 102?`
    * `Can you send a notification email to john@test.com with subject 'Alert' and body 'Check the system log.'`
    """
)