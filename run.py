import subprocess
import sys
import os
import time

def main():
    print("===============================================================")
    print("  Universal Multimodal Document Analyzer (Two-Stage Vision)   ")
    print("===============================================================")
    
    # 1. Start Backend FastAPI
    print("[1/2] Launching FastAPI Backend on http://localhost:8000 ...")
    backend_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"],
        cwd=os.path.join(os.path.dirname(__file__), "backend")
    )

    time.sleep(2)

    # 2. Start Frontend Vite
    print("[2/2] Launching Vite Frontend on http://localhost:5173 ...")
    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
    frontend_proc = subprocess.Popen(
        [npm_cmd, "run", "dev"],
        cwd=os.path.join(os.path.dirname(__file__), "frontend")
    )

    print("\n===============================================================")
    print(" Application running successfully:")
    print(" - Web UI:  http://localhost:5173")
    print(" - API Docs: http://localhost:8000/docs")
    print(" - Press Ctrl+C to terminate both servers")
    print("===============================================================\n")

    try:
        backend_proc.wait()
        frontend_proc.wait()
    except KeyboardInterrupt:
        print("\nStopping services...")
        backend_proc.terminate()
        frontend_proc.terminate()

if __name__ == "__main__":
    main()
