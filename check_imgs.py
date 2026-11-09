from PIL import Image
from pathlib import Path

proj_path = Path(r"d:\PythonProject\saga\projects\Calixto Island")
imgs = list(proj_path.glob("**/*.jpg")) + list(proj_path.glob("**/*.png"))

for img_path in imgs:
    try:
        with Image.open(img_path) as img:
            print(f"{img_path.relative_to(proj_path)}: {img.size}")
    except Exception as e:
        print(f"Error {img_path}: {e}")
