import sys
from pathlib import Path
from fastapi.routing import APIRoute

# Add project root to sys.path
ROOT_DIR = Path(__file__).parent.parent
sys.path.append(str(ROOT_DIR))

try:
    from backend.server import app
    print("✅ Successfully imported 'app' from 'backend.server'")
    
    print("\n--- Registered Routes in backend.server:app ---")
    found_yolo = False
    for route in app.routes:
        if isinstance(route, APIRoute):
            methods = ", ".join(route.methods)
            print(f"  - {route.path} [{methods}]")
            if "/api/yolo/detect-objects" in route.path:
                found_yolo = True
        else:
            print(f"  - {route.path} [Mount/Other]")
            
    print("-----------------------------------------------")
    
    if found_yolo:
        print("✅ YOLO route found!")
    else:
        print("❌ YOLO route NOT found in backend.server:app")

except ImportError as e:
    print(f"❌ Failed to import backend.server: {e}")
except Exception as e:
    print(f"❌ An unexpected error occurred: {e}")
