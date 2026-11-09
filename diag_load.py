import sys
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).parent
sys.path.append(str(ROOT_DIR))

try:
    from backend.services.project_service import project_service
    print("Attempting to load project 'Calixto Island'...")
    data = project_service.load_project("Calixto Island")
    print(f"Successfully loaded! Found {len(data.get('scenes', {}))} scenes.")
except Exception as e:
    print(f"FAILED to load project: {e}")
    import traceback
    traceback.print_exc()
