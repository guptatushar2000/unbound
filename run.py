import uvicorn
import os

# Get port from environment variable or use default
port = int(os.getenv("PORT", 9000))

if __name__ == "__main__":
    # Run app with hot reload in development
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)