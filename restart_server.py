import os
import signal
import subprocess
import time

# Kill all Python and gunicorn processes
try:
    for proc in os.popen("ps aux | grep 'python\|gunicorn' | grep -v grep").read().splitlines():
        pid = int(proc.split()[1])
        try:
            os.kill(pid, signal.SIGKILL)
            print(f"Killed process {pid}")
        except:
            pass
except:
    pass

# Wait for processes to terminate
time.sleep(2)

# Start the server
print("Starting the server...")
subprocess.Popen(["gunicorn", "--bind", "0.0.0.0:5000", "--reuse-port", "--reload", "main:app"])

print("Server restarted!")