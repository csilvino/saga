"""
Modelos de dados (dataclasses) para a Saga Engine.

Estas classes representam a estrutura de um projeto de jogo de forma tipada,
facilitando o acesso aos dados carregados do project.json.
"""
import json
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Tuple

# --- Modelos de Geometria e Posição ---

@dataclass
class Size:
    width: int
    height: int

    def to_dict(self):
        return asdict(self)

@dataclass
class Position:
    x: int
    y: int

    def to_dict(self):
        return asdict(self)

@dataclass
class Shape:
    type: str
    points: List[List[int]] = field(default_factory=list)
    radius: Optional[float] = None

    def to_dict(self):
        d = asdict(self)
        # Remove None values for cleaner JSON
        return {k: v for k, v in d.items() if v is not None}

# --- Modelos de Assets ---

@dataclass
class SpriteAsset:
    path: str
    frame_size: Optional[Size] = None
    tags: List[str] = field(default_factory=list)

    def to_dict(self):
        d = asdict(self)
        if self.frame_size:
            d['frame_size'] = self.frame_size.to_dict()
        return {k: v for k, v in d.items() if v is not None and (not isinstance(v, list) or v)} # Remove empty lists

@dataclass
class AudioAsset:
    path: str
    type: str
    volume: float

    def to_dict(self):
        return asdict(self)

@dataclass
class FontAsset:
    path: str
    size: int

    def to_dict(self):
        return asdict(self)

@dataclass
class ItemAsset:
    name: str
    description: str
    path: str

    def to_dict(self):
        return asdict(self)

@dataclass
class Assets:
    sprites: Dict[str, SpriteAsset] = field(default_factory=dict)
    audio: Dict[str, AudioAsset] = field(default_factory=dict)
    fonts: Dict[str, FontAsset] = field(default_factory=dict)
    items: Dict[str, ItemAsset] = field(default_factory=dict)
    raw: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        return {
            'sprites': {k: v.to_dict() for k, v in self.sprites.items()},
            'audio': {k: v.to_dict() for k, v in self.audio.items()},
            'fonts': {k: v.to_dict() for k, v in self.fonts.items()},
            'items': {k: v.to_dict() for k, v in self.items.items()},
            'raw': self.raw
        }

# --- Modelos de Diálogo ---

@dataclass
class DialogChoice:
    text: str
    next: str

    def to_dict(self):
        return asdict(self)

@dataclass
class DialogNode:
    id: str
    type: str
    character: Optional[str] = None
    text: Optional[str] = None
    next: Optional[str] = None
    choices: Optional[List[DialogChoice]] = None

    def to_dict(self):
        d = asdict(self)
        if self.choices:
            d['choices'] = [c.to_dict() for c in self.choices]
        return {k: v for k, v in d.items() if v is not None and (not isinstance(v, list) or v)} # Remove empty lists

@dataclass
class Dialog:
    start_node: str
    nodes: Dict[str, DialogNode] = field(default_factory=dict)

    def to_dict(self):
        return {
            'start_node': self.start_node,
            'nodes': {k: v.to_dict() for k, v in self.nodes.items()}
        }

# --- Modelos de Componentes de Jogo ---

@dataclass
class Action:
    type: str
    params: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)

@dataclass
class Hotspot:
    id: str
    shape: Shape
    action: Action
    name: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    visible: Optional[bool] = None
    enabled: Optional[bool] = None
    z: Optional[int] = None

    def to_dict(self):
        d = asdict(self)
        d['shape'] = self.shape.to_dict()
        d['action'] = self.action.to_dict()
        return {k: v for k, v in d.items() if v is not None and (not isinstance(v, list) or v)}

@dataclass
class GameObject:
    id: str
    type: str
    sprite: str
    position: Position
    properties: Dict[str, Any] = field(default_factory=dict)
    animation_sprites: Optional[List[str]] = field(default_factory=list)
    animation_speed: Optional[float] = 1.0

    def to_dict(self):
        d = asdict(self)
        d['position'] = self.position.to_dict()
        return {k: v for k, v in d.items() if v is not None and (not isinstance(v, dict) or v)} # Remove empty dicts

@dataclass
class Scene:
    id: str
    background: str
    size: Size
    hotspots: List[Hotspot] = field(default_factory=list)
    objects: List[GameObject] = field(default_factory=list)
    name: Optional[str] = None
    layers: List[Any] = field(default_factory=list) # Simplificado, pode ser mais detalhado

    def to_dict(self):
        d = asdict(self)
        d['size'] = self.size.to_dict()
        d['hotspots'] = [h.to_dict() for h in self.hotspots]
        d['objects'] = [o.to_dict() for o in self.objects]
        return {k: v for k, v in d.items() if v is not None and (not isinstance(v, list) or v)}

# --- Modelo Principal do Projeto ---

@dataclass
class Metadata:
    author: str
    description: str
    license: Optional[str] = None

    def to_dict(self):
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None}

@dataclass
class Project:
    name: str
    version: str
    start_scene: str
    navigation_mode: str
    metadata: Metadata
    scenes: Dict[str, Scene]
    assets: Assets
    project_path: str = field(repr=False) # Não incluir no dict de serialização
    dialogs: Dict[str, Dialog] = field(default_factory=dict)
    scripts: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict, project_path: str) -> 'Project':
        """
        Cria uma instância de Project a partir de um dicionário.
        Este método faz a conversão dos dicionários aninhados para as dataclasses correspondentes.
        """
        assets_data = data.get('assets', {})
        assets = Assets(
            sprites={k: SpriteAsset(path=v['path'], frame_size=Size(**v['frame_size']) if 'frame_size' in v else None, tags=v.get('tags', [])) for k, v in assets_data.get('sprites', {}).items()},
            audio={k: AudioAsset(**v) for k, v in assets_data.get('audio', {}).items()},
            fonts={k: FontAsset(**v) for k, v in assets_data.get('fonts', {}).items()},
            items={k: ItemAsset(**v) for k, v in assets_data.get('items', {}).items()},
            raw=assets_data.get('raw', {})
        )

        dialogs_data = data.get('dialogs', {})
        dialogs = {}
        for dialog_id, dialog_data in dialogs_data.items():
            nodes = {}
            for node_id, node_raw_data in dialog_data.get('nodes', {}).items():
                choices = None
                if 'choices' in node_raw_data:
                    choices = [DialogChoice(**choice_data) for choice_data in node_raw_data['choices']]
                nodes[node_id] = DialogNode(
                    id=node_raw_data['id'],
                    type=node_raw_data['type'],
                    character=node_raw_data.get('character'),
                    text=node_raw_data.get('text'),
                    next=node_raw_data.get('next'),
                    choices=choices
                )
            dialogs[dialog_id] = Dialog(start_node=dialog_data['start_node'], nodes=nodes)

        scenes_data = data.get('scenes', {})
        scenes = {}
        for scene_id, scene_raw_data in scenes_data.items():
            scenes[scene_id] = Scene(
                id=scene_raw_data['id'],
                name=scene_raw_data.get('name'),
                background=scene_raw_data['background'],
                size=Size(**scene_raw_data['size']),
                hotspots=[Hotspot(shape=Shape(**h['shape']), action=Action(**h['action']), **{k:v for k,v in h.items() if k not in ['shape', 'action']}) for h in scene_raw_data.get('hotspots', [])],
                objects=[GameObject(position=Position(**o['position']), **{k:v for k,v in o.items() if k != 'position'}) for o in scene_raw_data.get('objects', [])],
                layers=scene_raw_data.get('layers', [])
            )

        metadata = Metadata(**data.get('metadata', {}))

        return cls(
            name=data['name'],
            version=data['version'],
            start_scene=data['start_scene'],
            navigation_mode=data['navigation_mode'],
            metadata=metadata,
            scenes=scenes,
            assets=assets,
            dialogs=dialogs,
            scripts=data.get('scripts', {}),
            project_path=project_path
        )

    def to_dict(self):
        """
        Converte a instância do Projeto e suas dataclasses aninhadas em um dicionário
        pronto para serialização JSON.
        """
        d = {
            'name': self.name,
            'version': self.version,
            'start_scene': self.start_scene,
            'navigation_mode': self.navigation_mode,
            'metadata': self.metadata.to_dict(),
            'scenes': {k: v.to_dict() for k, v in self.scenes.items()},
            'assets': self.assets.to_dict(),
            'dialogs': {k: v.to_dict() for k, v in self.dialogs.items()},
            'scripts': self.scripts
        }
        return {k: v for k, v in d.items() if v is not None and (not isinstance(v, dict) or v) and (not isinstance(v, list) or v)}
