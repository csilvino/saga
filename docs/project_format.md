# Formato de Projeto  Saga Engine

Resumo rápido
- Arquivo principal: project.json (siga shared/project_schema.json).
- Estrutura: name, version, start_scene, scenes, assets.
- Scenes: contêm background, layers, hotspots, objects.
- Hotspots: formas (rect/poly/circle) + action (objeto com type/params).

Exemplo mínimo (project.json)
{
  "name": "demo",
  "version": "0.1.0",
  "start_scene": "scene_1",
  "scenes": {
    "scene_1": {
      "id": "scene_1",
      "name": "Sala",
      "background": "bg/room.png",
      "hotspots": [
        {
          "id": "door_1",
          "shape": { "type": "rect", "points": [[100,200],[200,350]] },
          "action": { "type": "go_to_scene", "params": { "scene": "scene_2" } }
        }
      ]
    }
  },
  "assets": {
    "sprites": {
      "hero": { "path": "sprites/hero.png", "frame_size": { "width": 64, "height": 64 } }
    },
    "audio": {
      "bg_music": { "path": "audio/ambience.mp3", "type": "music", "volume": 0.8 }
    },
    "fonts": {
      "main": { "path": "fonts/Inter-Regular.ttf", "size": 16 }
    }
  }
}

Validação
- Ferramenta recomendada: jsonschema (Python) para validar no build/export:
  python -m jsonschema -i project.json shared/project_schema.json
