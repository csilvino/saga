import sys
import logging
logging.basicConfig(level=logging.INFO)

sys.path.append(r"d:\PythonProject\saga")
from backend.services.animation_service import animation_service

try:
    # Try with a common generic object failure to see if it reaches the genai client initialization
    animation_service.generate_animation_sheet("SAGA", "invalid_id", "test", 3)
except ValueError as ve:
    print(f"VAL_ERR: {ve}")
except Exception as e:
    import traceback
    traceback.print_exc()
