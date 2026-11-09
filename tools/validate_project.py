# Simple JSON Schema validator for Saga projects
import json
import sys
from pathlib import Path

try:
    import jsonschema
except Exception:
    print("jsonschema não instalado. Rode: pip install jsonschema")
    sys.exit(2)


def validate_file(project_path: Path, schema_path: Path) -> bool:
    # abrir com utf-8-sig para ignorar BOM se existir
    with project_path.open("r", encoding="utf-8-sig") as f:
        data = json.load(f)
    with schema_path.open("r", encoding="utf-8-sig") as f:
        schema = json.load(f)
    try:
        jsonschema.validate(instance=data, schema=schema)
        print(f"[OK] {project_path}")
        return True
    except jsonschema.ValidationError as ve:
        loc = ".".join(map(str, ve.path)) if ve.path else "<root>"
        print(f"[INVALID] {project_path} -> {ve.message} (at {loc})")
        return False
    except Exception as e:
        print(f"[ERROR] {project_path} -> {e}")
        return False


def main(args):
    if len(args) < 2:
        print("Uso: validate_project.py <project.json|projects_dir> [schema_path]")
        return 2
    target = Path(args[1])
    schema = Path(args[2]) if len(args) > 2 else Path("shared/project_schema.json")
    if not schema.exists():
        print(f"Schema não encontrado: {schema}")
        return 2
    failures = 0
    if target.is_dir():
        for p in sorted(target.rglob("*.json")):
            ok = validate_file(p, schema)
            if not ok:
                failures += 1
    elif target.is_file():
        ok = validate_file(target, schema)
        if not ok:
            failures += 1
    else:
        print(f"Alvo inválido: {target}")
        return 2
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
