
import json
import os
import uuid
import logging
from typing import List, Dict, Any, Optional
from google import genai
from backend.config.user_settings import get_gemini_model
from tools.ai_connectors.comfy_client import ComfyClient

logger = logging.getLogger(__name__)

class AIChoreographer:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.comfy = ComfyClient()

    def plan_scene(self, user_description: str) -> Dict[str, Any]:
        """
        Asks Gemini to break down the user description into a scene composition plan.
        """
        prompt = f"""
        You are an Art Director for a 2D Adventure Game (like Monkey Island).
        Analyze this user request: "{user_description}"
        
        Output a JSON object with this EXACT structure (no markdown):
        {{
            "positive_prompt": "A detailed detailed description of the background environment, high quality, 8k...",
            "negative_prompt": "text, watermark, blurry, distorted, sketch, low quality",
            "visual_style": "pixel art, 16-bit style", 
            "objects_to_extract": [
                {{
                    "name": "clock",
                    "description": "antique grandfather clock",
                    "animation_hint": "pendulum swinging" 
                }}
            ]
        }}
        """
        
        
        try:
            response = self.client.models.generate_content(
                model=get_gemini_model(),
                contents=prompt
            )
            clean_text = response.text.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_text)
        except Exception as e:
            logger.error(f"Gemini Planning Error: {e}")
            raise

    def generate_scene_art(self, prompt: str, project_path: str) -> str:
        """
        Orchestrates the creation of a scene background:
        1. Plans with Gemini
        2. Generates with ComfyUI
        3. Saves to project
        """
        plan = self.plan_scene(prompt)
        
        # Load ComfyUI workflow (this would normally be loaded from a json file)
        # For now, we assume a simple txt2img workflow structure
        # In a real impl, we'd load 'comfy_workflows/txt2img.json'
        
        # NOTE: This is a placeholder workflow construction. 
        # The user needs to provide the actual JSON export from ComfyUI for this to work 100%.
        # We will use a simplified structure here assuming the standard Default Workflow.
        workflow = self._build_txt2img_workflow(plan['positive_prompt'])
        
        logger.info(f"Sending prompt to ComfyUI: {plan['positive_prompt']}")
        response = self.comfy.queue_prompt(workflow)
        prompt_id = response['prompt_id']
        
        self.comfy.wait_for_execution(prompt_id)
        
        # Get history to find output filename
        history = self.comfy.get_history(prompt_id)
        # Traverse history to find the image output... 
        # (Simplified logic, assumes last node is SaveImage)
        outputs = history[prompt_id]['outputs']
        for node_id in outputs:
             images = outputs[node_id].get('images', [])
             if images:
                 img_data = images[0]
                 filename = img_data['filename']
                 folder_type = img_data['type']
                 subfolder = img_data['subfolder']
                 
                 image_bytes = self.comfy.get_image(filename, subfolder, folder_type)
                 
                 # Save to project
                 scene_id = str(uuid.uuid4())[:8]
                 rel_path = f"backgrounds/scene_{scene_id}.png"
                 full_path = os.path.join(project_path, rel_path)
                 os.makedirs(os.path.dirname(full_path), exist_ok=True)
                 
                 with open(full_path, "wb") as f:
                     f.write(image_bytes)
                     
                 return rel_path.replace("\\", "/")

        raise Exception("ComfyUI did not return an image.")

    def analyze_parts(self, object_name: str, image_path: str) -> List[Dict[str, Any]]:
        """
        Analyzes an image and identifies animatable parts (e.g., Pendulum in a Clock).
        Returns a list of parts with names, descriptions, and likely bounding boxes.
        """
        import PIL.Image
        img = PIL.Image.open(image_path)
        
        prompt = f"""
        Analyze this image of a "{object_name}".
        Identify specific sub-components that should be animated separately for a high-quality game feel.
        Example for a clock: the "Pendulum" or the "Clock Hands".
        
        For each part, provide:
        1. A name.
        2. A description of its animation behavior (e.g., "swinging", "rotating").
        3. A normalized bounding box [ymin, xmin, ymax, xmax] (0-1000) that ENCLOSES the entire part.
        
        CRITICAL: The bounding box must be large enough to contain the whole part even if some areas are thin (like a pendulum rod).
        
        Output a JSON list of objects:
        [
            {{
                "part_name": "Pendulum",
                "behavior": "swinging style animation",
                "bbox": [500, 450, 950, 550]
            }}
        ]
        """
        
        
        try:
            response = self.client.models.generate_content(
                model=get_gemini_model(),
                contents=[prompt, img]
            )
            clean_text = response.text.replace("```json", "").replace("```", "").strip()
            parts = json.loads(clean_text)
            logger.info(f"AI Detected Parts for {object_name}: {parts}")
            return parts
        except Exception as e:
            logger.error(f"Error analyzing parts: {e}")
            return []

    def analyze_animation(self, object_name: str, hint: Optional[str] = None) -> Dict[str, Any]:
        """
        Suggests animation parameters for an object based on its name and an optional hint.
        """
        hint_text = f" User hint: {hint}" if hint else ""
        prompt = f"""
        Suggest 2D game sprite animation parameters for an object named "{object_name}".{hint_text}
        
        Output a JSON object exactly like this:
        {{
            "description": "Short description of the movement",
            "suggested_frames": 4,
            "fps": 8,
            "loop": true
        }}
        """
        
        try:
            response = self.client.models.generate_content(
                model=get_gemini_model(),
                contents=prompt
            )
            clean_text = response.text.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_text)
        except Exception as e:
            logger.error(f"Error suggesting animation: {e}")
            return {{
                "description": "Animação simples",
                "suggested_frames": 3,
                "fps": 8,
                "loop": True
            }}

    def _build_txt2img_workflow(self, positive_prompt: str) -> Dict[str, Any]:
        """
        Helper: Returns a standard ComfyUI API JSON for txt2img.
        Node IDs (3, 4, 5, etc.) must match the User's ComfyUI default workflow.
        """
        return {
            "3": {
                "inputs": {
                    "seed": 156680208700286,
                    "steps": 20,
                    "cfg": 8,
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "denoise": 1,
                    "model": ["4", 0],
                    "positive": ["6", 0],
                    "negative": ["7", 0],
                    "latent_image": ["5", 0]
                },
                "class_type": "KSampler",
                "_meta": {
                    "title": "KSampler"
                }
            },
            "4": {
                "inputs": {
                    "ckpt_name": "v1-5-pruned-emaonly.ckpt"
                },
                "class_type": "CheckpointLoaderSimple",
                "_meta": {
                    "title": "Load Checkpoint"
                }
            },
            "5": {
                "inputs": {
                    "width": 512,
                    "height": 512,
                    "batch_size": 1
                },
                "class_type": "EmptyLatentImage",
                "_meta": {
                    "title": "Empty Latent Image"
                }
            },
            "6": {
                "inputs": {
                    "text": positive_prompt,
                    "clip": ["4", 1]
                },
                "class_type": "CLIPTextEncode",
                "_meta": {
                    "title": "CLIP Text Encode (Prompt)"
                }
            },
            "7": {
                "inputs": {
                    "text": "text, watermark",
                    "clip": ["4", 1]
                },
                "class_type": "CLIPTextEncode",
                "_meta": {
                    "title": "CLIP Text Encode (Negative Prompt)"
                }
            },
            "8": {
                "inputs": {
                    "samples": ["3", 0],
                    "vae": ["4", 2]
                },
                "class_type": "VAEDecode",
                "_meta": {
                    "title": "VAE Decode"
                }
            },
            "9": {
                "inputs": {
                    "filename_prefix": "ComfyUI",
                    "images": ["8", 0]
                },
                "class_type": "SaveImage",
                "_meta": {
                    "title": "Save Image"
                }
            }
        }
