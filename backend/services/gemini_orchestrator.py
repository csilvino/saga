from google import genai
from google.genai import types
from typing import Dict, Any, Optional
import json
import logging
import httpx
import asyncio
import time
from backend.config.user_settings import get_gemini_model
from backend.services.project_service import project_service # Import necessário para resolver caminhos
from fastapi import HTTPException

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SAGA_API_URL = "http://127.0.0.1:8070"

class GeminiAssetOrchestrator:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.recent_calls = {}
        
        self.tools = [
            types.Tool(function_declarations=[
                types.FunctionDeclaration(
                    name="set_scene_background",
                    description="Define a imagem de fundo para uma cena específica.",
                    parameters=types.Schema(
                        type="OBJECT",
                        properties={
                            "project_name": types.Schema(type="STRING"),
                            "scene_id": types.Schema(type="STRING"),
                            "background_path": types.Schema(type="STRING")
                        },
                        required=["project_name", "scene_id", "background_path"]
                    )
                ),
                types.FunctionDeclaration(
                    name="create_object_in_scene",
                    description="Cria um objeto de jogo completo em uma cena.",
                    parameters=types.Schema(
                        type="OBJECT",
                        properties={
                            "project_name": types.Schema(type="STRING"),
                            "scene_id": types.Schema(type="STRING"),
                            "object_name": types.Schema(type="STRING"),
                            "description": types.Schema(type="STRING"),
                            "object_type": types.Schema(type="STRING")
                        },
                        required=["project_name", "scene_id", "object_name", "description", "object_type"]
                    )
                ),
                types.FunctionDeclaration(
                    name="update_object_properties",
                    description="Modifica as propriedades de um objeto existente.",
                    parameters=types.Schema(
                        type="OBJECT",
                        properties={
                            "project_name": types.Schema(type="STRING"),
                            "scene_id": types.Schema(type="STRING"),
                            "object_id": types.Schema(type="STRING"),
                            "updates": types.Schema(type="OBJECT")
                        },
                        required=["project_name", "scene_id", "object_id", "updates"]
                    )
                ),
                types.FunctionDeclaration(
                    name="generate_image_and_set_as_background",
                    description="Processo completo para gerar uma imagem de fundo e aplicá-la a uma cena. Use esta ferramenta sempre que o usuário pedir para criar um background para uma cena.",
                    parameters=types.Schema(
                        type="OBJECT",
                        properties={
                            "project_name": types.Schema(type="STRING"),
                            "scene_id": types.Schema(type="STRING"),
                            "prompt": types.Schema(type="STRING", description="A descrição em linguagem natural do que a imagem deve conter."),
                            "width": types.Schema(type="INTEGER"),
                            "height": types.Schema(type="INTEGER"),
                            "reference_scene_id": types.Schema(type="STRING", description="O ID da cena de referência, se o usuário pedir para seguir o estilo de outra cena.")
                        },
                        required=["project_name", "scene_id", "prompt"]
                    )
                ),
                types.FunctionDeclaration(
                    name="create_scene",
                    description="Cria uma nova cena vazia no projeto.",
                    parameters=types.Schema(
                        type="OBJECT",
                        properties={
                            "project_name": types.Schema(type="STRING"),
                            "scene_name": types.Schema(type="STRING"),
                            "check_if_exists": types.Schema(type="BOOLEAN", description="Sempre defina como True para verificar se a cena já existe antes de criar.")
                        },
                        required=["project_name", "scene_name"]
                    )
                ),
                types.FunctionDeclaration(
                    name="generate_sprite_for_object",
                    description="Gera um sprite visual para um objeto específico.",
                    parameters=types.Schema(
                        type="OBJECT",
                        properties={
                            "project_name": types.Schema(type="STRING"),
                            "object_description": types.Schema(type="STRING"),
                            "object_type": types.Schema(type="STRING"),
                            "width": types.Schema(type="INTEGER"),
                            "height": types.Schema(type="INTEGER"),
                        },
                        required=["project_name", "object_description", "object_type"]
                    )
                ),
                types.FunctionDeclaration(
                    name="create_object_animation",
                    description="Gera um sprite sheet animado para um objeto e atualiza o objeto com a configuração de animação.",
                    parameters=types.Schema(
                        type="OBJECT",
                        properties={
                            "project_name": types.Schema(type="STRING"),
                            "object_id": types.Schema(type="STRING"),
                            "description": types.Schema(type="STRING", description="Descrição da animação (ex: 'pêndulo balançando', 'porta abrindo')."),
                            "frame_count": types.Schema(type="INTEGER", description="Número de frames para gerar (ex: 3).")
                        },
                        required=["project_name", "object_id", "description"]
                    )
                ),
                types.FunctionDeclaration(
                    name="delete_scene",
                    description="Deleta uma cena existente do projeto.",
                    parameters=types.Schema(
                        type="OBJECT",
                        properties={
                            "project_name": types.Schema(type="STRING"),
                            "scene_id": types.Schema(type="STRING")
                        },
                        required=["project_name", "scene_id"]
                    )
                ),
                types.FunctionDeclaration(
                    name="analyze_scene_background",
                    description=(
                        "Analisa a imagem de fundo de uma cena e retorna uma descrição detalhada do seu estilo visual. "
                        "IMPORTANTE: Após receber o resultado desta função, você DEVE imediatamente chamar "
                        "'create_scene' e depois 'generate_image_and_set_as_background' usando a descrição "
                        "de estilo retornada para compor o prompt da nova imagem. NÃO retorne apenas texto."
                    ),
                    parameters=types.Schema(
                        type="OBJECT",
                        properties={
                            "project_name": types.Schema(type="STRING"),
                            "scene_id": types.Schema(type="STRING")
                        },
                        required=["project_name", "scene_id"]
                    )
                ),
            ])
        ]
        
        model_name = get_gemini_model()
        logger.info(f"Inicializando chat com modelo: {model_name}")

        try:
            with open("docs/SAGA_LIBRARY_V3.md", "r", encoding="utf-8") as f:
                library_content = f.read()
        except Exception as e:
            logger.error(f"Erro ao ler SAGA_LIBRARY_V3.md: {e}")
            library_content = ""

        system_instruction = f"""
Você é o AI DIRECTOR do Saga Engine - um sistema completo de criação de jogos point-and-click.

# 🎯 SUA MISSÃO
Quando o usuário pedir algo, você deve usar as ferramentas disponíveis para EXECUTAR, não apenas descrever.

# ⚠️ REGRAS CRÍTICAS — LEIA COM ATENÇÃO

## REGRA 1: LOOP DE FERRAMENTAS
Você pode e DEVE chamar múltiplas ferramentas em sequência dentro de uma mesma resposta.
Após receber o resultado de uma ferramenta, analise-o e chame a próxima ferramenta necessária.
NUNCA retorne texto de conclusão se ainda há ações pendentes.

## REGRA 2: FLUXO OBRIGATÓRIO PARA "CRIAR CENA NO MESMO ESTILO"
Quando o usuário pedir uma nova cena seguindo o estilo de outra:

PASSO 1 → Chame `analyze_scene_background` na cena de referência
PASSO 2 → Leia a descrição retornada (style_description, elements, lighting, etc.)
PASSO 3 → Chame `create_scene` para criar a nova cena
PASSO 4 → Chame `generate_image_and_set_as_background` com:
           - prompt: TODOS os detalhes visuais do PASSO 2 + a nova cena pedida
           - reference_scene_id: O ID da cena de referência (MUITO IMPORTANTE)
PASSO 5 → Apenas ENTÃO responda ao usuário confirmando o que foi feito

## REGRA 3: NUNCA PARE APÓS analyze_scene_background
O resultado de `analyze_scene_background` é INSUMO para a próxima chamada.
Ele NUNCA é a resposta final. Sempre continue com create_scene e generate_image_and_set_as_background.

## REGRA 4: CONSTRUÇÃO DO PROMPT DE IMAGEM
Ao chamar `generate_image_and_set_as_background`, o prompt DEVE conter:
- O estilo visual da cena de referência (cores, iluminação, técnica de pintura)
- A descrição específica da nova cena pedida
- Elementos de atmosfera e composição

Exemplo de prompt BOM:
"Victorian point-and-click adventure background, warm candlelight atmosphere, 
painted illustration style with detailed wood textures and rich amber tones, 
library interior with tall bookshelves floor to ceiling, reading desk in center, 
spiral staircase to upper level, dusty particles in light beams, 1920x1080"

## REGRA 5: EVITAR DUPLICATAS
- SEMPRE use check_if_exists: true em create_scene
- Se a resposta retornar created: false, use o scene_id retornado (cena já existia)
- NUNCA chame a mesma ferramenta com os mesmos parâmetros duas vezes

## REGRA 6: MODELO DE IMAGEM
As ferramentas de geração de imagem internamente usam gemini-2.5-flash-preview-image-generation.
Você não precisa se preocupar com isso — apenas chame as ferramentas e elas cuidam do modelo correto.

---
{library_content}
"""

        self.chat = self.client.chats.create(
            model=model_name,
            config=types.GenerateContentConfig(
                tools=self.tools,
                system_instruction=system_instruction
            ),
            history=[]
        )
        logger.info("Orquestrador Gemini inicializado.")

    def _optimize_prompt_for_diffusion(self, natural_prompt: str, style_reference: str) -> Dict[str, str]:
        """Usa a Gemini para otimizar um prompt para geração de imagem."""
        logger.info(f"Otimizando prompt: '{natural_prompt}'")
        
        optimization_instruction = f"""
        Você é especialista em engenharia de prompts para geração de imagens.
        Converta a descrição abaixo em prompt positivo e negativo otimizados.

        Descrição: "{natural_prompt}"
        Estilo de referência: "{style_reference}"

        Retorne APENAS um JSON:
        {{
          "positive_prompt": "prompt detalhado em inglês com palavras-chave separadas por vírgula",
          "negative_prompt": "palavras-chave do que evitar"
        }}
        """
        
        response = self.client.models.generate_content(
            model=get_gemini_model(),
            contents=optimization_instruction
        )
        
        try:
            cleaned = response.text.replace("```json", "").replace("```", "").strip()
            return json.loads(cleaned)
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Erro ao parsear prompt otimizado: {e}")
            return {
                "positive_prompt": f"stylized 2D game background, point-and-click adventure, {natural_prompt}",
                "negative_prompt": "photorealistic, noisy, blurry, distorted, text, watermark"
            }

    def _get_scene_background_path(self, project_name: str, scene_id: str) -> Optional[str]:
        """Helper para encontrar o caminho da imagem de background de uma cena."""
        try:
            project = project_service.load_project(project_name)
            if scene_id not in project.get("scenes", {}):
                return None
            
            scene = project["scenes"][scene_id]
            background_path = scene.get("background")
            
            if not background_path:
                for obj in scene.get("objects", []):
                    if obj.get("type") == "background":
                        background_path = obj.get("sprite")
                        break
            
            if background_path and "?" in background_path:
                background_path = background_path.split("?")[0]
                
            return background_path
        except Exception as e:
            logger.error(f"Erro ao buscar background da cena {scene_id}: {e}")
            return None

    async def _execute_single_tool(self, function_call) -> Dict:
        """Executa uma única tool call e retorna o resultado."""
        name = function_call.name
        args = dict(function_call.args)
        
        logger.info(f"🛠️  Executando tool: {name}")
        logger.info(f"    Args: {json.dumps(args, indent=2, ensure_ascii=False)}")

        # Lógica especial para generate_image_and_set_as_background
        if name == 'generate_image_and_set_as_background':
            style_ref = args.get('style_reference', '2D painted point-and-click adventure game style')
            
            optimized_prompts = await asyncio.to_thread(
                self._optimize_prompt_for_diffusion,
                args['prompt'],
                style_ref
            )
            
            # Prepara os argumentos para a API
            api_args = {
                "project_name": args['project_name'],
                "prompt": optimized_prompts['positive_prompt'],
                "negative_prompt": optimized_prompts['negative_prompt'],
                "output_type": "backgrounds",
                "width": args.get('width', 1920),
                "height": args.get('height', 1080),
            }

            # Se houver uma cena de referência, busca o caminho da imagem dela
            if 'reference_scene_id' in args:
                ref_bg_path = self._get_scene_background_path(args['project_name'], args['reference_scene_id'])
                if ref_bg_path:
                    logger.info(f"🔗 Usando imagem de referência da cena {args['reference_scene_id']}: {ref_bg_path}")
                    api_args['reference_image_path'] = ref_bg_path
                else:
                    logger.warning(f"⚠️ Cena de referência {args['reference_scene_id']} não tem background válido.")

            api_response = await self.execute_api_tool("generate_image", api_args)

            if api_response.get("success"):
                background_path = api_response.get("image_path")
                logger.info(f"✅ Imagem gerada: {background_path}. Aplicando como background...")
                return await self.execute_api_tool("set_scene_background", {
                    "project_name": args['project_name'],
                    "scene_id": args['scene_id'],
                    "background_path": background_path,
                })
            else:
                logger.error(f"❌ Falha ao gerar imagem: {api_response}")
                return api_response

        # CORREÇÃO: Mapeamento para generate_sprite_for_object
        elif name == 'generate_sprite_for_object':
            # A API espera 'prompt', mas a tool envia 'object_description'
            api_args = {
                "project_name": args['project_name'],
                "prompt": f"Sprite isolado de {args['object_description']}, fundo transparente, estilo pixel art ou ilustração 2D de alta qualidade para jogo.",
                "negative_prompt": "fundo, background, cenário, texto, marca d'água",
                "output_type": "sprites",
                "width": args.get('width', 512),
                "height": args.get('height', 512),
            }
            return await self.execute_api_tool("generate_image", api_args)

        else:
            return await self.execute_api_tool(name, args)

    async def process_command(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Processa um comando com loop agentic completo.
        Continua executando tools até a Gemini retornar texto final.
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"📨 MENSAGEM DO USUÁRIO: {user_input}")

        full_prompt = user_input
        if context:
            context_str = json.dumps(context, indent=2, ensure_ascii=False)
            full_prompt = f"Contexto atual do projeto:\n{context_str}\n\nComando do usuário: {user_input}"

        try:
            # === TURNO INICIAL ===
            response = self.chat.send_message(full_prompt)
            
            all_tool_responses = []
            max_iterations = 10  # Segurança contra loops infinitos
            iteration = 0

            # === LOOP AGENTIC ===
            while iteration < max_iterations:
                iteration += 1
                logger.info(f"\n🔄 Iteração {iteration} do loop agentic")

                if not response.candidates or not response.candidates[0].content.parts:
                    logger.error("❌ Resposta sem candidates ou parts")
                    break

                parts = response.candidates[0].content.parts
                
                # Separar function_calls de texto
                function_calls = [p for p in parts if p.function_call and p.function_call.name]
                text_parts = [p.text for p in parts if hasattr(p, 'text') and p.text]

                logger.info(f"   Function calls encontradas: {len(function_calls)}")
                logger.info(f"   Text parts encontradas: {len(text_parts)}")

                # --- Sem function calls = Gemini terminou ---
                if not function_calls:
                    final_text = "".join(text_parts) if text_parts else None
                    
                    if final_text:
                        logger.info(f"✅ Gemini finalizou com texto: {final_text[:200]}...")
                    else:
                        logger.warning("⚠️ Gemini retornou sem function calls e sem texto (None)")
                        # Tentar dar um nudge para continuar
                        if iteration <= 2:
                            logger.info("🔁 Enviando nudge para continuar...")
                            response = self.chat.send_message(
                                "Continue executando os próximos passos necessários para completar a tarefa. "
                                "Chame as ferramentas restantes."
                            )
                            continue
                        final_text = "Ação executada. Verifique o canvas para ver o resultado."
                    
                    return {
                        "text_response": final_text,
                        "tool_responses": all_tool_responses
                    }

                # --- Executar todas as function calls desta rodada ---
                tool_response_parts = []
                
                for fc in function_calls:
                    logger.info(f"\n🤖 Gemini chamou: {fc.function_call.name}")
                    
                    result = await self._execute_single_tool(fc.function_call)
                    all_tool_responses.append({
                        "tool": fc.function_call.name,
                        "result": result
                    })
                    
                    logger.info(f"   Resultado: {json.dumps(result, indent=2, ensure_ascii=False)[:300]}")
                    
                    tool_response_parts.append(
                        types.Part.from_function_response(
                            name=fc.function_call.name,
                            response=result
                        )
                    )

                # Enviar TODOS os resultados de volta para a Gemini
                logger.info(f"\n📤 Enviando {len(tool_response_parts)} resultado(s) para a Gemini...")
                response = self.chat.send_message(tool_response_parts)
                
                # Continuar o loop — a Gemini vai decidir se chama mais tools ou encerra

            # Se chegou aqui, atingiu o limite de iterações
            logger.error(f"❌ Loop agentic atingiu limite de {max_iterations} iterações")
            return {
                "text_response": "Ação parcialmente executada. Verifique o canvas.",
                "tool_responses": all_tool_responses
            }

        except Exception as e:
            logger.error(f"Erro ao processar o comando: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Erro na comunicação com a IA: {str(e)}")

    async def execute_api_tool(self, name: str, args: Dict) -> Dict:
        """Executa uma chamada HTTP para a API interna do SAGA ENGINE."""
        
        # DEBOUNCE
        call_key = f"{name}:{json.dumps(args, sort_keys=True)}"
        current_time = time.time()
        
        if call_key in self.recent_calls:
            if (current_time - self.recent_calls[call_key]) < 2.0:
                logger.warning(f"⚠️ Chamada duplicada ignorada: {name}")
                return {"success": True, "message": "Operação já executada recentemente", "duplicate": True}
        
        self.recent_calls[call_key] = current_time
        self.recent_calls = {k: v for k, v in self.recent_calls.items() if (current_time - v) < 10.0}

        tool_map = {
            "create_scene":                  "/api/scenes/create",
            "set_scene_background":          "/api/scenes/set-background",
            "create_object_in_scene":        "/api/objects/create",
            "update_object_properties":      "/api/objects/update",
            "generate_image":                "/api/genai/generate-image",
            "generate_sprite_for_object":    "/api/genai/generate-image",
            "create_object_animation":       "/api/genai/animate-object", # Adicionado
            "extract_sprite_from_scene":     "/api/genai/extract-high-quality",
            "list_assets":                   "/api/tools/list-assets",
            "delete_scene":                  "/api/scenes/",
            "delete_object":                 "/api/objects/",
            "analyze_scene_background":      "/api/genai/analyze-scene",
        }
        
        endpoint = tool_map.get(name)
        if not endpoint:
            logger.warning(f"Ferramenta desconhecida: {name}")
            return {"error": f"Ferramenta '{name}' não implementada."}

        async with httpx.AsyncClient() as client:
            try:
                if name == 'create_scene' and 'check_if_exists' not in args:
                    args['check_if_exists'] = True

                if name in ['delete_scene', 'delete_object']:
                    response = await client.delete(
                        f"{SAGA_API_URL}{endpoint}", params=args, timeout=120.0
                    )
                else:
                    response = await client.post(
                        f"{SAGA_API_URL}{endpoint}", json=args, timeout=120.0
                    )
                
                if response.status_code == 409:
                    logger.warning(f"Conflito (409) para '{name}': {response.text}")
                    return response.json()

                response.raise_for_status()
                result = response.json()
                logger.info(f"✅ API '{name}' retornou: {str(result)[:200]}")
                return result
                
            except httpx.HTTPStatusError as e:
                logger.error(f"Erro HTTP em '{name}': {e.response.status_code} - {e.response.text}")
                return {"error": f"Erro na API: {e.response.status_code}", "details": e.response.text}
            except Exception as e:
                logger.error(f"Erro inesperado em '{name}': {e}")
                return {"error": str(e)}