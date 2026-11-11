"""
Read-only view of a project for the language and the engine: finds objects and scenes by id,
name or alias, independent of accents and case.

Project layout (project.json): scenes is a dict id -> scene; a scene has objects (a list),
description, exits (direction -> scene id) and ses (its script). An object has id, name, type,
description, properties {portable, hidden, aliases} and ses.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Dict, List, Optional, Tuple


def slug(text) -> str:
    text = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def sound_key(text) -> str:
    """The key of a 'play "..."' sound in project["sounds"]: the description, slugged."""
    return slug(text)[:80]


def obj_description(obj: dict) -> str:
    return (obj.get("description") or (obj.get("properties") or {}).get("description") or "").strip()


def obj_aliases(obj: dict) -> List[str]:
    aliases = (obj.get("properties") or {}).get("aliases") or obj.get("aliases") or []
    if isinstance(aliases, str):
        aliases = [a.strip() for a in aliases.split(",")]
    return [a for a in aliases if a]


def is_scenery(obj: dict) -> bool:
    """Background images and empty placeholders are not things the player can interact with."""
    return obj.get("type") == "background"


class World:
    def __init__(self, project: dict):
        self.project = project
        self.scenes: Dict[str, dict] = project.get("scenes") or {}
        self.objects: Dict[str, dict] = {}
        self.home: Dict[str, str] = {}          # object id -> scene where it starts
        for sid, scene in self.scenes.items():
            for obj in scene.get("objects") or []:
                if obj.get("id") and not is_scenery(obj):
                    self.objects[obj["id"]] = obj
                    self.home[obj["id"]] = sid

    def object_names(self, obj_id: str) -> List[str]:
        obj = self.objects[obj_id]
        return [obj.get("name") or obj_id] + obj_aliases(obj)

    def find_object(self, ref: str, prefer: Optional[List[str]] = None) -> Optional[str]:
        """Object id for an id, a name or an alias; among equal names, those in `prefer` win."""
        if not ref:
            return None
        if ref in self.objects:
            return ref
        key = slug(ref)
        hits = [oid for oid in self.objects
                if key == slug(oid) or any(key == slug(n) for n in self.object_names(oid))]
        if not hits:
            return None
        for oid in hits:
            if prefer and oid in prefer:
                return oid
        return hits[0]

    def find_scene(self, ref: str) -> Optional[str]:
        if not ref:
            return None
        if ref in self.scenes:
            return ref
        key = slug(ref)
        for sid, scene in self.scenes.items():
            if key in (slug(sid), slug(scene.get("name"))):
                return sid
        return None

    def scene_name(self, sid: str) -> str:
        return (self.scenes.get(sid) or {}).get("name") or sid

    def object_name(self, oid: str) -> str:
        return (self.objects.get(oid) or {}).get("name") or oid

    def base_exits(self, sid: str) -> Dict[str, str]:
        exits = (self.scenes.get(sid) or {}).get("exits") or {}
        return {slug(d): t for d, t in exits.items() if t}
