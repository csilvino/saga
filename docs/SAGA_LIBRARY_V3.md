# 📚 SES COMPLETE LIBRARY v3.0
## The Ultimate Game Director's Reference

> *"Todo comando, toda possibilidade, toda lógica de jogo em um só lugar."*
> *Versão 3.0 — Expandida com: AI Director, Cutscenes, Achievements, Analytics, i18n, Event Bus, Accessibility e muito mais.*

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
    chapter?: number                // Capítulo da história
    act?: string                    // "Ato 1 - A Chegada"
  }
  
  // VISUAL
  visual {
    background: AssetPath           // "backgrounds/sala.png"
    lighting: LightingMode          // day | night | dim | bright | custom
    weather?: WeatherType           // sunny | rainy | snowy | foggy
    particles?: ParticleEffect[]    // neve, chuva, poeira
    filters?: ImageFilter[]         // sepia, blur, contrast
    parallax?: ParallaxLayer[]      // Camadas de profundidade
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
      spatial?: Position
    }
  }
  
  // NAVEGAÇÃO
  navigation {
    exits: {
      [Direction]: Exit {
        to: SceneID
        condition?: () => boolean
        transition?: TransitionType // fade | slide | instant | wipe | iris
        onExit?: () => void
        label?: string              // Aparece no cursor/tooltip
      }
    }
    mapPosition?: Vector2
    visitCount: number
    region?: string                 // "Castelo", "Floresta" — para mapa
  }
  
  // ESTADO
  state {
    isLocked: boolean
    isDiscovered: boolean
    weather: WeatherState
    timeOfDay: TimeOfDay
    [customKey: string]: any
  }
  
  // POPULAÇÃO
  entities: {
    objects: GameObject[]
    characters: Character[]
    items: Item[]
    hotspots: Hotspot[]
  }
  
  // CICLO DE VIDA
  lifecycle {
    onFirstEnter?: () => void
    onEnter?: () => void
    onExit?: () => void
    onUpdate?: (delta: number) => void
    onLongStay?: () => void         // Após X segundos
    onReturn?: () => void           // Segunda visita em diante
  }
  
  // TRIGGERS
  triggers: Trigger[] {
    condition: () => boolean
    action: () => void
    once: boolean
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
  
  // ANALYTICS (para modo educacional)
  analytics?: {
    trackTime: boolean              // Quanto tempo ficou na cena
    trackActions: boolean          // Quais objetos clicou
    learningObjective?: string     // "Identificar causas da Revolução"
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

// Cena com retorno diferente
scene LibraryScene {
  on firstEnter {
    playCutscene("library_intro")
    narrate("Você nunca esteve em um lugar assim.")
  }
  
  on return {
    narrate("A biblioteca... de volta.")
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
    localizedName?: LocaleKey     // Para i18n
  }
  
  // VISUAL
  visual {
    sprite: AssetPath | SpriteSheet
    position: Vector2
    size: Vector2
    rotation: degrees
    scale: Vector2
    zIndex: number
    opacity: 0..1
    visible: boolean
    
    animations?: {
      [stateName: string]: Animation {
        frames: AssetPath[]
        fps: number
        loop: boolean
      }
    }
    currentAnimation?: string
    
    glow?: boolean
    shadow?: boolean
    highlight?: boolean
    
    // ACESSIBILIDADE
    accessibilityLabel?: string   // Descrição para leitores de tela
  }
  
  // FÍSICA (opcional)
  physics? {
    mass: number
    velocity: Vector2
    gravity: boolean
    collision: CollisionShape
    solid: boolean
  }
  
  // INTERAÇÃO
  interaction {
    interactable: boolean
    verbs: Verb[]                 // examine | take | use | open | close
    cursor: CursorType
    hotspot: Rectangle
    range?: number
    tooltip?: string              // Aparece ao passar o mouse
  }
  
  // ESTADO
  state: {
    [key: string]: any
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
  
  when condition { }
  
  every duration { }
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

// Container
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

// Decoração
object Painting extends DecorationTemplate {
  on examine {
    narrate(description)
  }
}

// Destrutível
object Vase extends DestructibleTemplate {
  health: 1
  
  on click {
    destroy()
    playSound("glass_break.wav")
    dropItem("coin")
  }
}

// NOVO: Placa/Sinal de Texto
object SignPost {
  on examine {
    showMessage(text, {
      style: "sign",
      duration: 4000
    })
  }
}

// NOVO: Espelho
object Mirror {
  on examine {
    showCutscene("player_reflection")
    narrate("Você se olha no espelho. Ainda o mesmo... ou não?")
  }
}

// NOVO: Terminal/Computador
object Terminal {
  state {
    powered: false
    accessLevel: 0
    data: string[]
  }
  
  on use {
    if (!state.powered) {
      narrate("Sem energia.")
    } else {
      openInterface("terminal_ui", {
        data: state.data,
        accessLevel: state.accessLevel
      })
    }
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
    category: ItemCategory         // weapon | key | consumable | quest | tool | book | food
    tags: string[]
    rarity: Rarity                 // common | uncommon | rare | legendary
    lore?: string                  // História do item (aparece em examine detalhado)
  }
  
  // VISUAL
  visual {
    icon: AssetPath
    sprite?: AssetPath
    color?: Color
    glow?: Color                   // Para itens mágicos
  }
  
  // PROPRIEDADES
  properties {
    stackable: boolean
    maxStack: number
    weight: number
    value: number
    durability?: number
    consumable: boolean
    questItem?: boolean            // Não pode ser descartado/vendido
    unique?: boolean               // Só pode ter 1 no inventário
  }
  
  // ATRIBUTOS (RPG)
  attributes? {
    damage?: number
    defense?: number
    healing?: number
    mana?: number
    speed?: number
    [stat: string]: number
  }
  
  // ENCANTAMENTOS (para RPG)
  enchantments?: {
    [effectName: string]: {
      value: number
      description: string
    }
  }
  
  // USO
  usage {
    usableInInventory: boolean
    usableOnObjects: boolean
    usableOnCharacters: boolean
    consumeOnUse: boolean
    cooldown?: milliseconds
    requiresSkill?: { skill: string, level: number }
  }
  
  // EVENTOS
  on collect {
    playSound("item_get.wav")
    narrate(`Você obteve: ${name}`)
    analytics.track("item_collected", { itemID: this.id })
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
  
  on useOn(target: Object | Character) { }
  
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
item BronzeKey extends KeyTemplate {
  unlocks: ["door_main", "chest_library"]
}

item HealthPotion extends ConsumableTemplate {
  healing: 50
  on use {
    player.health += healing
    playSound("drink.wav")
    remove from inventory
  }
}

item Sword extends WeaponTemplate {
  damage: 25
  durability: 100
  range: 1.5
}

item MysteriousLetter extends QuestItemTemplate {
  questID: "mystery_of_manor"
  canDrop: false
  
  on examine {
    narrate(lore)
    flags.letter_read = true
  }
}

item WoodPlank {
  on combine with Nails {
    if (player.has("hammer")) {
      create("wooden_board")
      narrate("Você criou uma tábua reforçada!")
    }
  }
}

// NOVO: Livro Legível
item AncientTome extends ReadableTemplate {
  pages: [
    "Página 1: O reino foi fundado em 1200...",
    "Página 2: O rei desapareceu numa noite de tempestade...",
    "Página 3: Dizem que o tesouro está..."
  ]
  
  on use {
    openBookUI(this.pages)
    flags.read_ancient_tome = true
    player.experience += 10
  }
}

// NOVO: Mapa
item TreasureMap extends MapTemplate {
  reveals: ["scene_cave", "scene_ruins"]
  
  on use {
    openMapUI()
    scenes.reveal(reveals)
    narrate("O mapa revela locais desconhecidos!")
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
    title?: string
    description: string
    age?: number
    gender?: string
    species?: string
    faction?: string               // Para sistemas de reputação
    role?: string                  // "Guardião", "Mercador", "Vilão"
  }
  
  // VISUAL
  visual {
    sprite: AssetPath | SpriteSheet
    portrait?: AssetPath
    position: Vector2
    scale: number
    facing: Direction
    
    animations: {
      idle: Animation
      walk: Animation
      talk: Animation
      [emotion: string]: Animation
    }
    
    // Variações visuais (estado)
    variants?: {
      [variantName: string]: AssetPath  // "wounded", "disguised"
    }
  }
  
  // ATRIBUTOS
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
  
  // ESTADO MENTAL
  mental {
    mood: Mood
    relationship: {
      [characterID: string]: number  // -100 a +100
    }
    memory: {
      [flagID: string]: any
    }
    trustLevel: number             // 0..100 — desbloqueia diálogos especiais
  }
  
  // COMPORTAMENTO
  behavior {
    ai?: AIType                    // passive | patrol | follow | hostile | wander
    patrolPath?: Vector2[]         // Pontos do patrulhamento
    schedule?: Schedule[] {
      time: TimeOfDay
      location: SceneID
      action: string
    }
    personality: Personality {
      traits: string[]
      quirks: string[]
      speakingStyle?: string       // "formal", "nervoso", "poético"
    }
    reactionToPlayer?: {
      onFirstMeet: string          // "surprised" | "friendly" | "hostile"
      onLowReputation: string
      onHighReputation: string
    }
  }
  
  // DIÁLOGO
  dialogue {
    defaultTree: DialogueTreeID
    trees: {
      [treeID: string]: DialogueTree
    }
    voice?: VoiceType
    textSpeed?: number             // Para acessibilidade
  }
  
  // COMÉRCIO
  shop? {
    buys: ItemCategory[]
    sells: ItemID[]
    priceMultiplier: number
    currency: string
    restockInterval?: milliseconds
  }
  
  // QUESTS
  quests? {
    available: QuestID[]
    active: QuestID[]
    completed: QuestID[]
  }
  
  // COMBATE
  combat? {
    hostile: boolean
    attackDamage: number
    attackRange: number
    attackSpeed: milliseconds
    loot: LootTable
    abilities?: Ability[]
  }
  
  // EVENTOS
  on click { startDialogue(defaultTree) }
  on talk { startConversation() }
  on attack { enterCombat() }
  on death { dropLoot(); updateQuests() }
  on giveMoney(amount: number) { relationship[player] += amount / 10 }
  on giveItem(item: ItemID) {
    if (wants(item)) {
      relationship[player] += 20
      narrate("${name} agradece!")
    }
  }
  
  // NOVO: Reação a evento global
  on gameEvent(event: string) {
    match event {
      case "king_died": {
        mood = "sad"
        dialogue.defaultTree = "reaction_king_death"
      }
    }
  }
}
```

---

## 1.5 HOTSPOT (Área Interativa Invisível)

```typescript
hotspot HotspotID {
  area: Rectangle | Circle | Polygon
  type: HotspotType               // trigger | teleport | camera | cutscene | danger
  
  activation {
    trigger: TriggerType          // enter | exit | stay | click
    condition?: () => boolean
    once: boolean
    cooldown?: milliseconds
  }
  
  on activate { }
  on enter { }
  on exit { }
  on stay { }                     // NOVO: enquanto player está na área
}
```

### **Hotspot Examples**

```typescript
hotspot SecretPassage {
  area: rect(100, 100, 50, 50)
  on enter {
    if (player.has("secret_key")) {
      goToScene("SecretRoom")
    }
  }
}

hotspot BossCutscene {
  area: rect(400, 200, 100, 50)
  once: true
  on enter {
    playCutscene("boss_appears")
  }
}

hotspot LavaZone {
  area: circle(300, 400, 100)
  every 1000 {
    if (playerInArea()) {
      player.health -= 10
      playSound("sizzle.wav")
    }
  }
}

// NOVO: Área de sussurro/som posicional
hotspot GhostWhisper {
  area: rect(150, 200, 80, 80)
  on enter {
    playSound("ghost_whisper.wav", { volume: 0.3, loop: true })
    narrate("Você sente um arrepio...")
  }
  on exit {
    stopSound("ghost_whisper.wav")
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
    nextLevelXP?: number
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
      sort(by: "name" | "type" | "value"): void
      findByType(type: ItemCategory): Item[]
    }
  }
  
  // SKILLS (RPG)
  skills?: {
    [skillName: string]: {
      level: number
      experience: number
      maxLevel: number
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
    statusEffects: StatusEffect[]  // poisoned, blessed, cursed
  }
  
  // REPUTAÇÃO (por facção)
  reputation?: {
    [faction: string]: number      // -100 a +100
  }
  
  // PROGRESSO
  progress {
    scenesVisited: SceneID[]
    itemsCollected: ItemID[]
    npcsMetcount: number
    questsCompleted: QuestID[]
    achievements: AchievementID[]
    playTime: milliseconds
    deaths: number
    choicesMade: { [choiceID: string]: number }  // Rastreia decisões
  }
  
  // MÉTODOS
  methods {
    moveTo(position: Vector2)
    lookAt(direction: Direction)
    say(text: string)
    think(text: string)
    emote(emotion: string)
    levelUp()
    gainXP(amount: number)
    addSkillXP(skill: string, amount: number)
  }
}
```

---

## 2.2 DIALOGUE SYSTEM

```typescript
dialogue DialogueID {
  meta {
    title: string
    description?: string
    participants: CharacterID[]
    isRepeatable?: boolean         // Pode ser reiniciado?
    skipable?: boolean             // Player pode pular?
  }
  
  start: NodeID
  
  nodes: {
    [nodeID: string]: DialogueNode {
      speaker: CharacterID | "narrator" | "player"
      text: string | () => string
      emotion?: EmotionType
      voice?: AudioClip
      animation?: AnimationID
      portrait?: AssetPath         // Sobrescreve portrait do personagem
      
      condition?: () => boolean
      
      onEnter?: () => void
      onExit?: () => void
      
      // Timing
      autoAdvance?: milliseconds   // Avança automaticamente após X ms
      waitForAnimation?: boolean
      
      next: NodeID | Choice[] | "end"
    }
  }
  
  choices: {
    [choiceID: string]: Choice {
      text: string
      condition?: () => boolean
      icon?: string
      color?: Color
      
      // Custo de recursos
      costs?: {
        gold?: number
        health?: number
        reputation?: { [faction: string]: number }
      }
      
      // Skill check
      skillCheck?: {
        skill: string
        difficulty: number         // 1-10
        onSuccess: NodeID
        onFail: NodeID
      }
      
      onSelect?: () => void
      effects?: Effect[]
      next: NodeID
      
      // Rastreamento de escolha
      trackAs?: string             // Para analytics
    }
  }
  
  state: { [key: string]: any }
  
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

// Diálogo com Condições e Memória
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
      onEnter { startQuest("find_library_key") }
      next: "end"
    }
  }
}

// Diálogo com Skill Check
dialogue PersuadeCaptain {
  nodes {
    persuasion_attempt {
      speaker: "Player"
      text: "[Persuasão] Deixe-me passar, é urgente!"
      condition: () => player.attributes.charisma >= 5
      skillCheck: {
        skill: "charisma"
        difficulty: 6
        onSuccess: "success"
        onFail: "failure"
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

// NOVO: Diálogo Multi-personagem
dialogue CouncilMeeting {
  participants: ["lord", "merchant", "wizard"]
  start: "opening"
  
  nodes {
    opening {
      speaker: "lord"
      text: "O reino está em perigo. Precisamos agir."
      next: "merchant_speaks"
    }
    merchant_speaks {
      speaker: "merchant"
      text: "Mas os custos, milorde..."
      emotion: "worried"
      next: "wizard_speaks"
    }
    wizard_speaks {
      speaker: "wizard"
      text: "O ouro não importa se o reino cair."
      next: "player_choice"
    }
    player_choice {
      speaker: "narrator"
      text: "Todos olham para você."
      next: [
        choice side_lord: "Apóio o lorde" -> "support_war"
        choice side_merchant: "Apóio o mercador" -> "support_peace"
        choice neutral: "Precisamos de mais informação" -> "ask_details"
      ]
    }
  }
  
  onComplete {
    flags.council_decision = lastChoice
    analytics.track("major_choice", { choice: lastChoice })
  }
}
```

---

## 2.3 QUEST SYSTEM

```typescript
quest QuestID {
  meta {
    title: string
    description: string
    category: QuestCategory        // main | side | daily | hidden | tutorial
    difficulty: Difficulty
    recommendedLevel?: number
    estimatedTime?: minutes        // Para interface
    icon?: AssetPath
  }
  
  giver: CharacterID
  
  objectives: Objective[] {
    id: string
    description: string
    type: ObjectiveType            // collect | kill | talk | explore | craft | solve | photograph | escort
    target: string
    current: number
    required: number
    optional: boolean
    hidden?: boolean               // Revela após condição
    
    onComplete?: () => void
  }
  
  state: QuestState                // inactive | active | completed | failed | abandoned
  
  rewards {
    experience?: number
    gold?: number
    items?: ItemID[]
    reputation?: { [faction: string]: number }
    unlocks?: string[]
    achievement?: AchievementID
  }
  
  requirements? {
    level?: number
    items?: ItemID[]
    completedQuests?: QuestID[]
    flags?: FlagCondition[]
    reputation?: { [faction: string]: number }
  }
  
  failConditions? {
    timeLimit?: milliseconds
    onCharacterDeath?: CharacterID
    onItemLost?: ItemID
    onFlagChange?: { flag: string, value: any }
  }
  
  stages: Stage[] {
    id: string
    description: string
    onStart?: () => void
    onComplete?: () => void
  }
  currentStage: number
  
  // MÚLTIPLOS FINAIS
  endings?: {
    [endingID: string]: {
      condition: () => boolean
      rewards: Rewards
      narrative: string
    }
  }
  
  on start {
    narrate(`Nova Quest: ${title}`)
    showQuestLog()
    analytics.track("quest_started", { questID: this.id })
  }
  
  on objectiveComplete(obj: Objective) {
    playSound("objective_complete.wav")
    showNotification(`✓ ${obj.description}`)
  }
  
  on complete {
    giveRewards()
    playSound("quest_complete.wav")
    narrate("Quest Completa!")
    analytics.track("quest_completed", { questID: this.id })
  }
  
  on fail {
    narrate("Quest Falhada.")
    analytics.track("quest_failed", { questID: this.id, stage: currentStage })
  }
}
```

---

## 2.4 PUZZLE SYSTEM

```typescript
puzzle PuzzleID {
  type: PuzzleType                 // code | sequence | logic | inventory | riddle | spatial | memory | pattern
  difficulty: Difficulty
  solution: any
  
  state {
    attempts: number
    maxAttempts?: number
    isSolved: boolean
    timeSpent: milliseconds
    hintsUsed: number
  }
  
  hints: Hint[] {
    text: string
    condition: () => boolean
    cost?: number                  // Custo em ouro/XP para revelar
  }
  
  // Feedback progressivo
  partialCredit?: boolean          // Reconhece respostas parciais
  
  on attempt(answer: any) {
    state.attempts++
    state.timeSpent += time.delta
    
    if (answer == solution) {
      solve()
    } else {
      if (maxAttempts && attempts >= maxAttempts) {
        fail()
      } else {
        provideFeedback(answer)
      }
    }
    
    analytics.track("puzzle_attempt", {
      puzzleID: this.id,
      correct: answer == solution,
      attempts: state.attempts
    })
  }
  
  on solve {
    state.isSolved = true
    playSound("puzzle_solve.wav")
    giveReward()
    analytics.track("puzzle_solved", {
      puzzleID: this.id,
      attempts: state.attempts,
      hintsUsed: state.hintsUsed,
      timeSpent: state.timeSpent
    })
  }
  
  on fail {
    lockPuzzle()
    triggerConsequence()
  }
}
```

### **Puzzle Types Expandido**

```typescript
// Código
puzzle SafeCode {
  type: "code"
  solution: "1842"
  maxAttempts: 3
  hints: [
    { text: "O ano está escrito no quadro", condition: () => examined("painting") },
    { text: "Olhe a data no livro", condition: () => attempts >= 2 }
  ]
  on solve { open("safe"); player.inventory.add("golden_key") }
  on fail { triggerAlarm() }
}

// Sequência
puzzle PianoMelody {
  type: "sequence"
  solution: ["C", "E", "G", "C"]
  on attempt(notes: string[]) {
    if (notes == solution) { solve() }
    else { playSound("wrong_note.wav") }
  }
  on solve { openSecretDoor() }
}

// Inventário
puzzle AlchemyPuzzle {
  type: "inventory"
  solution: { ingredients: ["herb", "crystal", "water"], order: "specific" }
  on attempt(items: ItemID[]) {
    if (correctCombination(items)) {
      createItem("magic_potion")
      solve()
    }
  }
}

// Lógica
puzzle ChessPuzzle {
  type: "logic"
  board: ChessBoard
  solution: Move[]
  on attempt(move: Move) {
    if (isCorrectMove(move)) {
      if (allMovesComplete()) { solve() }
      else { narrate("Correto! Continue...") }
    } else {
      reset()
      narrate("Movimento errado.")
    }
  }
}

// NOVO: Puzzle Espacial (mover objetos)
puzzle SlidingBoxes {
  type: "spatial"
  grid: Grid(4, 4)
  pieces: [
    { id: "box1", position: {x:0, y:0}, size: {w:2, h:1} },
    { id: "box2", position: {x:2, y:0}, size: {w:1, h:2} }
  ]
  goal: { "box1": {x:2, y:3} }
  
  on move(pieceID: string, direction: Direction) {
    if (isValidMove(pieceID, direction)) {
      movePiece(pieceID, direction)
      if (checkGoal()) { solve() }
    }
  }
}

// NOVO: Puzzle de Memória (Simon Says)
puzzle MemoryPattern {
  type: "memory"
  sequenceLength: 4
  
  state {
    currentSequence: string[]
    playerInput: string[]
    round: 1
  }
  
  on start {
    state.currentSequence = generateRandomSequence(sequenceLength)
    playSequence(state.currentSequence)
  }
  
  on playerInput(button: string) {
    state.playerInput.push(button)
    
    let pos = state.playerInput.length - 1
    if (state.playerInput[pos] != state.currentSequence[pos]) {
      reset()
      narrate("Errou! Tente de novo.")
    } else if (state.playerInput.length == state.currentSequence.length) {
      solve()
    }
  }
}

// NOVO: Riddle (Advinha)
puzzle SphinxRiddle {
  type: "riddle"
  riddle: "Tenho cidades, mas não casas. Tenho montanhas, mas não árvores. Tenho água, mas não peixes. O que sou?"
  solution: ["mapa", "um mapa"]  // Aceita variações
  
  ui {
    type: "text_input"
    placeholder: "Sua resposta..."
    caseSensitive: false
  }
  
  on attempt(answer: string) {
    if (solution.includes(answer.toLowerCase())) {
      solve()
    } else {
      narrate("A esfinge sacode a cabeça.")
      state.attempts++
    }
  }
}
```

---

# 🎨 PARTE 3: SISTEMAS VISUAIS

## 3.1 CAMERA

```typescript
camera {
  position: Vector2
  zoom: number
  rotation: degrees
  bounds?: Rectangle
  
  follow(target: Entity, smoothness?: number)
  stopFollow()
  
  moveTo(position: Vector2, duration?: milliseconds)
  shake(intensity: number, duration: milliseconds)
  zoom(level: number, duration?: milliseconds)
  
  fadeOut(duration: milliseconds, color?: Color)
  fadeIn(duration: milliseconds)
  flash(color: Color, duration: milliseconds)
  
  // NOVO: Cutscene helpers
  pan(from: Vector2, to: Vector2, duration: milliseconds)
  focusOn(entity: Entity, zoomLevel?: number, duration?: milliseconds)
  cinematic(enabled: boolean)      // Barras de letterbox
}
```

---

## 3.2 ANIMATION

```typescript
animation AnimationID {
  frames: AssetPath[]
  fps: number
  loop: boolean
  
  play()
  pause()
  stop()
  reset()
  
  onComplete?: () => void
  onLoop?: () => void
  onFrame?: (frame: number) => void
}

tween {
  target: Entity
  property: string
  from: any
  to: any
  duration: milliseconds
  easing: EasingType              // linear | easeIn | easeOut | bounce | elastic | back
  delay?: milliseconds
  
  onUpdate?: (value: any) => void
  onComplete?: () => void
}

// NOVO: Sequência de tweens encadeados
tweenSequence {
  steps: TweenStep[]
  
  add(tween: Tween): this
  play()
  pause()
  stop()
  onComplete?: () => void
}
```

---

## 3.3 PARTICLES

```typescript
particles ParticleSystemID {
  emitter {
    position: Vector2
    rate: number
    lifetime: milliseconds
    continuous: boolean
    shape?: "point" | "line" | "circle" | "rect"
  }
  
  particle {
    sprite: AssetPath
    size: Vector2
    sizeOverLife?: Curve           // Cresce/diminui com o tempo
    color: Color
    colorOverLife?: Gradient       // Muda de cor ao longo do tempo
    opacity: 0..1
    velocity: Vector2
    velocityVariance?: Vector2
    acceleration: Vector2
    gravity: number
    rotation: degrees
    angularVelocity: degrees
    lifetime: milliseconds
    fadeOut: boolean
  }
  
  preset: ParticlePreset           // fire | smoke | sparkles | rain | snow | magic | blood | dust
  
  start()
  stop()
  burst(count: number)
}
```

---

# 🎬 PARTE 3B: CUTSCENE SYSTEM *(NOVO)*

```typescript
cutscene CutsceneID {
  // CONTROLE
  skippable: boolean
  pausable: boolean
  
  // ATORES (personagens que participam)
  actors: CharacterID[]
  
  // TIMELINE — sequência de ações
  timeline: CutsceneAction[] [
    
    // Mover câmera
    { at: 0, action: "camera.moveTo", params: { x: 400, y: 300, duration: 2000 } }
    
    // Aparecer personagem
    { at: 500, action: "spawn", params: { character: "villain", position: {x: 600, y: 400} } }
    
    // Falar
    { at: 1000, action: "say", params: { character: "villain", text: "Você veio tarde demais!" } }
    
    // Animação
    { at: 2000, action: "animate", params: { target: "villain", animation: "laugh" } }
    
    // Som
    { at: 2000, action: "playSound", params: { file: "evil_laugh.wav" } }
    
    // Efeito
    { at: 2500, action: "effect", params: { type: "flash", color: "red" } }
    
    // Fade
    { at: 4000, action: "fadeOut", params: { duration: 1000 } }
    
    // Ir para cena
    { at: 5000, action: "goToScene", params: { scene: "boss_arena" } }
  ]
  
  onStart?: () => void
  onComplete?: () => void
  onSkip?: () => void
}

// ATALHOS PARA CUTSCENES SIMPLES
cutscene SimpleIntro {
  characters: ["narrator"]
  
  steps: [
    say("narrator", "Era uma vez..."),
    wait(1000),
    say("narrator", "Um reino distante."),
    fadeOut(1000),
    goToScene("KingdomScene")
  ]
}

// API DE CUTSCENE
playCutscene(cutsceneID: CutsceneID)
stopCutscene()
pauseCutscene()
onCutsceneComplete(callback: () => void)

// FUNÇÕES HELPER DENTRO DE CUTSCENES
say(character: CharacterID, text: string, duration?: ms)
wait(duration: ms)
moveTo(character: CharacterID, position: Vector2, duration?: ms)
animate(target: Entity, animation: string)
fadeIn(duration: ms, color?: Color)
fadeOut(duration: ms, color?: Color)
showTitle(text: string, subtitle?: string, duration?: ms)
playSound(file: AssetPath)
stopSound(file: AssetPath)
goToScene(sceneID: SceneID)
lockInput()
unlockInput()
```

### **Cutscene Examples**

```typescript
// INTRO DO JOGO
cutscene GameIntro {
  skippable: true
  
  steps: [
    lockInput(),
    fadeIn(2000, "black"),
    showTitle("O Mistério da Mansão Calixto", "Um Conto de Aventura", 3000),
    wait(1000),
    say("narrator", "Anos atrás, o famoso detetive Calixto desapareceu sem deixar rastros..."),
    wait(2000),
    say("narrator", "Hoje, você recebeu uma carta misteriosa."),
    playSound("letter_open.wav"),
    showItem("mysterious_letter"),
    wait(2000),
    fadeOut(1000, "black"),
    goToScene("mansion_entrance"),
    unlockInput()
  ]
}

// BOSS ENCONTRA O PLAYER
cutscene BossReveal {
  actors: ["villain", "player"]
  skippable: false
  
  timeline: [
    { at: 0,    action: "camera.shake", params: { intensity: 5, duration: 500 } },
    { at: 500,  action: "playSound", params: { file: "dramatic_sting.wav" } },
    { at: 500,  action: "spawn", params: { character: "villain", position: {x: 500, y: 200} } },
    { at: 1000, action: "say", params: { character: "villain", text: "Impressionante. Chegou até aqui." } },
    { at: 3000, action: "say", params: { character: "player", text: "Acabou, Malkor. Sei de tudo." } },
    { at: 5000, action: "say", params: { character: "villain", text: "Sabe? Então morra sabendo." } },
    { at: 6000, action: "camera.focusOn", params: { entity: "villain", zoom: 1.5, duration: 500 } },
    { at: 7000, action: "startCombat", params: { enemy: "villain" } }
  ]
}
```

---

# ⚙️ PARTE 4: SISTEMAS CORE

## 4.1 FLAGS & VARIABLES

```typescript
flags {
  [key: string]: boolean
  set(key: string, value: boolean)
  get(key: string): boolean
  toggle(key: string)
  has(key: string): boolean
}

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
  save(slot?: number) {
    data = {
      player: player.serialize(),
      scene: currentScene,
      flags: flags,
      vars: vars,
      quests: quests,
      achievements: achievements,
      timestamp: now()
    }
    storage.save(slot, data)
  }
  
  load(slot: number) {
    data = storage.load(slot)
    if (data) {
      player.deserialize(data.player)
      goToScene(data.scene)
      flags = data.flags
      vars = data.vars
      quests = data.quests
      achievements = data.achievements
    }
  }
  
  autoSave(interval: milliseconds) {
    every interval {
      save(0)
    }
  }
  
  // NOVO: Save com thumbnail
  saveWithScreenshot(slot: number) {
    screenshot = captureScreen()
    save(slot, { ...data, thumbnail: screenshot })
  }
  
  // NOVO: Cloud save
  syncToCloud() {
    if (user.isLoggedIn) {
      cloud.save(user.id, currentSaveData)
    }
  }
}
```

---

## 4.3 UI SYSTEM

```typescript
ui {
  showMessage(text: string, duration?: milliseconds)
  showNotification(text: string, icon?: string)
  narrate(text: string)
  
  showChoice(question: string, options: string[]): Promise<number>
  
  showTextInput(prompt: string, maxLength?: number): Promise<string>
  showNumberInput(prompt: string, min?: number, max?: number): Promise<number>
  
  openInventory()
  closeInventory()
  
  openQuestLog()
  openJournal()
  addJournalEntry(title: string, text: string)
  
  openMenu(menuID: MenuID)
  closeMenu()
  
  showDialogueBox(character: CharacterID, text: string)
  hideDialogueBox()
  
  startCutscene()
  endCutscene()
  
  hud {
    show()
    hide()
    updateHealth(value: number)
    updateMana(value: number)
    updateGold(value: number)
    showCustomStat(label: string, value: number, max: number)
  }
  
  // NOVO: Tooltips
  showTooltip(text: string, position: Vector2)
  hideTooltip()
  
  // NOVO: Tutorial Overlay
  showTutorial(stepID: string)
  nextTutorialStep()
  skipTutorial()
  
  // NOVO: Popup de Achievement
  showAchievement(achievementID: AchievementID)
  
  // NOVO: Barra de progresso
  showProgressBar(label: string, current: number, max: number, duration?: ms)
  
  // NOVO: Mapa
  openMap()
  highlightOnMap(sceneID: SceneID, color?: Color)
}
```

---

## 4.4 AUDIO SYSTEM

```typescript
audio {
  playMusic(file: AssetPath, options?: {
    loop?: boolean
    volume?: 0..1
    fadeIn?: milliseconds
    crossfade?: boolean            // Troca suave com música atual
  })
  
  stopMusic(fadeOut?: milliseconds)
  pauseMusic()
  resumeMusic()
  
  playSound(file: AssetPath, options?: {
    volume?: 0..1
    pitch?: number
    pan?: -1..1
    position?: Vector2
    loop?: boolean
    id?: string                    // Para stopSound por ID
  })
  
  stopSound(fileOrID: string)
  
  // NOVO: Layers musicais
  addMusicLayer(file: AssetPath, volume: 0..1)
  removeMusicLayer(file: AssetPath)
  
  playVoice(file: AssetPath)
  stopVoice()
  
  setMasterVolume(volume: 0..1)
  setMusicVolume(volume: 0..1)
  setSfxVolume(volume: 0..1)
  setVoiceVolume(volume: 0..1)
  muteAll()
  unmuteAll()
}
```

---

## 4.5 TIME SYSTEM

```typescript
time {
  now(): milliseconds
  delta: milliseconds
  
  gameTime: milliseconds
  timeOfDay: TimeOfDay
  dayNumber: number
  
  advanceTime(amount: milliseconds)
  setTime(time: TimeOfDay)
  
  every(interval: milliseconds, callback: () => void)
  after(delay: milliseconds, callback: () => void)
  cancel(timerID: TimerID)         // Cancela timer
  
  schedule: {
    at(time: TimeOfDay, callback: () => void)
    daily(callback: () => void)
  }
  
  // NOVO: Formato legível
  format(time: TimeOfDay): string  // "14:30" ou "Tarde"
  
  // NOVO: Pausa narrativa
  pause()                          // Pausa o tempo do jogo
  resume()
}
```

---

# 🏆 PARTE 4B: ACHIEVEMENT SYSTEM *(NOVO)*

```typescript
achievement AchievementID {
  // METADADOS
  title: string
  description: string
  icon: AssetPath
  category: AchievementCategory   // story | exploration | combat | puzzle | collection | secret
  hidden?: boolean                  // Não aparece até ser desbloqueado
  
  // RARIDADE
  rarity: Rarity                   // common | uncommon | rare | legendary
  points?: number                  // Sistema de pontos (gamification)
  
  // CONDIÇÃO DE DESBLOQUEIO
  condition: () => boolean
  
  // PROGRESSO (para achievements graduais)
  progress?: {
    current: number
    required: number
    trackVar: string               // Variável que rastreia o progresso
  }
  
  // RECOMPENSA
  reward?: {
    gold?: number
    item?: ItemID
    title?: string                 // Título especial para o player
    cosmetic?: AssetPath           // Avatar, cor, etc.
  }
  
  // EVENTOS
  on unlock {
    ui.showAchievement(this)
    playSound("achievement.wav")
    analytics.track("achievement_unlocked", { id: this.id })
  }
}

// SISTEMA
achievements {
  all: Achievement[]
  unlocked: AchievementID[]
  
  check()                          // Verifica todas as condições
  unlock(id: AchievementID)        // Desbloqueia manualmente
  isUnlocked(id: AchievementID): boolean
  getProgress(id: AchievementID): number  // 0..1
  
  totalPoints: number
  completionPercent: number
}

// EXEMPLOS
achievement FirstSteps {
  title: "Primeiros Passos"
  description: "Entre na mansão pela primeira vez."
  icon: "icons/footprints.png"
  category: "story"
  rarity: "common"
  condition: () => flags.entered_mansion
}

achievement MasterDetective {
  title: "Detetive Mestre"
  description: "Resolva todos os puzzles sem usar dicas."
  icon: "icons/magnifier.png"
  category: "puzzle"
  rarity: "legendary"
  hidden: true
  condition: () => vars.hintsUsed == 0 && vars.puzzlesSolved >= 10
  reward: {
    title: "O Detetive"
    gold: 500
  }
}

achievement Collector {
  title: "Colecionador"
  description: "Colecione 50 itens."
  icon: "icons/bag.png"
  category: "collection"
  progress: {
    required: 50
    trackVar: "itemsCollected"
  }
  condition: () => player.progress.itemsCollected.length >= 50
}
```

---

# 📡 PARTE 4C: EVENT BUS *(NOVO)*

O Event Bus permite comunicação entre entidades sem acoplamento direto.

```typescript
// EMITIR EVENTO
emit(eventName: string, data?: any)

// ESCUTAR EVENTO
on(eventName: string, callback: (data: any) => void)

// UMA VEZ
once(eventName: string, callback: (data: any) => void)

// REMOVER LISTENER
off(eventName: string, callback: Function)

// EVENTOS BUILT-IN
events {
  // Cena
  "scene:enter"              // { sceneID, previousScene }
  "scene:exit"               // { sceneID, nextScene }
  "scene:firstVisit"         // { sceneID }
  
  // Jogador
  "player:levelUp"           // { level, stats }
  "player:death"             // { cause, scene }
  "player:heal"              // { amount, source }
  "player:damage"            // { amount, source }
  
  // Inventário
  "inventory:itemAdded"      // { item, quantity }
  "inventory:itemRemoved"    // { item, quantity }
  "inventory:full"           // {}
  
  // Quest
  "quest:started"            // { questID }
  "quest:objectiveComplete"  // { questID, objectiveID }
  "quest:completed"          // { questID, rewards }
  "quest:failed"             // { questID }
  
  // Diálogo
  "dialogue:started"         // { dialogueID }
  "dialogue:choiceMade"      // { dialogueID, choiceID }
  "dialogue:ended"           // { dialogueID }
  
  // Combat
  "combat:started"           // { enemies }
  "combat:ended"             // { result, loot }
  
  // Puzzle
  "puzzle:solved"            // { puzzleID, attempts }
  "puzzle:failed"            // { puzzleID }
  
  // Achievement
  "achievement:unlocked"     // { achievementID }
  
  // Tempo
  "time:dayChanged"          // { day }
  "time:timeOfDayChanged"    // { from, to }
  
  // Custom
  [customEvent: string]: any
}

// EXEMPLOS DE USO
// --- Em um objeto ---
object Torch {
  on destroy {
    emit("torch:extinguished", { position: this.position })
  }
}

// --- Em uma cena ---
scene DarkCorridor {
  on enter {
    on("torch:extinguished", () => {
      scene.lighting = "pitch_black"
      narrate("A última tocha se apaga. Escuridão total.")
    })
  }
}

// --- Sistema global ---
on("player:death", (data) => {
  vars.deaths++
  showGameOver()
})

on("quest:completed", (data) => {
  achievements.check()
})
```

---

# 🌍 PARTE 4D: LOCALIZAÇÃO / I18N *(NOVO)*

Essencial para o mercado educacional multilíngue.

```typescript
i18n {
  // IDIOMA ATUAL
  currentLocale: string            // "pt-BR" | "en-US" | "es-ES"
  
  // TEXTOS TRADUZIDOS
  strings: {
    [locale: string]: {
      [key: string]: string
    }
  }
  
  // OBTER TEXTO
  t(key: string, params?: object): string
  
  // MUDAR IDIOMA
  setLocale(locale: string)
  
  // FORMATOS
  formatNumber(n: number): string  // "1.000" ou "1,000"
  formatDate(d: Date): string
  formatCurrency(n: number): string
  
  // PLURALIZAÇÃO
  plural(count: number, singular: string, plural: string): string
}

// DEFININDO STRINGS
locale "pt-BR" {
  "door.locked":          "A porta está trancada."
  "door.unlocked":        "Porta destrancada!"
  "item.collected":       "Você obteve: {itemName}"
  "quest.started":        "Nova Quest: {questTitle}"
  "puzzle.hint":          "Dica {n}: {hintText}"
  "achievement.unlocked": "🏆 Conquista: {title}"
  "npc.greeting.formal":  "Bom dia, viajante."
}

locale "en-US" {
  "door.locked":          "The door is locked."
  "door.unlocked":        "Door unlocked!"
  "item.collected":       "You obtained: {itemName}"
  "quest.started":        "New Quest: {questTitle}"
  "puzzle.hint":          "Hint {n}: {hintText}"
  "achievement.unlocked": "🏆 Achievement: {title}"
  "npc.greeting.formal":  "Good day, traveler."
}

// USO NOS EVENTOS
object Door {
  on click {
    if (state.locked) {
      narrate(i18n.t("door.locked"))
    }
  }
}

item Coin {
  on collect {
    narrate(i18n.t("item.collected", { itemName: this.name }))
  }
}
```

---

# ♿ PARTE 4E: ACESSIBILIDADE *(NOVO)*

Crucial para uso educacional e inclusivo.

```typescript
accessibility {
  // VISUAL
  highContrast: boolean
  textSize: "small" | "medium" | "large" | "xlarge"
  colorBlindMode: "none" | "protanopia" | "deuteranopia" | "tritanopia"
  reduceMotion: boolean            // Menos animações
  
  // LEITOR DE TELA
  screenReader: {
    enabled: boolean
    announce(text: string)         // Anuncia via TTS
    describeScene(sceneID: SceneID): string
    describeObject(objectID: ObjectID): string
  }
  
  // TEXTO
  textToSpeech: {
    enabled: boolean
    voice: string
    rate: number                   // Velocidade
    speak(text: string)
    stop()
  }
  
  // CONTROLES
  keyboardNavigation: boolean
  subtitles: {
    enabled: boolean
    position: "top" | "bottom"
    fontSize: number
    background: boolean
  }
  
  // TEMPO
  pauseOnFocusLoss: boolean
  extendedDialogueTime: boolean    // Mais tempo para ler
  slowModeMultiplier: number       // 0.5 = tudo na metade da velocidade
  
  // CONTEÚDO
  contentWarnings: {
    violence: boolean
    flash: boolean
    horror: boolean
  }
}
```

---

# 📊 PARTE 4F: ANALYTICS SYSTEM *(NOVO)*

Fundamental para o produto educacional SaaS.

```typescript
analytics {
  // CONFIGURAÇÃO
  enabled: boolean
  sessionID: string
  userID?: string
  
  // TRACKING BÁSICO
  track(event: string, data?: object)
  
  // EVENTOS AUTOMÁTICOS (já rastreados pelo engine)
  autoTrack: {
    sceneVisits: boolean
    itemsCollected: boolean
    dialogueChoices: boolean
    puzzleAttempts: boolean
    questProgress: boolean
    sessionTime: boolean
    deaths: boolean
  }
  
  // RELATÓRIOS (para modo educacional)
  reports {
    // Progresso do aluno
    studentProgress(userID: string): {
      scenesVisited: number
      totalScenes: number
      puzzlesSolved: number
      totalPuzzles: number
      questsCompleted: number
      objectivesMet: string[]
      timeSpent: milliseconds
      lastPlayed: Date
    }
    
    // Relatório de turma (para professor)
    classReport(classID: string): {
      students: StudentProgress[]
      averageCompletion: number
      commonStuckPoints: string[]
      topPerformers: string[]
    }
    
    // Dificuldades (onde alunos travam)
    heatmap(): {
      [sceneID: string]: {
        avgTimeSpent: milliseconds
        dropoffRate: number        // % que sai sem completar
        commonActions: string[]
      }
    }
    
    // Objetivos educacionais
    learningObjectives(): {
      [objective: string]: {
        achieved: number           // % de jogadores
        avgTime: milliseconds
      }
    }
  }
  
  // EXPORTAR
  export(format: "json" | "csv"): string
}

// EXEMPLOS DE USO
puzzle HistoryPuzzle {
  learningObjective: "Causas da Revolução Francesa"
  
  on solve {
    analytics.track("learning_objective_met", {
      objective: this.learningObjective,
      attempts: state.attempts,
      hintsUsed: state.hintsUsed,
      timeSpent: state.timeSpent
    })
  }
}

scene BattleOfWaterloo {
  analytics: {
    trackTime: true
    learningObjective: "Identificar causas da derrota de Napoleão"
  }
  
  on exit {
    analytics.track("scene_completed", {
      scene: "BattleOfWaterloo",
      objectivesMet: flags.understood_flanking && flags.read_all_clues
    })
  }
}
```

---

# 🎬 PARTE 5: CONTROLES & LÓGICA

## 5.1 CONTROL FLOW

```typescript
if (condition) { }
when (condition) { }

match (value) {
  case pattern1: action1
  case pattern2: action2
  default: defaultAction
}

for item in collection { }
while (condition) { }
repeat (times) { }

await asyncFunction()
wait(milliseconds)
waitUntil(condition)
waitFor(event)

// NOVO: Guard (sai da função se condição falhar)
guard (condition) else {
  narrate("Condição não atendida.")
  return
}

// NOVO: Try/Catch para ações arriscadas
try {
  openLockedChest(chest)
} catch(error) {
  narrate("Algo deu errado.")
  log(error)
}
```

---

## 5.2 FUNCTIONS

```typescript
function functionName(param1: Type, param2: Type): ReturnType {
  return value
}

const func = (x, y) => x + y

on event(callback: () => void)

// NOVO: Funções assíncronas
async function fetchSceneData(sceneID: SceneID) {
  let data = await api.getScene(sceneID)
  return data
}

// NOVO: Função com timeout
function withTimeout(fn: Function, ms: number) {
  let timer = after(ms, () => { cancel(fn) })
  fn()
  cancel(timer)
}
```

---

## 5.3 QUERIES

```typescript
find(type: EntityType, filter?: (entity) => boolean)
findAll(type: EntityType)
findByName(name: string)
findByTag(tag: string)
findNearest(position: Vector2, type?: EntityType)
findInRadius(position: Vector2, radius: number)

// NOVO: Queries compostas
findWhere({ type: "door", state: "locked", scene: currentScene })
countWhere({ type: "enemy", alive: true })
anyWhere({ type: "fire", burning: true }): boolean
allWhere({ type: "candle", lit: true }): boolean
```

---

## 5.4 MATH & UTILS

```typescript
math {
  abs(x), floor(x), ceil(x), round(x)
  min(...values), max(...values)
  clamp(value, min, max)
  
  random(): 0..1
  randomInt(min, max)
  randomChoice(array)
  randomChance(probability: 0..1): boolean
  
  // NOVO: Seed para reprodutibilidade
  setSeed(seed: number)
  seededRandom(seed: number): number
  
  distance(p1: Vector2, p2: Vector2)
  angle(from: Vector2, to: Vector2)
  lerp(a, b, t)
  
  sin, cos, tan, atan2
  PI, TAU, E
  
  // NOVO: Curvas
  smoothstep(edge0: number, edge1: number, x: number): number
  bezier(p0, p1, p2, p3, t): number
}

string {
  concat, split, join
  substring, indexOf
  toUpperCase, toLowerCase
  replace, trim
  format(template: string, ...args)
  interpolate`Texto com ${variable}`
  
  // NOVO
  padStart(length: number, char?: string): string
  capitalize(): string
  truncate(maxLength: number, suffix?: string): string
}

array {
  push, pop, shift, unshift
  map, filter, reduce, find
  sort, reverse, shuffle
  first, last, isEmpty
  contains, indexOf
  
  // NOVO
  chunk(size: number): array[]    // Divide em grupos
  unique(): array                 // Remove duplicatas
  flatten(): array               // Achata arrays aninhados
  zip(other: array): array       // Combina dois arrays
  sum(): number
  average(): number
}
```

---

# 🎯 PARTE 6: EVENTOS GLOBAIS

## 6.1 GAME EVENTS

```typescript
on gameStart { }
on gameOver { }
on gamePause { }
on gameResume { }

on levelUp { }
on achievementUnlock(achievement: AchievementID) { }
on questComplete(quest: QuestID) { }

on keyPress(key: KeyCode) { }
on keyRelease(key: KeyCode) { }
on mouseClick(position: Vector2) { }
on mouseMove(position: Vector2) { }

on sceneChange(from: SceneID, to: SceneID) { }
on itemCollect(item: ItemID) { }
on itemUse(item: ItemID) { }
on dialogueStart(dialogue: DialogueID) { }
on dialogueEnd(dialogue: DialogueID) { }

// NOVOS
on playerDeath { }
on dayChanged(day: number) { }
on reputationChanged(faction: string, delta: number) { }
on cutsceneStart(id: CutsceneID) { }
on cutsceneEnd(id: CutsceneID) { }
on achievementUnlocked(id: AchievementID) { }
on sessionStart { analytics.startSession() }
on sessionEnd { analytics.endSession() }
```

---

# 🏆 PARTE 7: SISTEMAS AVANÇADOS

## 7.1 COMBAT SYSTEM

```typescript
combat {
  start(enemies: Character[])
  end()
  
  currentTurn: Character
  nextTurn()
  
  attack(attacker: Character, target: Character, weapon?: Item)
  defend(character: Character)
  useSkill(character: Character, skill: Skill, target?: Character)
  useItem(character: Character, item: Item, target?: Character)
  flee(character: Character): boolean
  
  calculateDamage(attacker, target, weapon?): number
  calculateHit(attacker, target): boolean
  
  applyStatus(character: Character, status: StatusEffect)
  removeStatus(character: Character, status: StatusEffect)
  
  // NOVO: Crítico
  isCriticalHit(attacker: Character): boolean
  criticalMultiplier: number
  
  // NOVO: Combo
  comboCount: number
  onCombo(count: number, callback: () => void)
  
  on combatStart { }
  on combatEnd(result: "victory" | "defeat" | "flee") { }
  on turnStart(character: Character) { }
  on damage(character: Character, amount: number) { }
  on death(character: Character) { }
  on criticalHit(attacker: Character, target: Character) { }
}
```

---

## 7.2 CRAFTING SYSTEM

```typescript
crafting {
  recipes: Recipe[] {
    id: string
    name: string
    ingredients: { [itemID: string]: quantity }
    result: ItemID
    resultQuantity: number
    requiredTool?: ItemID
    requiredSkill?: { skill: SkillType, level: number }
    craftTime?: milliseconds
    discoverable?: boolean         // Descoberta ao combinar itens
  }
  
  craft(recipeID: RecipeID): boolean
  
  learnRecipe(recipeID: RecipeID)
  hasRecipe(recipeID: RecipeID): boolean
  
  // NOVO: Descoberta automática
  tryAutoDiscover(items: ItemID[]): Recipe | null
  
  // NOVO: Qualidade baseada em skill
  calculateQuality(recipe: Recipe): "poor" | "normal" | "masterwork"
}
```

---

## 7.3 WEATHER SYSTEM

```typescript
weather {
  current: WeatherType
  intensity: 0..1
  
  set(type: WeatherType, intensity?: number, transition?: milliseconds)
  clear()
  
  affects {
    visibility: boolean
    lighting: boolean
    movement: boolean
    combat: boolean
    sound: boolean                 // NOVO: afeta volume ambiente
  }
  
  particles: ParticleSystem
  ambientSound?: SoundEffect
  
  // NOVO: Previsão
  forecast: WeatherType[]         // Próximos ciclos de tempo
  cycle(weathers: WeatherType[], interval: milliseconds)  // Alterna automaticamente
}
```

---

## 7.4 ECONOMY SYSTEM

```typescript
economy {
  currency: { name: string, symbol: string }
  
  calculatePrice(item: Item, merchant: Character): number
  
  buy(item: Item, merchant: Character): boolean
  sell(item: Item, merchant: Character): boolean
  
  // NOVO: Inflação e demanda
  marketDemand: { [itemID: string]: 0..2 }  // 1 = normal, >1 = caro
  applyInflation(rate: number)
  
  // NOVO: Negociação
  negotiate(item: Item, merchant: Character, offerPrice: number): boolean {
    if (player.skills.charisma >= merchant.charisma) {
      return true
    }
    return randomChance(0.3)
  }
}
```

---

## 7.5 SKILL SYSTEM *(NOVO)*

```typescript
skills {
  // DEFINIÇÃO DE SKILL
  [skillName: string]: Skill {
    name: string
    description: string
    maxLevel: number
    
    effects: {
      [level: number]: Effect[]
    }
    
    // Como aumentar
    gainXP(amount: number)
    levelUp()
    
    // Verificar
    check(difficulty: number): boolean  // Rola baseado no nível
    checkWithDice(sides: number, bonus?: number): boolean
  }
  
  // PREDEFINIDOS
  lockpicking: Skill {
    maxLevel: 5
    on use(lock: Object) {
      if (check(lock.difficulty)) {
        lock.open()
      } else {
        narrate("Não conseguiu abrir.")
        gainXP(5)  // Aprende com o erro
      }
    }
  }
  
  stealth: Skill {
    on activate {
      player.state.isStealthy = true
      npcs.filter(n => !n.combat.hostile).forEach(n => {
        n.detectionRadius *= (1 - level / maxLevel)
      })
    }
  }
  
  persuasion: Skill {
    on dialogueChoice(choice: Choice) {
      if (choice.type == "persuade") {
        let bonus = level * 5
        choice.successChance += bonus
      }
    }
  }
}
```

---

## 7.6 FACTION SYSTEM *(NOVO)*

```typescript
factions {
  [factionID: string]: Faction {
    name: string
    description: string
    color: Color
    icon: AssetPath
    
    // Reputação do player
    reputation: number             // -100 a +100
    
    // Níveis de reputação
    levels: {
      [-100]: "Inimigo Declarado"
      [-50]:  "Hostil"
      [0]:    "Neutro"
      [25]:   "Amigável"
      [50]:   "Honrado"
      [75]:   "Exaltado"
      [100]:  "Lendário"
    }
    
    // Reações ao player baseadas na reputação
    effects: {
      [level: string]: {
        priceMultiplier: number
        questsAvailable: QuestID[]
        dialogueOptions: string[]
        hostilesAttack: boolean
      }
    }
    
    // Relações entre facções
    relations: {
      [otherFactionID: string]: number  // -1 (guerra) a +1 (aliados)
    }
  }
  
  // MÉTODOS
  changeReputation(factionID: string, delta: number)
  getLevel(factionID: string): string
  areAllied(f1: string, f2: string): boolean
  areAtWar(f1: string, f2: string): boolean
}
```

---

# 📝 PARTE 8: TEMPLATES PRONTOS

## 8.1 COMPLETE GAME OBJECT EXAMPLES

### Porta Completa

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
  
  on examine {
    if (state.locked) {
      narrate("A porta está trancada. Há um buraco de fechadura.")
    } else {
      narrate("Uma porta de carvalho maciço.")
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
      case "bronze_key": unlock()
      case "lockpick": startMinigame("lockpicking")
      case "axe": damage(25)
      default: narrate("Isso não funciona aqui.")
    }
  }
  
  function unlock() {
    state.locked = false
    playSound("door_unlock.wav")
    narrate("*CLIQUE* A porta foi destrancada!")
    flags.main_door_unlocked = true
    emit("door:unlocked", { doorID: this.id })
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
    camera.shake(5, 200)
    if (state.health <= 0) { destroy() }
    else { narrate(`A porta está danificada (${state.health}/100)`) }
  }
  
  function destroy() {
    state.locked = false
    state.opened = true
    sprite = "doors/door_broken.png"
    playSound("wood_break.wav")
    narrate("A porta se quebra em pedaços!")
    emit("door:destroyed", { doorID: this.id })
  }
}
```

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
    faction: "guild_smiths"
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
  
  attributes { health: 200, strength: 18, charisma: 12 }
  
  mental {
    mood: "focused"
    relationship: { "player": 0 }
    personality: {
      traits: ["honesto", "trabalhador", "teimoso"]
      speakingStyle: "direto e grosseiro"
    }
  }
  
  behavior {
    schedule: [
      {time: "morning", location: "blacksmith", action: "hammering"},
      {time: "afternoon", location: "blacksmith", action: "hammering"},
      {time: "evening", location: "tavern", action: "drinking"}
    ]
  }
  
  shop {
    sells: ["iron_sword", "steel_axe", "chainmail"]
    buys: ["ore", "weapon", "armor"]
    priceMultiplier: 1.2
  }
  
  on click {
    if (relationship[player] >= 50) {
      startDialogue("blacksmith_friend")
    } else if (relationship[player] <= -20) {
      startDialogue("blacksmith_angry")
    } else {
      startDialogue("blacksmith_greeting")
    }
  }
  
  dialogue blacksmith_greeting {
    start: "intro"
    nodes {
      intro {
        speaker: "Blacksmith"
        text: "Bem-vindo à forja! Precisa de algo afiado?"
        next: [
          choice trade: "Quero ver suas armas" -> "show_shop"
          choice quest: "Ouvi que precisa de ajuda" -> "quest_intro"
          choice leave: "Só passando" -> "goodbye"
        ]
      }
      show_shop {
        onEnter { openShop(this) }
        next: "end"
      }
      quest_intro {
        speaker: "Blacksmith"
        text: "Ah sim... Me traga 5 barras de aço."
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
        text: "Até mais."
        next: "end"
      }
    }
  }
}
```

---

### Puzzle Completo

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
    { text: "Procure no quadro atrás da mesa", condition: () => state.attempts >= 1 },
    { text: "O ano está escrito no livro", condition: () => state.attempts >= 2 },
    { text: "Olhe a data na carta antiga", condition: () => examined("old_letter") }
  ]
  
  on attempt(code: string) {
    state.attempts++
    if (code == solution) {
      solve()
    } else {
      let correct = countCorrectDigits(code, solution)
      if (correct > 0) {
        narrate(`Você ouve ${correct} cliques suaves...`)
      } else {
        narrate("Nada acontece.")
      }
      
      if (state.attempts >= state.maxAttempts) {
        fail()
      }
    }
  }
  
  on solve {
    state.isSolved = true
    playSound("puzzle_solve.wav")
    playAnimation("safe_open")
    narrate("*CLIQUE* O cofre se abre!")
    
    let perfect = (state.attempts == 1 && state.hintsUsed == 0)
    if (perfect) {
      player.inventory.add("golden_key")
      player.experience += 100
      achievements.unlock("master_detective")
    } else {
      player.inventory.add("silver_key")
      player.experience += 50
    }
    
    flags.library_safe_open = true
  }
  
  on fail {
    narrate("❌ O cofre trava permanentemente!")
    playSound("alarm.wav")
    flags.library_safe_failed = true
    npc("librarian").attitude = "hostile"
  }
}
```

---

# 🎯 PARTE 9: REFERÊNCIA RÁPIDA PARA IA DIRECTOR

## 9.1 COMANDOS MAIS USADOS

```typescript
createObject({ name, type, position, sprite?, ses? })
createScene({ name, background, objects? })
createDialogue({ id, character, nodes })
createQuest({ title, objectives, rewards })
createCutscene({ id, steps })               // NOVO
createAchievement({ id, title, condition }) // NOVO

setFlag(key, value)
setVar(key, value)
emit(event, data?)                          // NOVO

narrate(text)
showChoice(question, options)

goToScene(sceneID)

giveItem(itemID, quantity?)
removeItem(itemID, quantity?)

playCutscene(id)                            // NOVO
unlockAchievement(id)                       // NOVO

analytics.track(event, data)               // NOVO
i18n.t(key, params?)                        // NOVO
```

---

## 9.2 PADRÕES COMUNS

### Porta com Chave
```typescript
object Door {
  state: "locked"
  on click {
    if (state == "locked") {
      if (player.has("key")) { state = "open"; narrate("Porta destrancada!") }
      else { narrate("Precisa de uma chave.") }
    } else { goToScene("NextRoom") }
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
  on click { startDialogue("shop_greeting") }
}
```

### Puzzle Básico
```typescript
puzzle SimpleCode {
  solution: "1234"
  on attempt(code) {
    if (code == solution) { solve() }
  }
  on solve { open("door") }
}
```

### Quest de Coleta
```typescript
quest FetchQuest {
  objectives: [{ type: "collect", target: "herb", required: 3 }]
  on complete { giveItem("potion") }
}
```

### Cutscene Rápida *(NOVO)*
```typescript
cutscene SimpleReveal {
  steps: [
    camera.focusOn("villain", 1.5, 500),
    say("villain", "Você não devia ter vindo aqui."),
    wait(2000),
    goToScene("boss_fight")
  ]
}
```

### Achievement Simples *(NOVO)*
```typescript
achievement Explorer {
  title: "Explorador"
  condition: () => player.progress.scenesVisited.length >= 10
}
```

---

## 9.3 MACROS PARA IA DIRECTOR

```typescript
@macro CreateInteractiveObject(name, description, behavior) {
  object Generated {
    name: $name
    description: $description
    
    @if (behavior == "door") {
      on click {
        if (state == "locked") { narrate("Trancado.") }
        else { goToScene("next") }
      }
    }
    @if (behavior == "container") {
      inventory: []
      on click { openInventory(this) }
    }
    @if (behavior == "decoration") {
      on examine { narrate($description) }
    }
    @if (behavior == "collectible") {
      on click { player.inventory.add(this.id); destroy(this) }
    }
  }
}

@macro CreateNPC(name, greeting, hasShop, hasQuest) {
  character Generated {
    name: $name
    dialogue default {
      nodes {
        greeting {
          speaker: $name
          text: $greeting
          next: [
            @if (hasShop) { choice "Ver loja" -> "shop" }
            @if (hasQuest) { choice "Precisa de ajuda?" -> "quest" }
            choice "Até logo" -> "end"
          ]
        }
      }
    }
  }
}

// NOVO: Macro de Área com Perigo
@macro CreateHazardZone(area, damage, interval, sound) {
  hotspot Generated {
    area: $area
    every $interval {
      if (playerInArea()) {
        player.health -= $damage
        playSound($sound)
        emit("hazard:damage", { amount: $damage })
      }
    }
  }
}

// NOVO: Macro de Quest Simples
@macro CreateSimpleQuest(title, collectTarget, amount, reward) {
  quest Generated {
    title: $title
    objectives: [
      { type: "collect", target: $collectTarget, required: $amount }
    ]
    on complete {
      giveItem($reward)
      narrate(`${title} - Completa!`)
    }
  }
}

// NOVO: Macro de Cutscene de Intro
@macro CreateSceneIntro(characterID, text, duration) {
  cutscene Generated {
    steps: [
      lockInput(),
      camera.focusOn($characterID, 1.2, 500),
      say($characterID, $text),
      wait($duration),
      unlockInput()
    ]
  }
}

// NOVO: Macro de Achievement de Coleta
@macro CreateCollectionAchievement(title, itemID, required) {
  achievement Generated {
    title: $title
    description: `Colete ${$required} ${$itemID}.`
    progress: {
      required: $required
      trackVar: "collected_" + $itemID
    }
    condition: () => vars["collected_" + $itemID] >= $required
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
    
    on command "examinar mesa" { narrate("Descrição da mesa...") }
    on command "n" or "norte" { goToScene("NextRoom") }
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
      on click { examine() }
    }
  }
}
```

### RPG com Combate
```typescript
game RPG {
  mode: "rpg"
  
  player {
    attributes { health: 100, mana: 50, level: 1 }
  }
  
  character Enemy {
    combat { hostile: true, health: 50, attackDamage: 10 }
    on death { dropLoot({ gold: 50, items: ["potion"] }) }
  }
}
```

### NOVO: Jogo Educacional
```typescript
game EducationalAdventure {
  mode: "educational"
  subject: "history"
  grade: "8th"
  locale: "pt-BR"
  
  analytics {
    enabled: true
    reportTo: "teacher_dashboard"
    trackLearningObjectives: true
  }
  
  accessibility {
    textToSpeech: true
    subtitles: true
    extendedDialogueTime: true
  }
  
  scene HistoricalTour {
    background: "paris_1789.png"
    analytics.learningObjective: "Causas da Revolução Francesa"
    
    object BastilleSign {
      on examine {
        showPicture("bastille.png")
        narrate("A Bastilha — símbolo do absolutismo real...")
        analytics.track("examined_bastille")
      }
    }
    
    puzzle RevolutionQuiz {
      type: "riddle"
      learningObjective: "Identificar causas sociais da Revolução"
      riddle: "O que alimentou a revolta popular além da fome?"
      solution: ["desigualdade", "impostos", "absolutismo"]
      
      on solve {
        player.experience += 50
        analytics.track("quiz_correct", { topic: "revolution_causes" })
        narrate("Correto! A desigualdade social foi uma das principais causas.")
      }
      
      on fail {
        showHint("Pense nas diferenças entre nobreza e camponeses...")
        analytics.track("quiz_incorrect", { topic: "revolution_causes" })
      }
    }
  }
}
```

### NOVO: Jogo Infantil
```typescript
game ChildAdventure {
  mode: "point_and_click"
  ageRange: "4-8"
  locale: "pt-BR"
  
  accessibility {
    textToSpeech: true
    textSize: "xlarge"
    subtitles: { enabled: true, fontSize: 24 }
    reduceMotion: false
    contentWarnings { violence: false, horror: false }
  }
  
  // Sem game over, sem falhas — apenas progresso
  gameSettings {
    allowFailure: false
    unlimitedHints: true
    celebrateSmallWins: true
    parentalReport: true
  }
  
  player {
    name: vars.childName  // Personalização — nome da criança
    avatar: vars.childAvatar
  }
  
  scene MagicForest {
    background: "forest_colorful.png"
    
    on enter {
      narrate(`Olá, ${player.name}! Bem-vindo à Floresta Mágica!`)
      playSound("cheerful_music.wav")
    }
    
    object FriendlyUnicorn {
      on click {
        animate("unicorn_wave")
        say("unicorn", `Oi ${player.name}! Pode me ajudar a encontrar minha estrela perdida?`)
        startQuest("find_star")
      }
    }
    
    puzzle ColorPuzzle {
      type: "sequence"
      solution: ["red", "blue", "yellow"]
      
      on solve {
        emit("celebrate")
        playSound("fanfare.wav")
        narrate("🌟 Você acertou! Incrível!")
        analytics.track("child_puzzle_solved", { childID: vars.childID })
      }
      
      // Nunca falha — sempre encoraja
      on attempt {
        if (!correct) {
          narrate("Quase! Tente de novo, você consegue! 💪")
        }
      }
    }
  }
}
```

---

# 🤖 PARTE 10: GUIA COMPLETO PARA IA DIRECTOR *(EXPANDIDO)*

## 10.1 PROTOCOLO DE CRIAÇÃO

Quando o usuário pedir qualquer elemento de jogo, siga este protocolo:

```
PASSO 1: ENTENDER A INTENÇÃO
  - O que o usuário quer criar?
  - Qual é o contexto narrativo?
  - Qual é o tipo de jogo? (educacional, RPG, p&c, infantil)
  - Qual o nível de detalhe pedido?

PASSO 2: CONSULTAR A BIBLIOTECA
  - Qual entidade usar? (scene, object, item, character, puzzle...)
  - Qual template se encaixa?
  - Há macro disponível?
  - Precisa de múltiplos sistemas integrados?

PASSO 3: GERAR CÓDIGO SES
  - Usar a sintaxe correta
  - Incluir todos os campos obrigatórios
  - Adicionar eventos relevantes
  - Integrar analytics se modo educacional
  - Usar i18n se multilíngue
  - Emitir eventos para integração via Event Bus

PASSO 4: INTEGRAR COM O PROJETO
  - Verificar se depende de outras entidades
  - Verificar conflitos de nomes/IDs
  - Adicionar ao arquivo correto

PASSO 5: CONFIRMAR COM O USUÁRIO
  - Resumir o que foi criado
  - Explicar como funciona
  - Sugerir próximos passos relacionados
```

---

## 10.2 RESPOSTA A PEDIDOS VAGOS

Quando o usuário pede algo vago, INFIRA e CRIE algo completo:

```
Usuário: "Crie uma cena de biblioteca"
IA deve criar:
  ✅ scene LibraryScene com background, música ambiente
  ✅ 3-5 objects (estantes, escrivaninha, vela, livros, escada)
  ✅ 1 NPC (bibliotecário opcional)
  ✅ 1 item coletável (chave ou livro especial)
  ✅ 1 puzzle relacionado (cifra, sequência de livros)
  ✅ Hotspot para saída
  ✅ Atmosfera sonora (páginas, corujas)
  ✅ onFirstEnter narrativa
```

---

## 10.3 CRIAÇÃO EM CAMADAS

Para pedidos complexos, crie em camadas:

```
CAMADA 1: Estrutura (scene, navigation)
CAMADA 2: Visual (background, objects, sprites)
CAMADA 3: Interação (events, dialogues)
CAMADA 4: Lógica (puzzles, quests, flags)
CAMADA 5: Polimento (sounds, particles, camera)
CAMADA 6: Analytics (se educacional)
CAMADA 7: Acessibilidade (se modo infantil/educacional)
```

---

## 10.4 INTEGRAÇÃO ENTRE SISTEMAS

A IA deve sempre pensar em como os sistemas se conectam:

```typescript
// EXEMPLO: Quest que afeta diálogo, economia e achievement
quest FindArtifact {
  on complete {
    // 1. Recompensa econômica
    player.gold += 500
    
    // 2. Reputação de facção
    factions.changeReputation("scholars_guild", +30)
    
    // 3. Desbloqueia diálogo
    npc("professor").dialogue.unlock("artifact_knowledge")
    
    // 4. Achievement
    achievements.check()
    
    // 5. Evento global (outros NPCs reagem)
    emit("artifact:found", { playerID: player.id })
    
    // 6. Analytics
    analytics.track("main_quest_completed", {
      timeSpent: vars.sessionTime,
      playStyle: vars.combatCount > vars.diplomacyCount ? "warrior" : "diplomat"
    })
    
    // 7. Próxima fase
    startCutscene("artifact_reveal")
  }
}
```

---

## 10.5 GERAÇÃO DE IMAGENS (SANA / GEMINI)

Quando precisar de assets visuais, use esta sintaxe para solicitar ao gerador de imagens:

```typescript
// Prompt para gerar background
@generateImage {
  type: "background"
  style: "point-and-click 2D, painted, warm lighting"
  scene: "Victorian library with tall bookshelves, candles, wooden desk"
  resolution: "1920x1080"
  format: "png"
  saveAs: "backgrounds/library.png"
}

// Prompt para gerar sprite
@generateImage {
  type: "sprite"
  style: "2D game character, pixel art OR hand-drawn"
  subject: "elderly male librarian with glasses, wearing vest"
  poses: ["idle", "talking", "pointing"]
  background: "transparent"
  saveAs: "characters/librarian.png"
}

// Prompt para gerar ícone de item
@generateImage {
  type: "item_icon"
  style: "inventory icon, 64x64, colored background"
  subject: "ancient bronze key with ornate handle"
  saveAs: "items/bronze_key.png"
}

// Prompt para gerar sequência de animação
@generateImageSequence {
  type: "animation"
  frames: 4
  subject: "candle flame flickering"
  style: "2D sprite, transparent background"
  fps: 8
  saveAs: "animations/candle_flame_{frame}.png"
}
```

---

## 10.6 EXEMPLOS DE PEDIDOS E RESPOSTAS

### Pedido: "Crie um mercador suspeito"

```typescript
character SuspiciousMerchant {
  identity {
    name: "Aldric, o Suspeito"
    title: "Vendedor de Raridades"
    description: "Olhos que evitam contato. Sempre sorrindo, nunca explicando."
    species: "human"
    faction: "thieves_guild"  // Afiliação secreta
  }
  
  visual {
    sprite: "characters/merchant_hooded.png"
    portrait: "portraits/merchant_suspicious.png"
    animations: {
      idle: { frames: ["merchant_idle_1.png", "merchant_idle_2.png"], fps: 1 }
      nervous: { frames: ["merchant_nervous.png"], fps: 4 }
      talk: { frames: ["merchant_talk.png"], fps: 3 }
    }
  }
  
  mental {
    mood: "guarded"
    trustLevel: 0
    personality: {
      traits: ["dissimulado", "ganancioso", "inteligente"]
      speakingStyle: "evasivo, muda de assunto rapidamente"
    }
    memory: {
      "knows_about_heist": false
      "bribed_by_player": false
    }
  }
  
  shop {
    sells: ["strange_potion", "lockpick_set", "forged_document"]
    buys: ["stolen_goods", "rare_gem"]
    priceMultiplier: 2.0  // Cobra caro
  }
  
  dialogue {
    defaultTree: "merchant_default"
  }
  
  dialogue merchant_default {
    start: "greeting"
    nodes {
      greeting {
        speaker: "SuspiciousMerchant"
        text: when player.reputation.thieves_guild >= 25 {
          "Ah... um amigo dos irmãos. Entre, entre."
        } when memory.bribed_by_player {
          "Você de novo. Ainda não falei nada, tá?"
        } otherwise {
          "Apenas um humilde vendedor de raridades. Nada de especial aqui."
        }
        
        next: [
          choice browse: "Quero ver o que tem" -> "show_goods"
          choice info: "Sei sobre o assalto" -> "confrontation"
          choice bribe: "[Subornar - 100 ouro] Preciso de informação" 
                       condition: () => player.gold >= 100
                       -> "bribe_attempt"
          choice leave: "Desculpe, engano meu" -> "end"
        ]
      }
      
      confrontation {
        speaker: "SuspiciousMerchant"
        text: "Não sei do que está falando. Agora por favor..."
        emotion: "nervous"
        animation: "nervous"
        
        condition: () => !flags.has_evidence_against_merchant
        
        next: [
          choice evidence: "Tenho provas" 
                          condition: () => flags.has_evidence_against_merchant
                          -> "caught"
          choice threaten: "[Intimidar] Melhor falar..."
                          condition: () => player.skills.intimidation >= 3
                          -> "intimidation_check"
          choice leave: "Está bem..." -> "end"
        ]
      }
      
      bribe_attempt {
        speaker: "SuspiciousMerchant"
        text: "*Pega o ouro e olha ao redor* ...O carregamento chega amanhã, porto sul. Pronto?"
        
        onEnter {
          player.gold -= 100
          memory.bribed_by_player = true
          flags.knows_smuggling_route = true
          relationship[player] += 15
        }
        
        next: "end"
      }
      
      caught {
        speaker: "SuspiciousMerchant"
        text: "*Visivelmente nervoso* Tudo bem... tudo bem. O que precisa?"
        emotion: "scared"
        
        onEnter {
          trustLevel = 80
          mood = "cooperative"
        }
        
        next: [
          choice demand_info: "Me conta tudo" -> "spill_secrets"
          choice recruit: "Trabalhe para mim" -> "recruitment"
        ]
      }
    }
  }
  
  // Reage a eventos globais
  on gameEvent("guards:patrol_nearby") {
    mood = "nervous"
    animation = "nervous"
    dialogue.defaultTree = "merchant_afraid"
  }
  
  on gameEvent("heist:exposed") {
    if (!memory.bribed_by_player) {
      goToScene("docks")  // Foge
      flags.merchant_fled = true
    }
  }
}
```

---

### Pedido: "Crie uma cena educacional sobre a Amazônia"

```typescript
scene AmazonExploration {
  meta {
    name: "Floresta Amazônica"
    description: "A maior floresta tropical do mundo, lar de milhões de espécies."
    type: "exterior"
    tags: ["natureza", "biodiversidade", "educacional"]
    chapter: 2
  }
  
  visual {
    background: "backgrounds/amazon_rainforest.png"
    lighting: "day"
    weather: "sunny"
    particles: ["tropical_birds_fly_by", "butterflies", "floating_pollen"]
    filters: []
  }
  
  audio {
    music: { file: "music/jungle_ambience.wav", loop: true, volume: 0.6 }
    ambient: [
      { file: "sounds/birds.wav", loop: true, volume: 0.4 },
      { file: "sounds/river.wav", loop: true, volume: 0.3 }
    ]
  }
  
  analytics {
    trackTime: true
    trackActions: true
    learningObjective: "Compreender a biodiversidade e importância da Amazônia"
  }
  
  entities {
    objects: [
      object InfoBoard_Biodiversity {
        name: "Placa: Biodiversidade"
        sprite: "objects/info_board.png"
        position: {x: 300, y: 400}
        
        on examine {
          showInfoCard({
            title: "A Amazônia em Números",
            facts: [
              "🌿 400 bilhões de árvores",
              "🦜 1.300 espécies de pássaros",
              "🐟 3.000 espécies de peixes",
              "💧 20% da água doce do planeta"
            ],
            image: "infographics/amazon_stats.png"
          })
          analytics.track("read_biodiversity_info")
          player.experience += 10
        }
      }
      
      object RiverSample {
        name: "Amostra de Água do Rio"
        sprite: "objects/water_sample.png"
        position: {x: 600, y: 500}
        
        on use {
          startMinigame("water_analysis_puzzle")
          analytics.track("started_water_analysis")
        }
      }
      
      object AncientTree {
        name: "Árvore Centenária"
        sprite: "objects/giant_tree.png"
        
        on examine {
          narrate("Esta árvore tem mais de 200 anos. Imagine o que ela testemunhou...")
          showTimeline("amazon_history_200_years")
          analytics.track("examined_ancient_tree")
          flags.examined_tree = true
        }
      }
    ]
    
    characters: [
      character IndigenousGuide {
        name: "Tupã"
        description: "Guardião indígena do conhecimento da floresta."
        
        dialogue guide_dialogue {
          start: "welcome"
          nodes {
            welcome {
              speaker: "Tupã"
              text: "Bem-vindo à nossa floresta, jovem explorador. O que deseja aprender?"
              next: [
                choice animals: "Fale sobre os animais" -> "about_animals"
                choice threats: "Quais são as ameaças?" -> "about_threats"
                choice culture: "Como vocês vivem aqui?" -> "about_culture"
              ]
            }
            
            about_animals {
              speaker: "Tupã"
              text: "A Amazônia abriga mais de 10% de todas as espécies do mundo. Cada planta, cada inseto tem seu papel."
              onEnter {
                showImage("animals_diversity.png")
                analytics.track("learned_about_animals")
              }
              next: [
                choice more_questions: "Tenho outra pergunta" -> "welcome"
                choice quiz: "Quero fazer o quiz!" -> "start_quiz"
              ]
            }
            
            about_threats {
              speaker: "Tupã"
              text: "Desmatamento, garimpo ilegal, queimadas... nossa floresta sofre. Mas cada pessoa que aprende pode fazer a diferença."
              emotion: "sad"
              onEnter {
                analytics.track("learned_about_threats")
                flags.learned_threats = true
              }
              next: "welcome"
            }
          }
        }
      }
    ]
  }
  
  puzzle AmazonQuiz {
    type: "riddle"
    learningObjective: "Identificar características e importância da Amazônia"
    
    questions: [
      {
        text: "Qual porcentagem da água doce do mundo está na Amazônia?",
        options: ["5%", "10%", "20%", "50%"],
        correct: 2,
        explanation: "A Amazônia contém aproximadamente 20% de toda a água doce do planeta!"
      },
      {
        text: "Quantas espécies de peixes existem na Amazônia?",
        options: ["500", "1.000", "3.000", "10.000"],
        correct: 2,
        explanation: "Com mais de 3.000 espécies, o rio Amazonas tem a maior diversidade de peixes do mundo."
      }
    ]
    
    on solve {
      narrate("🌟 Parabéns! Você é um especialista em Amazônia!")
      player.experience += 100
      achievements.unlock("amazon_expert")
      analytics.track("quiz_completed", {
        score: state.correctAnswers,
        total: questions.length
      })
    }
  }
  
  lifecycle {
    onFirstEnter {
      playCutscene("amazon_intro")
      narrate("Você chegou à maior floresta tropical do mundo.")
      analytics.track("scene_first_visit", { scene: "AmazonExploration" })
    }
    
    onExit {
      if (flags.examined_tree && flags.learned_threats) {
        narrate("Você aprendeu muito sobre a Amazônia hoje.")
        player.experience += 50
      }
    }
  }
}
```

---

## 10.7 CHECKLIST DE QUALIDADE

Antes de finalizar qualquer criação, verifique:

```
ENTIDADE BÁSICA:
□ ID único e descritivo
□ Nome e descrição completos
□ Tipo correto declarado
□ Visual definido (sprite/background)
□ Eventos principais implementados

NARRATIVA:
□ Texto tem personalidade e voz
□ Condições lógicas e consistentes
□ Consequências das ações definidas
□ Feedback ao jogador presente

INTEGRAÇÃO:
□ Flags setadas quando necessário
□ Analytics trackeado (se educacional)
□ Eventos emitidos para outros sistemas
□ Achievements verificados

ÁUDIO/VISUAL:
□ Sons relevantes referenciados
□ Animações definidas para estados principais
□ Particles/effects quando apropriado

ACESSIBILIDADE (se educacional/infantil):
□ Textos legíveis
□ TTS habilitado
□ Fallback para jogadores com dificuldades
□ Nunca puna — sempre encoraje

PERFORMANCE:
□ Não criar objetos desnecessários
□ Limpar listeners após uso
□ Usar pooling para partículas
```

---

# 🏁 CONCLUSÃO

## Esta biblioteca v3.0 contém:

✅ **Entidades:** Scene, Object, Item, Character, Hotspot — com versões expandidas  
✅ **Sistemas Base:** Player, Dialogue, Quest, Puzzle, Combat, Crafting  
✅ **Sistemas Novos:** Cutscene, Achievement, Event Bus, i18n, Accessibility, Analytics, Skill, Faction  
✅ **Controles:** Flags, Variables, Save/Load, UI, Audio, Time  
✅ **Visual:** Camera, Animation, Particles, Weather, Tweens  
✅ **Lógica:** Control Flow, Functions, Queries, Math  
✅ **Templates:** Objetos, NPCs, Puzzles prontos e expandidos  
✅ **Macros:** 6 macros incluindo Cutscene, Quest e Achievement  
✅ **Exemplos Completos:** Point&Click, RPG, Educacional, Infantil  
✅ **Guia IA:** Protocolo, criação em camadas, integração, geração de imagens, checklist  

---

## Para a Gemini AI Director:

**Esta é sua referência completa v3.0.**

Quando o usuário pedir:
1. Consulte esta biblioteca
2. Escolha os componentes apropriados
3. Gere código SES funcional e completo
4. Integre sistemas relacionados (analytics, events, achievements)
5. Adicione ao projeto
6. Confirme ao usuário com resumo claro

**Lembre-se sempre:**
- Modo educacional → sempre incluir analytics + accessibility
- Modo infantil → nunca punir, sempre encorajar, TTS habilitado
- Qualquer criação → emitir eventos via Event Bus para integração
- NPCs com personalidade → reagir a eventos globais

**VOCÊ AGORA TEM PODER TOTAL PARA CRIAR QUALQUER TIPO DE JOGO!** 🎮✨

---

**FIM DA BIBLIOTECA SES COMPLETA v3.0**
