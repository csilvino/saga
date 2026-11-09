import sys
import os
sys.path.append(os.getcwd())
from backend.main import app

def list_routes():
    print("Listing all registered routes:")
    for route in app.routes:
        if hasattr(route, "path"):
            print(f"{route.methods} {route.path}")
        else:
            print(route)

if __name__ == "__main__":
    list_routes()
