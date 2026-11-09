# 📚 SES COMPLETE LIBRARY v2.0
## The Ultimate Game Director's Reference

> *"Todo comando, toda possibilidade, toda lógica de jogo em um só lugar."*

---

# 🎭 PARTE 1: ENTIDADES BASE

## 1.1 SCENE (Cena)

```typescript
scene SceneID {
  // METADADOS
  meta {
    name: string                    // "Sala Principal"
    description: string             // Descrição narrativa
    type: SceneType                 // interior | exterior | abstract
    tags: string[]                  // ["escuro", "misterioso", "puzzle"]
  }
  
  // VISUAL
  visual {
    background: AssetPath           // "backgrounds/sala.png"
    lighting: LightingMode          // day | night | dim | bright | custom
    weather?: WeatherType           // sunny | rainy | snowy | foggy
    particles?: ParticleEffect[]    // neve, chuva, poeira
    filters?: ImageFilter[]         // sepia, blur, contrast
  }
  
  // AUDIO
  audio {
    music?: MusicTrack {
      file: AssetPath
      loop: boolean
      volume: 0..1
      fadeIn?: milliseconds
      fadeOut?: milliseconds
    }
    ambient?: SoundEffect[] {
      file: AssetPath
      loop: boolean
      volume: 0..1
      spatial?: Position           // Som posicional
    }
  }
  
  // NAVEGAÇÃO
  navigation {
    exits: {
      [Direction]: Exit {
        to: SceneID
        condition?: () => boolean  // Porta trancada?
        transition?: TransitionType // fade | slide | instant
        onExit?: () => void
      }
    }
    mapPosition?: Vector2         // Para mapa mundial
    visitCount: number            // Quantas vezes visitou
  }
  
  // ESTADO
  state {
    isLocked: boolean
    isDiscovered: boolean
    weather: WeatherState
    timeOfDay: TimeOfDay
    [customKey: string]: any      // Estado customizado
  }
  
  // POPULAÇÃO
  entities: {
    objects: GameObject[]
    characters: Character[]
    items: Item[]
    hotspots: Hotspot[]
  }
  
  // EVENTOS DE CICLO DE VIDA
  lifecycle {
    onFirstEnter?: () => void     // Primeira vez
    onEnter?: () => void          // Toda vez
    onExit?: () => void
    onUpdate?: (delta: number) => void  // A cada frame
    onLongStay?: () => void       // Após X segundos
  }
  
  // TRIGGERS CONDICIONAIS
  triggers: Trigger[] {
    condition: () => boolean
    action: () => void
    once: boolean                 // Dispara só uma vez?
  }
  
  // PUZZLE DA CENA
  puzzle?: {
    type: PuzzleType
    state: PuzzleState
    solution: any
    hints: string[]
    onSolve: () => void
    onFail?: () => void
  }
}
```

### **Scene Shortcuts (Atalhos)**

```typescript
// Criação rápida
scene SimpleRoom {
  name: "Quarto Simples"
  background: "room.png"
  
  on enter {
    narrate("Você entra no quarto.")
  }
}

// Cena com puzzle
scene LockedDoor {
  puzzle: CodePuzzle {
    code: "1842"
    onSolve {
      unlock(Door)
      goToScene("NextRoom")
    }
  }
}
```

---

## 1.2 OBJECT (Objeto de Cena)

```typescript
object ObjectID {
  // IDENTIDADE
  identity {
    name: string
    description: string
    type: ObjectType              // decoration | interactive | collectible | npc
    tags: string[]
  }
  
  // VISUAL
  visual {
    sprite: AssetPath | SpriteSheet
    position: Vector2
    size: Vector2
    rotation: degrees
    scale: Vector2
    zIndex: number                // Camada de profundidade
    opacity: 0..1
    visible: boolean
    
    // Animações
    animations?: {
      [stateName: string]: Animation {
        frames: AssetPath[]
        fps: number
        loop: boolean
      }
    }
    currentAnimation?: string
    
    // Efeitos visuais
    glow?: boolean
    shadow?: boolean
    highlight?: boolean
  }
  
  // FÍSICA (opcional)
  physics? {
    mass: number
    velocity: Vector2
    gravity: boolean
    collision: CollisionShape      // box | circle | polygon
    solid: boolean
  }
  
  // INTERAÇÃO
  interaction {
    interactable: boolean
    verbs: Verb[]                  // examine | take | use | open | close
    cursor: CursorType             // default | pointer | grab | look
    hotspot: Rectangle             // Área clicável
    range?: number                 // Distância máxima para interagir
  }
  
  // ESTADO
  state: {
    [key: string]: any             // Estado customizado
  }
  
  // INVENTÁRIO (se for container)
  inventory?: {
    items: ItemID[]
    capacity: number
    locked: boolean
    key?: ItemID
  }
  
  // EVENTOS
  on click { }
  on hover { }
  on examine { }
  on use { }
  on useWith(item: Item) { }
  on take { }
  on drop { }
  on damage(amount: number) { }
  on destroy { }
  
  // CONDIÇÕES
  when condition {
    // Executa quando condição é true
  }
  
  // TIMER
  every duration {
    // Executa periodicamente
  }
}
```

### **Object Templates (Pré-configurados)**

```typescript
// Porta
object Door extends DoorTemplate {
  state: "open" | "closed" | "locked"
  key?: ItemID
  leadsTo: SceneID
  
  on click {
    if (state == "locked") {
      if (player.has(key)) {
        state = "open"
        narrate("Você destrava a porta.")
      } else {
        narrate("A porta está trancada.")
      }
    } else if (state == "closed") {
      state = "open"
      playSound("door_open.wav")
    } else {
      goToScene(leadsTo)
    }
  }
}

// Container (Baú, Gaveta)
object Chest extends ContainerTemplate {
  locked: boolean
  contents: ItemID[]
  
  on click {
    if (locked) {
      narrate("Está trancado.")
    } else {
      openInventoryUI(contents)
    }
  }
}

// Objeto Decorativo
object Painting extends DecorationTemplate {
  on examine {
    narrate(description)
  }
}

// Objeto Destrutível
object Vase extends DestructibleTemplate {
  health: 1
  
  on click {
    destroy()
    playSound("glass_break.wav")
    dropItem("coin")
  }
}
```

---

## 1.3 ITEM (Item de Inventário)

```typescript
item ItemID {
  // IDENTIDADE
  identity {
    name: string
    description: string
    category: ItemCategory         // weapon | key | consumable | quest
    tags: string[]
    rarity: Rarity                 // common | uncommon | rare | legendary
  }
  
  // VISUAL
  visual {
    icon: AssetPath
    sprite?: AssetPath             // Para quando no mundo
    color?: Color                  // Borda/destaque
  }
  
  // PROPRIEDADES
  properties {
    stackable: boolean
    maxStack: number
    weight: number
    value: number                  // Preço/valor
    durability?: number            // Se degrada
    consumable: boolean
  }
  
  // ATRIBUTOS (para RPG)
  attributes? {
    damage?: number
    defense?: number
    healing?: number
    mana?: number
    speed?: number
    [stat: string]: number
  }
  
  // USO
  usage {
    usableInInventory: boolean
    usableOnObjects: boolean
    usableOnCharacters: boolean
    consumeOnUse: boolean
    cooldown?: milliseconds
  }
  
  // EVENTOS
  on collect {
    playSound("item_get.wav")
    narrate(`Você obteve: ${name}`)
  }
  
  on use {
    if (consumable) {
      player.health += healing
      remove from inventory
    }
  }
  
  on examine {
    showDetailedInfo(this)
  }
  
  on useOn(target: Object | Character) {
    // Lógica de uso
  }
  
  on combine(other: Item) {
    match (this, other) {
      case (Key, Lock): unlock()
      case (Potion, Bottle): createItem(FilledBottle)
    }
  }
  
  on drop {
    createObjectInScene(this.sprite, player.position)
  }
}
```

### **Item Templates**

```typescript
// Chave
item BronzeKey extends KeyTemplate {
  unlocks: ["door_main", "chest_library"]
}

// Consumível
item HealthPotion extends ConsumableTemplate {
  healing: 50
  on use {
    player.health += healing
    playSound("drink.wav")
    remove from inventory
  }
}

// Arma
item Sword extends WeaponTemplate {
  damage: 25
  durability: 100
  range: 1.5
}

// Quest Item
item MysteriousLetter extends QuestItemTemplate {
  questID: "mystery_of_manor"
  canDrop: false  // Não pode ser descartado
}

// Combinável
item WoodPlank {
  on combine with Nails {
    if (player.has("hammer")) {
      create("wooden_board")
      narrate("Você criou uma tábua reforçada!")
    }
  }
}
```

---

## 1.4 CHARACTER (Personagem/NPC)

```typescript
character CharacterID {
  // IDENTIDADE
  identity {
    name: string
    title?: string                 // "O Bibliotecário"
    description: string
    age?: number
    gender?: string
    species?: string               // human | elf | robot
  }
  
  // VISUAL
  visual {
    sprite: AssetPath | SpriteSheet
    portrait?: AssetPath           // Para diálogos
    position: Vector2
    scale: number
    facing: Direction
    
    // Animações
    animations: {
      idle: Animation
      walk: Animation
      talk: Animation
      [emotion: string]: Animation  // happy, sad, angry
    }
  }
  
  // ATRIBUTOS (para RPG)
  attributes? {
    health: number
    maxHealth: number
    mana?: number
    strength?: number
    intelligence?: number
    charisma?: number
    [stat: string]: number
  }
  
  // INVENTÁRIO
  inventory?: {
    items: ItemID[]
    gold?: number
  }
  
  // ESTADO MENTAL/EMOCIONAL
  mental {
    mood: Mood                     // happy | sad | angry | neutral | scared
    relationship: {
      [characterID: string]: number  // -100 (inimigo) a +100 (amigo)
    }
    memory: {
      [flagID: string]: any        // Lembra de eventos
    }
  }
  
  // COMPORTAMENTO
  behavior {
    ai?: AIType                    // passive | patrol | follow | hostile
    schedule?: Schedule[] {
      time: TimeOfDay
      location: SceneID
      action: string
    }
    personality: Personality {
      traits: string[]             // ["nervoso", "gentil", "teimoso"]
      quirks: string[]
    }
  }
  
  // DIÁLOGO
  dialogue {
    defaultTree: DialogueTreeID
    trees: {
      [treeID: string]: DialogueTree
    }
    voice?: VoiceType
  }
  
  // COMÉRCIO (se for mercador)
  shop? {
    buys: ItemCategory[]
    sells: ItemID[]
    priceMultiplier: number        // 1.0 = preço normal
    currency: string
  }
  
  // QUEST (se dá quests)
  quests? {
    available: QuestID[]
    active: QuestID[]
    completed: QuestID[]
  }
  
  // COMBATE (se for inimigo)
  combat? {
    hostile: boolean
    attackDamage: number
    attackRange: number
    attackSpeed: milliseconds
    loot: LootTable
  }
  
  // EVENTOS
  on click {
    startDialogue(defaultTree)
  }
  
  on talk {
    startConversation()
  }
  
  on attack {
    enterCombat()
  }
  
  on death {
    dropLoot()
    updateQuests()
  }
  
  on giveMoney(amount: number) {
    relationship[player] += amount / 10
  }
  
  on giveItem(item: ItemID) {
    if (wants(item)) {
      relationship[player] += 20
      narrate("${name} agradece!")
    }
  }
}
```

---

## 1.5 HOTSPOT (Área Interativa Invisível)

```typescript
hotspot HotspotID {
  // ÁREA
  area: Rectangle | Circle | Polygon
  
  // TIPO
  type: HotspotType               // trigger | teleport | camera | cutscene
  
  // ATIVAÇÃO
  activation {
    trigger: TriggerType          // enter | exit | stay | click
    condition?: () => boolean     // Só ativa se...
    once: boolean                 // Desativa após primeira vez?
    cooldown?: milliseconds
  }
  
  // AÇÃO
  on activate {
    // O que acontece
  }
  
  on enter {
    // Quando player entra na área
  }
  
  on exit {
    // Quando player sai da área
  }
}
```

### **Hotspot Examples**

```typescript
// Teleporte
hotspot SecretPassage {
  area: rect(100, 100, 50, 50)
  
  on enter {
    if (player.has("secret_key")) {
      goToScene("SecretRoom")
    }
  }
}

// Cutscene Trigger
hotspot BossCutscene {
  area: rect(400, 200, 100, 50)
  once: true
  
  on enter {
    playCutscene("boss_appears")
  }
}

// Zona de Dano
hotspot LavaZone {
  area: circle(300, 400, 100)
  
  every 1000 {  // A cada segundo
    if (playerInArea()) {
      player.health -= 10
      playSound("sizzle.wav")
    }
  }
}
```

---

# 🎮 PARTE 2: SISTEMAS DE JOGO

## 2.1 PLAYER (Jogador)

```typescript
player {
  // ATRIBUTOS
  attributes {
    health: number
    maxHealth: number
    mana?: number
    stamina?: number
    level?: number
    experience?: number
  }
  
  // INVENTÁRIO
  inventory {
    items: Item[]
    capacity: number
    gold: number
    
    methods {
      add(item: Item): boolean
      remove(itemID: ItemID): boolean
      has(itemID: ItemID): boolean
      count(itemID?: ItemID): number
      isFull(): boolean
    }
  }
  
  // POSIÇÃO
  position: Vector2
  scene: SceneID
  facing: Direction
  
  // ESTADO
  state {
    isMoving: boolean
    isInDialogue: boolean
    isInCombat: boolean
    isInCutscene: boolean
    canMove: boolean
    canInteract: boolean
  }
  
  // PROGRESSO
  progress {
    scenesVisited: SceneID[]
    itemsCollected: ItemID[]
    npcsMetcount: number
    questsCompleted: QuestID[]
    achievements: AchievementID[]
    playTime: milliseconds
  }
  
  // MÉTODOS
  methods {
    moveTo(position: Vector2)
    lookAt(direction: Direction)
    say(text: string)
    think(text: string)
    emote(emotion: string)
  }
}
```

---

## 2.2 DIALOGUE SYSTEM

```typescript
dialogue DialogueID {
  // METADADOS
  meta {
    title: string
    description?: string
    participants: CharacterID[]
  }
  
  // INÍCIO
  start: NodeID
  
  // NODES (Nós de Diálogo)
  nodes: {
    [nodeID: string]: DialogueNode {
      speaker: CharacterID | "narrator"
      text: string | () => string  // Texto dinâmico
      emotion?: EmotionType
      voice?: AudioClip
      animation?: AnimationID
      
      // Condições
      condition?: () => boolean    // Mostra se true
      
      // Efeitos colaterais
      onEnter?: () => void
      onExit?: () => void
      
      // Próximo
      next: NodeID | Choice[] | "end"
    }
  }
  
  // ESCOLHAS
  choices: {
    [choiceID: string]: Choice {
      text: string
      condition?: () => boolean    // Disponível se true
      icon?: string
      color?: Color
      
      // Consequências
      onSelect?: () => void
      effects?: Effect[]
      
      // Navegação
      next: NodeID
    }
  }
  
  // ESTADO LOCAL
  state: {
    [key: string]: any
  }
  
  // FINAL
  onComplete?: () => void
}
```

### **Dialogue Templates**

```typescript
// Diálogo Simples
dialogue GreetingShopkeeper {
  start: "intro"
  
  nodes {
    intro {
      speaker: "Shopkeeper"
      text: "Bem-vindo! Quer ver minhas mercadorias?"
      
      next: [
        choice yesChoice: "Sim, por favor" -> "show_shop"
        choice noChoice: "Não, obrigado" -> "goodbye"
      ]
    }
    
    show_shop {
      speaker: "Shopkeeper"
      text: "Aqui está tudo que tenho!"
      onEnter { openShop("shopkeeper_1") }
      next: "end"
    }
    
    goodbye {
      speaker: "Shopkeeper"
      text: "Volte sempre!"
      next: "end"
    }
  }
}

// Diálogo com Condições
dialogue LibrarianQuest {
  start: "greeting"
  
  nodes {
    greeting {
      speaker: "Librarian"
      text: when flags.met_before {
        "Ah, você de novo."
      } otherwise {
        "Olá, primeiro dia aqui?"
      }
      
      next: [
        choice ask_book: "Procuro um livro..." -> "quest_start"
        choice leave: "Até logo" -> "end"
      ]
    }
    
    quest_start {
      speaker: "Librarian"
      text: "Hmm, esse livro está na seção restrita..."
      
      condition: () => !flags.has_library_key
      
      onEnter {
        startQuest("find_library_key")
      }
      
      next: "end"
    }
  }
}

// Diálogo com Skill Checks
dialogue PersuadeCaptain {
  nodes {
    persuasion_attempt {
      speaker: "Player"
      text: "[Persuasão] Deixe-me passar, é urgente!"
      
      condition: () => player.attributes.charisma >= 5
      
      onSelect {
        if (randomChance(0.7)) {  // 70% chance
          goto("success")
        } else {
          goto("failure")
        }
      }
    }
    
    success {
      speaker: "Captain"
      text: "Muito bem... mas seja rápido."
      onEnter { unlock("gate") }
      next: "end"
    }
    
    failure {
      speaker: "Captain"
      text: "Não cai nessa, não."
      next: "end"
    }
  }
}
```

---

## 2.3 QUEST SYSTEM

```typescript
quest QuestID {
  // METADADOS
  meta {
    title: string
    description: string
    category: QuestCategory        // main | side | daily | hidden
    difficulty: Difficulty
    recommendedLevel?: number
  }
  
  // GIVER (quem dá a quest)
  giver: CharacterID
  
  // OBJETIVOS
  objectives: Objective[] {
    id: string
    description: string
    type: ObjectiveType            // collect | kill | talk | explore | craft
    target: string                 // O que fazer
    current: number
    required: number
    optional: boolean
    
    onComplete?: () => void
  }
  
  // ESTADO
  state: QuestState                // inactive | active | completed | failed
  
  // RECOMPENSAS
  rewards {
    experience?: number
    gold?: number
    items?: ItemID[]
    reputation?: {
      [faction: string]: number
    }
    unlocks?: string[]             // Desbloqueia novas áreas/features
  }
  
  // CONDIÇÕES
  requirements? {
    level?: number
    items?: ItemID[]
    completedQuests?: QuestID[]
    flags?: FlagCondition[]
  }
  
  // FALHA
  failConditions? {
    timeLimit?: milliseconds
    onCharacterDeath?: CharacterID
    onItemLost?: ItemID
  }
  
  // ETAPAS
  stages: Stage[] {
    id: string
    description: string
    onStart?: () => void
    onComplete?: () => void
  }
  currentStage: number
  
  // EVENTOS
  on start {
    narrate(`Nova Quest: ${title}`)
    showQuestLog()
  }
  
  on objectiveComplete(obj: Objective) {
    playSound("objective_complete.wav")
  }
  
  on complete {
    giveRewards()
    playSound("quest_complete.wav")
    narrate("Quest Completa!")
  }
  
  on fail {
    narrate("Quest Falhada.")
  }
}
```

### **Quest Templates**

```typescript
// Quest de Coleta
quest FetchQuest {
  title: "Ingredientes do Alquimista"
  
  objectives: [
    {
      type: "collect"
      target: "herb_moonflower"
      required: 3
    },
    {
      type: "collect"
      target: "crystal_shard"
      required: 1
    }
  ]
  
  on complete {
    giver.giveItem("health_elixir")
    player.experience += 100
  }
}

// Quest de Investigação
quest MysteryQuest {
  title: "O Mistério da Mansão"
  
  stages: [
    {
      description: "Examine a cena do crime"
      onComplete {
        flags.found_clue_1 = true
      }
    },
    {
      description: "Interrogue as testemunhas"
      objectives: [
        { type: "talk", target: "butler" },
        { type: "talk", target: "maid" }
      ]
    },
    {
      description: "Confronte o culpado"
      onComplete {
        startDialogue("reveal_culprit")
      }
    }
  ]
}

// Quest com Timer
quest TimedRescue {
  title: "Resgate Urgente"
  
  failConditions {
    timeLimit: 300000  // 5 minutos
  }
  
  on fail {
    npc("captive").die()
    narrate("Você não conseguiu a tempo...")
  }
}
```

---

## 2.4 PUZZLE SYSTEM

```typescript
puzzle PuzzleID {
  // TIPO
  type: PuzzleType                 // code | sequence | logic | inventory | riddle
  
  // DIFICULDADE
  difficulty: Difficulty
  
  // SOLUÇÃO
  solution: any
  
  // ESTADO
  state {
    attempts: number
    maxAttempts?: number
    isSolved: boolean
  }
  
  // HINTS
  hints: Hint[] {
    text: string
    condition: () => boolean       // Quando disponibilizar
  }
  
  // TENTATIVA
  on attempt(answer: any) {
    state.attempts++
    
    if (answer == solution) {
      solve()
    } else {
      if (maxAttempts && attempts >= maxAttempts) {
        fail()
      } else {
        provideFeedback(answer)
      }
    }
  }
  
  // SUCESSO
  on solve {
    state.isSolved = true
    playSound("puzzle_solve.wav")
    giveReward()
  }
  
  // FALHA
  on fail {
    lockPuzzle()
    triggerConsequence()
  }
}
```

### **Puzzle Types**

```typescript
// Puzzle de Código
puzzle SafeCode {
  type: "code"
  solution: "1842"
  maxAttempts: 3
  
  hints: [
    { text: "O ano está escrito no quadro", condition: () => examined("painting") },
    { text: "Olhe a data no livro", condition: () => attempts >= 2 }
  ]
  
  on solve {
    open("safe")
    player.inventory.add("golden_key")
  }
  
  on fail {
    triggerAlarm()
  }
}

// Puzzle de Sequência
puzzle PianoMelody {
  type: "sequence"
  solution: ["C", "E", "G", "C"]
  
  on attempt(notes: string[]) {
    if (notes == solution) {
      solve()
    } else {
      playSound("wrong_note.wav")
      narrate("Não foi dessa vez...")
    }
  }
  
  on solve {
    openSecretDoor()
  }
}

// Puzzle de Inventário
puzzle AlchemyPuzzle {
  type: "inventory"
  solution: {
    ingredients: ["herb", "crystal", "water"],
    order: "specific"
  }
  
  on attempt(items: ItemID[]) {
    if (correctCombination(items)) {
      createItem("magic_potion")
      solve()
    }
  }
}

// Puzzle de Lógica
puzzle ChessPuzzle {
  type: "logic"
  board: ChessBoard
  
  solution: Move[]
  
  on attempt(move: Move) {
    if (isCorrectMove(move)) {
      if (allMovesComplete()) {
        solve()
      } else {
        narrate("Correto! Continue...")
      }
    } else {
      reset()
      narrate("Movimento errado. Tente de novo.")
    }
  }
}
```

---

# 🎨 PARTE 3: SISTEMAS VISUAIS

## 3.1 CAMERA

```typescript
camera {
  // POSIÇÃO
  position: Vector2
  zoom: number
  rotation: degrees
  
  // LIMITES
  bounds?: Rectangle
  
  // SEGUIR
  follow(target: Entity, smoothness?: number)
  stopFollow()
  
  // MOVIMENTO
  moveTo(position: Vector2, duration?: milliseconds)
  shake(intensity: number, duration: milliseconds)
  zoom(level: number, duration?: milliseconds)
  
  // EFEITOS
  fadeOut(duration: milliseconds, color?: Color)
  fadeIn(duration: milliseconds)
  flash(color: Color, duration: milliseconds)
}
```

---

## 3.2 ANIMATION

```typescript
animation AnimationID {
  // FRAMES
  frames: AssetPath[]
  fps: number
  loop: boolean
  
  // CONTROLE
  play()
  pause()
  stop()
  reset()
  
  // EVENTOS
  onComplete?: () => void
  onLoop?: () => void
  onFrame?: (frame: number) => void
}

// Tweens (Animação Procedural)
tween {
  target: Entity
  property: string
  from: any
  to: any
  duration: milliseconds
  easing: EasingType            // linear | easeIn | easeOut | bounce
  
  onUpdate?: (value: any) => void
  onComplete?: () => void
}
```

---

## 3.3 PARTICLES

```typescript
particles ParticleSystemID {
  // EMISSOR
  emitter {
    position: Vector2
    rate: number               // Partículas por segundo
    lifetime: milliseconds
    continuous: boolean
  }
  
  // PARTÍCULA
  particle {
    sprite: AssetPath
    size: Vector2
    color: Color
    opacity: 0..1
    
    // FÍSICA
    velocity: Vector2
    acceleration: Vector2
    gravity: number
    rotation: degrees
    angularVelocity: degrees
    
    // TEMPO DE VIDA
    lifetime: milliseconds
    fadeOut: boolean
  }
  
  // PRESET
  preset: ParticlePreset       // fire | smoke | sparkles | rain | snow
  
  // CONTROLE
  start()
  stop()
  burst(count: number)
}
```

---

# ⚙️ PARTE 4: SISTEMAS CORE

## 4.1 FLAGS & VARIABLES

```typescript
// FLAGS (Booleanos Globais)
flags {
  [key: string]: boolean
  
  set(key: string, value: boolean)
  get(key: string): boolean
  toggle(key: string)
  has(key: string): boolean
}

// VARIABLES (Dados Globais)
vars {
  [key: string]: any
  
  set(key: string, value: any)
  get(key: string): any
  increment(key: string, amount?: number)
  decrement(key: string, amount?: number)
}

// Exemplos
flags.porta_aberta = true
vars.dias_passados = 0
vars.pontuacao = 100
```

---

## 4.2 SAVE SYSTEM

```typescript
game {
  // SALVAR
  save(slot?: number) {
    data = {
      player: player.serialize(),
      scene: currentScene,
      flags: flags,
      vars: vars,
      quests: quests,
      timestamp: now()
    }
    storage.save(slot, data)
  }
  
  // CARREGAR
  load(slot: number) {
    data = storage.load(slot)
    if (data) {
      player.deserialize(data.player)
      goToScene(data.scene)
      flags = data.flags
      vars = data.vars
      quests = data.quests
    }
  }
  
  // AUTO-SAVE
  autoSave(interval: milliseconds) {
    every interval {
      save(0)  // Slot auto-save
    }
  }
}

---

## 4.3 UI SYSTEM

```typescript
ui {
  // MENSAGENS
  showMessage(text: string, duration?: milliseconds)
  showNotification(text: string, icon?: string)
  narrate(text: string)  // Caixa de narrativa
  
  // ESCOLHAS
  showChoice(question: string, options: string[]): Promise<number>
  
  // INPUT
  showTextInput(prompt: string, maxLength?: number): Promise<string>
  showNumberInput(prompt: string, min?: number, max?: number): Promise<number>
  
  // INVENTÁRIO
  openInventory()
  closeInventory()
  
  // JOURNAL/LOG
  openQuestLog()
  openJournal()
  addJournalEntry(title: string, text: string)
  
  // MENUS
  openMenu(menuID: MenuID)
  closeMenu()
  
  // DIÁLOGO
  showDialogueBox(character: CharacterID, text: string)
  hideDialogueBox()
  
  // CUTSCENE
  startCutscene()
  endCutscene()
  
  // HUD
  hud {
    show()
    hide()
    updateHealth(value: number)
    updateMana(value: number)
    updateGold(value: number)
  }
}

---

## 4.4 AUDIO SYSTEM

```typescript
audio {
  // MÚSICA
  playMusic(file: AssetPath, options?: {
    loop?: boolean
    volume?: 0..1
    fadeIn?: milliseconds
  })
  
  stopMusic(fadeOut?: milliseconds)
  pauseMusic()
  resumeMusic()
  
  // SFX
  playSound(file: AssetPath, options?: {
    volume?: 0..1
    pitch?: number
    pan?: -1..1  // Estéreo
    position?: Vector2  // Som posicional
  })
  
  // VOZ
  playVoice(file: AssetPath)
  stopVoice()
  
  // CONTROLE GLOBAL
  setMasterVolume(volume: 0..1)
  setMusicVolume(volume: 0..1)
  setSfxVolume(volume: 0..1)
  muteAll()
  unmuteAll()
}

---

## 4.5 TIME SYSTEM

```typescript
time {
  // TEMPO REAL
  now(): milliseconds
  delta: milliseconds  // Tempo desde último frame
  
  // TEMPO DE JOGO
  gameTime: milliseconds
  
  // DIA/NOITE
  timeOfDay: TimeOfDay  // morning | afternoon | evening | night
  dayNumber: number
  
  // AVANÇAR TEMPO
  advanceTime(amount: milliseconds)
  setTime(time: TimeOfDay)
  
  // EVENTOS TEMPORAIS
  every(interval: milliseconds, callback: () => void)
  after(delay: milliseconds, callback: () => void)
  
  // SCHEDULE
  schedule: {
    at(time: TimeOfDay, callback: () => void)
    daily(callback: () => void)
  }
}

---

# 🎬 PARTE 5: CONTROLES & LÓGICA

## 5.1 CONTROL FLOW

```typescript
// CONDICIONAIS
if (condition) {
  // ...
}

when (condition) {
  // Mais semântico
}

match (value) {
  case pattern1: action1
  case pattern2: action2
  default: defaultAction
}

// LOOPS
for item in collection {
  // ...
}

while (condition) {
  // ...
}

repeat (times) {
  // ...
}

// ASYNC/WAIT
await asyncFunction()
wait(milliseconds)
waitUntil(condition)
waitFor(event)

---

## 5.2 FUNCTIONS

```typescript
function functionName(param1: Type, param2: Type): ReturnType {
  // corpo
  return value
}

// Arrow function
const func = (x, y) => x + y

// Callbacks
on event(callback: () => void)

---

## 5.3 QUERIES

```typescript
// BUSCAR ENTIDADES
find(type: EntityType, filter?: (entity) => boolean)
findAll(type: EntityType)
findByName(name: string)
findByTag(tag: string)
findNearest(position: Vector2, type?: EntityType)
findInRadius(position: Vector2, radius: number)

// EXEMPLOS
let enemies = findAll("enemy")
let nearestChest = findNearest(player.position, "chest")
let lockedDoors = find("door", d => d.state == "locked")

---

## 5.4 MATH & UTILS

```typescript
math {
  // BÁSICO
  abs(x), floor(x), ceil(x), round(x)
  min(...values), max(...values)
  clamp(value, min, max)
  
  // RANDOM
  random(): 0..1
  randomInt(min, max)
  randomChoice(array)
  randomChance(probability: 0..1): boolean
  
  // GEOMETRIA
  distance(p1: Vector2, p2: Vector2)
  angle(from: Vector2, to: Vector2)
  lerp(a, b, t)
  
  // TRIGONOMETRIA
  sin, cos, tan, atan2
  
  // CONSTANTES
  PI, TAU, E
}

string {
  // MANIPULAÇÃO
  concat, split, join
  substring, indexOf
  toUpperCase, toLowerCase
  replace, trim
  
  // FORMATAÇÃO
  format(template: string, ...args)
  interpolate`Texto com ${variable}`
}

array {
  // MÉTODOS
  push, pop, shift, unshift
  map, filter, reduce, find
  sort, reverse, shuffle
  
  // QUERIES
  first, last, isEmpty
  contains, indexOf
}

---

# 🎯 PARTE 6: EVENTOS GLOBAIS

## 6.1 GAME EVENTS

```typescript
// CICLO DE VIDA
on gameStart { }
on gameOver { }
on gamePause { }
on gameResume { }

// PROGRESSO
on levelUp { }
on achievementUnlock(achievement: AchievementID) { }
on questComplete(quest: QuestID) { }

// INPUT
on keyPress(key: KeyCode) { }
on keyRelease(key: KeyCode) { }
on mouseClick(position: Vector2) { }
on mouseMove(position: Vector2) { }

// SISTEMA
on sceneChange(from: SceneID, to: SceneID) { }
on itemCollect(item: ItemID) { }
on itemUse(item: ItemID) { }
on dialogueStart(dialogue: DialogueID) { }
on dialogueEnd(dialogue: DialogueID) { }

---

# 🏆 PARTE 7: SISTEMAS AVANÇADOS

## 7.1 COMBAT SYSTEM

```typescript
combat {
  // INICIAR
  start(enemies: Character[])
  end()
  
  // TURNO
  currentTurn: Character
  nextTurn()
  
  // AÇÕES
  attack(attacker: Character, target: Character, weapon?: Item)
  defend(character: Character)
  useSkill(character: Character, skill: Skill, target?: Character)
  useItem(character: Character, item: Item, target?: Character)
  flee(character: Character): boolean
  
  // CÁLCULO
  calculateDamage(attacker, target, weapon?): number
  calculateHit(attacker, target): boolean
  
  // EFEITOS
  applyStatus(character: Character, status: StatusEffect)
  removeStatus(character: Character, status: StatusEffect)
  
  // EVENTOS
  on combatStart { }
  on combatEnd(result: "victory" | "defeat" | "flee") { }
  on turnStart(character: Character) { }
  on damage(character: Character, amount: number) { }
  on death(character: Character) { }
}

---

## 7.2 CRAFTING SYSTEM

```typescript
crafting {
  // RECEITAS
  recipes: Recipe[] {
    id: string
    name: string
    ingredients: {
      [itemID: string]: quantity
    }
    result: ItemID
    resultQuantity: number
    
    // REQUISITOS
    requiredTool?: ItemID
    requiredSkill?: {
      skill: SkillType
      level: number
    }
    
    // TEMPO
    craftTime?: milliseconds
  }
  
  // CRAFTAR
  craft(recipeID: RecipeID): boolean {
    recipe = recipes[recipeID]
    
    if (!hasIngredients(recipe.ingredients)) {
      return false
    }
    
    if (recipe.requiredTool && !player.has(recipe.requiredTool)) {
      return false
    }
    
    consumeIngredients(recipe.ingredients)
    
    if (recipe.craftTime) {
      wait(recipe.craftTime)
    }
    
    player.inventory.add(recipe.result, recipe.resultQuantity)
    
    return true
  }
  
  // DESCOBRIR RECEITAS
  learnRecipe(recipeID: RecipeID)
  hasRecipe(recipeID: RecipeID): boolean
}

---

## 7.3 WEATHER SYSTEM

```typescript
weather {
  // ESTADO
  current: WeatherType  // clear | rain | snow | fog | storm
  intensity: 0..1
  
  // MUDAR
  set(type: WeatherType, intensity?: number, transition?: milliseconds)
  clear()
  
  // EFEITOS
  affects {
    visibility: boolean
    lighting: boolean
    movement: boolean
    combat: boolean
  }
  
  // PARTÍCULAS
  particles: ParticleSystem
  
  // AUDIO
  ambientSound?: SoundEffect
}

---

## 7.4 ECONOMY SYSTEM

```typescript
economy {
  // MOEDAS
  currency: {
    name: string
    symbol: string
  }
  
  // PREÇOS
  calculatePrice(item: Item, merchant: Character): number {
    basePrice = item.value
    multiplier = merchant.shop.priceMultiplier
    reputation = player.reputation[merchant.faction]
    
    return basePrice * multiplier * (1 - reputation/200)
  }
  
  // TRANSAÇÃO
  buy(item: Item, merchant: Character): boolean {
    price = calculatePrice(item, merchant)
    
    if (player.gold >= price) {
      player.gold -= price
      player.inventory.add(item)
      merchant.inventory.remove(item)
      return true
    }
    
    return false
  }
  
  sell(item: Item, merchant: Character): boolean {
    price = calculatePrice(item, merchant) * 0.5  // Vende por metade
    
    player.inventory.remove(item)
    player.gold += price
    merchant.inventory.add(item)
    
    return true
  }
}

---

# 📝 PARTE 8: TEMPLATES PRONTOS

## 8.1 COMPLETE GAME OBJECT EXAMPLES

### Porta Completa com Tudo

```typescript
object MainDoor {
  identity {
    name: "Porta Principal"
    description: "Uma porta de carvalho maciço com detalhes em bronze."
    type: "interactive"
    tags: ["door", "locked", "important"]
  }
  
  visual {
    sprite: "doors/oak_door.png"
    position: {x: 200, y: 150}
    size: {width: 80, height: 120}
    animations: {
      idle: {frames: ["door_closed.png"], fps: 1}
      opening: {frames: ["door_open_1.png", "door_open_2.png"], fps: 10}
      open: {frames: ["door_open.png"], fps: 1}
    }
  }
  
  state {
    locked: true
    opened: false
    health: 100
  }
  
  interaction {
    interactable: true
    verbs: ["examine", "use", "unlock"]
    cursor: "pointer"
    hotspot: {x: 0, y: 0, width: 80, height: 120}
  }
  
  // COMPORTAMENTO
  on examine {
    if (state.locked) {
      narrate("A porta está trancada. Há um buraco de fechadura.")
    } else if (state.opened) {
      narrate("A porta está aberta, revelando o corredor além.")
    } else {
      narrate("Uma porta fechada.")
    }
  }
  
  on click {
    if (state.locked) {
      narrate("A porta está trancada.")
      playSound("door_locked.wav")
    } else if (state.opened) {
      goToScene("Corridor")
    } else {
      open()
    }
  }
  
  on useWith(item: Item) {
    match item.id {
      case "bronze_key": {
        if (state.locked) {
          unlock()
        } else {
          narrate("A porta já está destrancada.")
        }
      }
      case "lockpick": {
        startMinigame("lockpicking")
      }
      case "axe": {
        damage(25)
      }
      default: {
        narrate("Isso não funciona aqui.")
      }
    }
  }
  
  // MÉTODOS CUSTOMIZADOS
  function unlock() {
    state.locked = false
    playSound("door_unlock.wav")
    playAnimation("shake")
    narrate("*CLIQUE* A porta foi destrancada!")
    flags.main_door_unlocked = true
  }
  
  function open() {
    state.opened = true
    playAnimation("opening")
    playSound("door_creak.wav")
    wait(500)
    currentAnimation = "open"
  }
  
  function damage(amount: number) {
    state.health -= amount
    playSound("wood_hit.wav")
    shake(5, 200)
    
    if (state.health <= 0) {
      destroy()
    } else {
      narrate(`A porta está danificada (${state.health}/100)`)
    }
  }
  
  function destroy() {
    state.locked = false
    state.opened = true
    sprite = "doors/door_broken.png"
    playSound("wood_break.wav")
    narrate("A porta se quebra em pedaços!")
    flags.main_door_destroyed = true
  }
}

---

### NPC Completo (Mercador)

```typescript
character Blacksmith {
  identity {
    name: "Ferreiro Grendel"
    title: "Mestre Ferreiro"
    description: "Um anão robusto com barba vermelha e mãos calejadas."
    age: 156
    species: "dwarf"
  }
  
  visual {
    sprite: "characters/blacksmith.png"
    portrait: "portraits/blacksmith.png"
    position: {x: 400, y: 300}
    animations: {
      idle: {frames: ["blacksmith_idle.png"], fps: 2}
      hammering: {frames: ["blacksmith_work_1.png", "blacksmith_work_2.png"], fps: 8}
      talk: {frames: ["blacksmith_talk.png"], fps: 4}
    }
  }
  
  attributes {
    health: 200
    strength: 18
    charisma: 12
  }
  
  mental {
    mood: "focused"
    relationship: {
      "player": 0  // Neutro
    }
    personality: {
      traits: ["honesto", "trabalhador", "teimoso"]
      quirks: ["bate na bigorna quando nervoso"]
    }
  }
  
  behavior {
    schedule: [
      {time: "morning", location: "blacksmith", action: "hammering"},
      {time: "afternoon", location: "blacksmith", action: "hammering"},
      {time: "evening", location: "tavern", action: "drinking"}
    ]
  }
  
  dialogue {
    defaultTree: "blacksmith_greeting"
  }
  
  shop {
    buys: ["ore", "weapon", "armor"]
    sells: ["iron_sword", "steel_axe", "chainmail"]
    priceMultiplier: 1.2
    currency: "gold"
  }
  
  quests {
    available: ["forge_legendary_sword"]
  }
  
  inventory {
    items: ["iron_sword", "steel_axe", "hammer"]
    gold: 500
  }
  
  // COMPORTAMENTO
  on click {
    if (relationship[player] >= 50) {
      startDialogue("blacksmith_friend")
    } else if (relationship[player] <= -20) {
      startDialogue("blacksmith_angry")
    } else {
      startDialogue("blacksmith_greeting")
    }
  }
  
  on giveItem(item: Item) {
    match item.type {
      case "ore": {
        relationship[player] += 10
        narrate("Grendel examina o minério com aprovação.")
        accept(item)
      }
      case "weapon": {
        if (item.quality == "masterwork") {
          relationship[player] += 20
          narrate("'Trabalho fino! Raras vezes vejo artesanato assim.'")
        }
        accept(item)
      }
      default: {
        narrate("'Não tenho uso para isso, rapaz.'")
        reject(item)
      }
    }
  }
  
  // DIÁLOGOS
  dialogue blacksmith_greeting {
    start: "intro"
    
    nodes {
      intro {
        speaker: "Blacksmith"
        text: "Bem-vindo à forja! Precisa de algo afiado?"
        animation: "talk"
        
        next: [
          choice trade: "Quero ver suas armas" -> "show_shop"
          choice quest: "Ouvi que precisa de ajuda" -> "quest_intro"
          choice leave: "Só passando" -> "goodbye"
        ]
      }
      
      show_shop {
        speaker: "Blacksmith"
        text: "Todas forjadas à mão. Qualidade garantida!"
        onEnter { openShop(this) }
        next: "end"
      }
      
      quest_intro {
        speaker: "Blacksmith"
        text: "Ah sim... preciso de um favor. Me traga 5 barras de aço e eu forjarei algo especial para você."
        
        onEnter {
          if (!flags.blacksmith_quest_started) {
            startQuest("forge_legendary_sword")
            flags.blacksmith_quest_started = true
          }
        }
        
        next: "end"
      }
      
      goodbye {
        speaker: "Blacksmith"
        text: "Até mais. E cuidado com essa espada!"
        next: "end"
      }
    }
  }
  
  // QUEST
  quest forge_legendary_sword {
    title: "A Espada Lendária"
    description: "Grendel pediu 5 barras de aço para forjar uma arma especial."
    
    objectives: [
      {
        type: "collect"
        target: "steel_bar"
        required: 5
        description: "Colete 5 barras de aço"
      },
      {
        type: "talk"
        target: "blacksmith"
        description: "Retorne ao ferreiro"
      }
    ]
    
    on complete {
      player.inventory.remove("steel_bar", 5)
      player.inventory.add("legendary_sword")
      relationship[player] += 50
      narrate("Grendel forja uma espada magnífica!")
      playAnimation("forge_sword")
      playSound("anvil_complete.wav")
    }
  }
}

---

### Sistema de Puzzle Completo

```typescript
puzzle LibraryCodePuzzle {
  type: "code"
  difficulty: "medium"
  
  solution: "1842"
  
  state {
    attempts: 0
    maxAttempts: 5
    isSolved: false
    hintsUsed: 0
  }
  
  hints: [
    {
      text: "Procure no quadro atrás da mesa",
      condition: () => state.attempts >= 1
    },
    {
      text: "O ano está escrito no livro na estante",
      condition: () => state.attempts >= 2
    },
    {
      text: "Olhe a data na carta antiga",
      condition: () => examined("old_letter")
    }
  ]
  
  ui {
    title: "Cofre da Biblioteca"
    description: "Digite o código de 4 dígitos"
    inputType: "numeric"
    maxLength: 4
  }
  
  on attempt(code: string) {
    state.attempts++
    
    if (code == solution) {
      solve()
    } else {
      // Feedback parcial
      let correctDigits = countCorrectDigits(code, solution)
      
      if (correctDigits > 0) {
        narrate(`Você ouve ${correctDigits} cliques suaves...`)
        playSound("lock_tick.wav", {count: correctDigits})
      } else {
        narrate("Nada acontece.")
        playSound("lock_wrong.wav")
      }
      
      if (state.attempts >= state.maxAttempts) {
        fail()
      } else {
        narrate(`Tentativas restantes: ${maxAttempts - attempts}`)
        offerHint()
      }
    }
  }
  
  function offerHint() {
    let availableHints = hints.filter(h => h.condition() && !h.used)
    
    if (availableHints.length > 0) {
      showChoice("Precisa de uma dica?", ["Sim", "Não"])
        .then(choice => {
          if (choice == 0) {
            showHint(availableHints[0])
          }
        })
    }
  }
  
  function showHint(hint: Hint) {
    narrate(`💡 DICA: ${hint.text}`)
    hint.used = true
    state.hintsUsed++
  }
  
  on solve {
    state.isSolved = true
    playSound("puzzle_solve.wav")
    playAnimation("safe_open")
    
    narrate("*CLIQUE* O cofre se abre!")
    
    open("library_safe")
    
    // Recompensa baseada em performance
    let perfectSolve = (state.attempts == 1 && state.hintsUsed == 0)
    
    if (perfectSolve) {
      player.inventory.add("golden_key")
      player.experience += 100
      unlockAchievement("master_detective")
      narrate("🏆 Resolvido perfeitamente! Você ganhou +100 XP!")
    } else {
      player.inventory.add("silver_key")
      player.experience += 50
    }
    
    flags.library_safe_open = true
  }
  
  on fail {
    narrate("❌ O cofre trava permanentemente!")
    playSound("alarm.wav")
    triggerAlarm()
    flags.library_safe_failed = true
    
    // Rota alternativa
    npc("librarian").attitude = "hostile"
    narrate("Você ouve passos rápidos se aproximando...")
  }
  
  function triggerAlarm() {
    playSound("alarm_loop.wav", {loop: true})
    scene.lighting = "red_flash"
    
    after(3000, () => {
      spawnGuards()
    })
  }
  
  function countCorrectDigits(attempt: string, solution: string): number {
    let count = 0
    for (let i = 0; i < 4; i++) {
      if (attempt[i] == solution[i]) count++
    }
    return count
  }
}

---

# 🎯 PARTE 9: REFERÊNCIA RÁPIDA PARA IA DIRECTOR

## 9.1 COMANDOS MAIS USADOS

```typescript
// CRIAR OBJETO
createObject({
  name: string,
  type: ObjectType,
  position: Vector2,
  sprite?: AssetPath,
  ses?: string
})

// CRIAR CENA
createScene({
  name: string,
  background: AssetPath,
  objects?: GameObject[]
})

// ADICIONAR DIÁLOGO
createDialogue({
  id: string,
  character: CharacterID,
  nodes: DialogueNode[]
})

// CRIAR QUEST
createQuest({
  title: string,
  objectives: Objective[],
  rewards: Rewards
})

// MODIFICAR ESTADO
setFlag(key: string, value: boolean)
setVar(key: string, value: any)

// NARRATIVA
narrate(text: string)
showChoice(question: string, options: string[])

// NAVEGAÇÃO
goToScene(sceneID: SceneID)

// ITEMS
giveItem(itemID: ItemID, quantity?: number)
removeItem(itemID: ItemID, quantity?: number)

---

## 9.2 PADRÕES COMUNS

### Porta com Chave
```typescript
object Door {
  state: "locked"
  
  on click {
    if (state == "locked") {
      if (player.has("key")) {
        state = "open"
        narrate("Porta destrancada!")
      } else {
        narrate("Precisa de uma chave.")
      }
    } else {
      goToScene("NextRoom")
    }
  }
}
```

### Objeto Coletável
```typescript
object Coin {
  on click {
    player.inventory.add("coin")
    playSound("coin.wav")
    destroy(this)
  }
}
```

### NPC Simples
```typescript
character Shopkeeper {
  on click {
    startDialogue("shop_greeting")
  }
}
```

### Puzzle Básico
```typescript
puzzle SimpleCode {
  solution: "1234"
  
  on attempt(code) {
    if (code == solution) {
      solve()
    }
  }
  
  on solve {
    open("door")
  }
}
```

### Quest de Coleta
```typescript
quest FetchQuest {
  objectives: [
    {type: "collect", target: "herb", required: 3}
  ]
  
  on complete {
    giveItem("potion")
  }
}
```

---

## 9.3 MACROS PARA IA DIRECTOR

### MACRO: Criar Objeto Completo
```typescript
@macro CreateInteractiveObject(
  name: string,
  description: string,
  behavior: "door" | "container" | "decoration" | "collectible"
) {
  object Generated {
    name: $name
    description: $description
    
    @if (behavior == "door") {
      on click {
        if (state == "locked") {
          narrate("Trancado.")
        } else {
          goToScene("next")
        }
      }
    }
    
    @if (behavior == "container") {
      inventory: []
      on click {
        openInventory(this)
      }
    }
    
    @if (behavior == "decoration") {
      on examine {
        narrate($description)
      }
    }
    
    @if (behavior == "collectible") {
      on click {
        player.inventory.add(this.id)
        destroy(this)
      }
    }
  }
}
```

### MACRO: Criar NPC com Diálogo
```typescript
@macro CreateNPC(
  name: string,
  greeting: string,
  hasShop: boolean,
  hasQuest: boolean
) {
  character Generated {
    name: $name
    
    dialogue default {
      start: "greeting"
      
      nodes {
        greeting {
          speaker: $name
          text: $greeting
          
          next: [
            @if (hasShop) {
              choice "Ver loja" -> "shop"
            }
            @if (hasQuest) {
              choice "Precisa de ajuda?" -> "quest"
            }
            choice "Até logo" -> "end"
          ]
        }
        
        @if (hasShop) {
          shop {
            onEnter { openShop(this) }
            next: "end"
          }
        }
        
        @if (hasQuest) {
          quest {
            text: "Sim, preciso que você..."
            onEnter { startQuest("quest_" + this.id) }
            next: "end"
          }
        }
      }
    }
  }
}
```

---

## 9.4 TEMPLATES DE JOGO COMPLETO

### Text Adventure Puro
```typescript
game TextAdventure {
  mode: "text_only"
  
  scene Room {
    description: "Descrição textual da sala"
    
    visibleObjects: ["mesa", "porta", "janela"]
    
    on command "examinar mesa" {
      narrate("Descrição da mesa...")
    }
    
    on command "n" or "norte" {
      goToScene("NextRoom")
    }
    
    on command "pegar chave" {
      if (visible("chave")) {
        player.inventory.add("chave")
        narrate("Você pegou a chave.")
      }
    }
  }
}
```

### Point & Click Visual
```typescript
game PointAndClick {
  mode: "visual"
  
  scene Room {
    background: "room.png"
    
    object Table {
      sprite: "table.png"
      position: {x: 300, y: 400}
      
      on click {
        examine()
      }
    }
  }
}
```

### RPG com Combate
```typescript
game RPG {
  mode: "rpg"
  
  player {
    attributes {
      health: 100
      mana: 50
      level: 1
    }
  }
  
  character Enemy {
    combat {
      hostile: true
      health: 50
      attackDamage: 10
    }
    
    on death {
      dropLoot({gold: 50, items: ["potion"]})
    }
  }
}
```

---

# 🏁 CONCLUSÃO

## Esta biblioteca contém:

✅ **Entidades:** Scene, Object, Item, Character, Hotspot  
✅ **Sistemas:** Player, Dialogue, Quest, Puzzle, Combat, Crafting  
✅ **Controles:** Flags, Variables, Save/Load, UI, Audio, Time  
✅ **Visual:** Camera, Animation, Particles, Weather  
✅ **Lógica:** Control Flow, Functions, Queries, Math  
✅ **Templates:** Objetos, NPCs, Puzzles prontos  
✅ **Macros:** Geração automática  
✅ **Exemplos:** Jogos completos funcionais  
✅ **Guia IA:** Como a IA deve usar tudo isso  

---

## Para a Gemini AI Director:

**Esta é sua referência completa.**

Quando o usuário pedir:
1. Consulte esta biblioteca
2. Escolha os componentes apropriados
3. Gere código SES funcional
4. Adicione ao projeto
5. Confirme ao usuário

**VOCÊ AGORA TEM PODER TOTAL PARA CRIAR QUALQUER JOGO!** 🎮✨

---

**FIM DA BIBLIOTECA SES COMPLETA v2.0**