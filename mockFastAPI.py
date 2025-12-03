from fastapi import FastAPI, HTTPException
from typing import Dict, Any

# 1. Initialize the FastAPI application
app = FastAPI(
    title="User Status Mock API",
    description="A simple mock API to return app status for a given user ID."
)

# 2. Mock Data Source (simulates a database)
# In a real application, this would be a database query.
mock_user_statuses: Dict[int, str] = {
    101: "Active",
    102: "Inactive",
    103: "Pending_Approval",
    104: "Suspended",
}

# 3. Define the Endpoint
@app.get("/users/{user_id}/status", response_model=Dict[str, Any])
def get_user_app_status(user_id: int):
    """
    Retrieves the application status for a specific user ID.
    """
    
    # Check if the user_id exists in our mock data
    if user_id not in mock_user_statuses:
        # If the user is not found, raise an HTTP 404 error
        raise HTTPException(
            status_code=404, 
            detail=f"User with ID {user_id} not found."
        )

    # If found, retrieve the status
    status = mock_user_statuses[user_id]
    
    # Return the status in a JSON object
    return {
        "user_id": user_id,
        "app_status": status,
        "message": f"Status retrieved successfully for user {user_id}."
    }

# 4. Run Instructions
# To run this file, you need to install uvicorn and fastapi:
# pip install fastapi uvicorn
#
# Then, execute the following command in your terminal:
# uvicorn filename:app --reload
# (Replace 'filename' with the actual name of your Python file, e.g., main:app)

# 5. Testing the Endpoint
# Once running, you can test it by navigating to:
# - Success: http://127.0.0.1:8000/users/101/status
# - Not Found: http://127.0.0.1:8000/users/999/status
#
# FastAPI also provides interactive documentation (Swagger UI) at:
# http://127.0.0.1:8000/docs