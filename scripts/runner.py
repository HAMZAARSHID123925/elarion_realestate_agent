import subprocess
import sys
import threading
import os

# Enable ANSI colors on Windows
if os.name == 'nt':
    os.system('color')

def kill_port(port):
    """Kill any process occupying the given port (Windows)."""
    try:
        result = subprocess.run(
            f'for /f "tokens=5" %a in (\'netstat -aon ^| findstr :{port}\') do taskkill /F /PID %a',
            shell=True, capture_output=True, text=True
        )
    except Exception:
        pass

def run_and_prefix(cmd, cwd, prefix, color_code):
    process = subprocess.Popen(
        cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, shell=True
    )
    for line in iter(process.stdout.readline, ''):
        if line:
            sys.stdout.write(f"\033[{color_code}m{prefix} |\033[0m {line}")
            sys.stdout.flush()

tasks = [
    ("python langgraph_agent/api.py", ".", "[LANGGRAPH]", "92"), # Green
    # Run from dograh/api so --env-file .env loads DATABASE_URL etc.
    ("python -m uvicorn api.app:app --host 0.0.0.0 --port 8000 --env-file .env", "dograh/api", "[DOGRAH API]", "93"), # Yellow
    ("npm install --legacy-peer-deps && npm run dev", "dograh/ui", "[DOGRAH UI]", "96"), # Cyan
]

threads = []
print("\033[95mStarting Elarion Real Estate Agent Services...\033[0m")
print("\033[90mPress Ctrl+C to stop all services.\033[0m\n")

# Kill any stale processes on ports we need
print("\033[90mClearing ports 8000 and 8001...\033[0m")
kill_port(8000)
kill_port(8001)

for cmd, cwd, prefix, color in tasks:
    t = threading.Thread(target=run_and_prefix, args=(cmd, cwd, prefix, color))
    t.daemon = True
    t.start()
    threads.append(t)

try:
    for t in threads:
        t.join()
except KeyboardInterrupt:
    print("\n\033[91mShutting down all services...\033[0m")
    sys.exit(0)

