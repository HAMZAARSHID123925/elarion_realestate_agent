"""
Layer 1: WhatsApp Input Channel Launcher.
Primary implementation lives in input_channels/whatsapp_server.py.
"""
from input_channels.whatsapp_server import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
