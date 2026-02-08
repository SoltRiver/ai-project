import sys
import os

# Add project root to sys.path
sys.path.append(os.getcwd())

print("Attempting to import fastapi_app...")
try:
    from fastapi_app import app, startup_event
    print("Import successful.")
except Exception as e:
    print(f"Import failed: {e}")
    sys.exit(1)

print("Running startup event...")
try:
    startup_event()
    print("Startup event completed.")
except Exception as e:
    print(f"Startup event failed: {e}")
    sys.exit(1)

print("Verifying DB file...")
if os.path.exists("ai_project.db"):
    print("DB file created.")
else:
    print("DB file NOT created.")
