# 📜 SAGA ENGINE SCRIPT (SES) v2.0
### The Complete Game Design Language

> "SES v2.0 expande o escopo para cobrir todo o ciclo de vida do jogo: Sistemas Globais, UI, Áudio e Configurações."

---

## 🌍 GLOBAL GAME SYSTEMS

Para criar um jogo completo, precisamos de lógica que exista *fora* das cenas.

### 1. System Declaration (Global Scope)
Use `system` para definir lógica persistente (ciclo dia/noite, trackeamento de stats globais).

```typescript
system GameLoop {
  state {
    playtime: 0
    is_night: false
    difficulty: "normal"
  }

  on init {
    // Roda uma vez ao iniciar o jogo
    assets.preload(["ui_atlas", "main_theme"])
    settings.resolution = { w: 1920, h: 1080 }
  }

  on update(dt) {
    state.playtime += dt
    
    // Ciclo Dia/Noite simples
    if (state.playtime % 600 > 300) {
      state.is_night = true
    } else {
      state.is_night = false
    }
  }

  on KeyPress(key) {
    if (key == "Escape") {
      ui.open("PauseMenu")
    }
  }
}
```

### 2. Player Global Definition
Defina o jogador independente da cena.

```typescript
global player {
  attributes {
    hp: 100
    max_hp: 100
    xp: 0
  }
  
  inventory {
    capacity: 20
  }
  
  on UnEquip(item) {
    narrate("Você guardou " + item.name)
  }
}
```

---

## 🖥️ UI & HUD SYSTEM

SES v2.0 introduz o conceito de `interface` para criar menus e HUDs.

```typescript
interface HUD {
  layer: "overlay"
  visible: true
  
  elements {
    HealthBar {
      type: "ProgressBar"
      value: () => global.player.hp / global.player.max_hp
      position: { x: 20, y: 20 }
      color: "#FF0000"
    }
    
    InventoryButton {
      type: "Button"
      icon: "bag_icon"
      position: { bottom: 20, right: 20 }
      onClick: () => ui.open("InventoryScreen")
    }
  }
}

interface PauseMenu {
  modal: true  // Pausa o jogo abaixo
  
  elements {
    ResumeBtn {
      type: "Button"
      label: "Continuar"
      onClick: () => ui.close("PauseMenu")
    }
    QuitBtn {
      type: "Button"
      label: "Sair"
      onClick: () => game.quit()
    }
  }
}
```

---

## 🔊 AUDIO MANAGER

Controle avançado de som além de apenas "tocar música".

```typescript
audio {
  channels {
    music: { volume: 0.8, loop: true }
    sfx: { volume: 1.0, polyphony: 10 }
    voice: { volume: 1.0 }
  }
  
  playlists {
    Exploration: ["forest_theme", "wind_ambience"]
    Combat: ["battle_intro", "battle_loop"]
  }
}

// Uso em scripts:
// audio.play("sword_hit", channel: "sfx")
// audio.crossfade("Exploration", duration: 2.0)
```

---

## 🛠️ EXISTING MODULES (Recap v1.1)

### Project Orchestration (AI Control)
- `create_scene(name, check_if_exists)`
- `create_object_in_scene(name, type, sprite)`
- `delete_scene(id)` / `delete_object(id)`
- `move_object(id, src, target)`
- `swap_objects(id_a, id_b)`

### Objects & Scenes (Core)
(Mantém toda a especificação v1.1 de Objects, Characters, Puzzles, etc.)

---

## 🧩 ASSET PIPELINE

Como a IA deve referenciar assets que ainda não existem:

1. **Placeholders**: `sprite: "placeholder:sword"`
2. **Generative Requests**:
   ```typescript
   @generate_audio("Som de espada batendo em metal")
   sound SwordHit
   
   @generate_texture("Textura de madeira velha para UI")
   asset WoodTexture
   ```

---

## 🎯 WORKFLOW COMPLETO (v2.0)

1. **Setup**: Definir `system GameLoop` e `global player`.
2. **UI**: Criar `interface HUD` e `interface MainMenu`.
3. **Content**: Criar Cenas e Objetos (uso normal do v1.1).
4. **Audio**: Configurar canais e playlists.

**Agora o SES cobre 100% das necessidades de um jogo.** 🚀
