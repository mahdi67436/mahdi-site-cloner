import os
import signal
import psutil

# Google Chrome-এর সব প্রসেস খুঁজে বের করা
for proc in psutil.process_iter(['name']):
    try:
        if proc.info['name'] and "chrome" in proc.info['name'].lower():
            print(f"Closing: {proc.info['name']} (PID: {proc.pid})")
            proc.terminate()  # প্রসেস বন্ধ করা
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        pass

print("All Google Chrome processes have been terminated.")
