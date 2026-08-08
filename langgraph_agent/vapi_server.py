"""
Layer 1: VAPI Voice Input Channel Launcher.
Primary implementation lives in input_channels/vapi_server.py.
"""
from input_channels.vapi_server import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
