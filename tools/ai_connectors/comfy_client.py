
import websocket # type: ignore
import uuid
import json
import urllib.request
import urllib.parse
from typing import Dict, Any, Optional

class ComfyClient:
    def __init__(self, server_address="127.0.0.1:8188"):
        self.server_address = server_address
        self.client_id = str(uuid.uuid4())
        self.ws = None

    def queue_prompt(self, prompt: Dict[str, Any]) -> Dict[str, Any]:
        """
        Submits a prompt workflow to the ComfyUI server.
        """
        p = {"prompt": prompt, "client_id": self.client_id}
        data = json.dumps(p).encode('utf-8')
        req = urllib.request.Request(f"http://{self.server_address}/prompt", data=data)
        return json.loads(urllib.request.urlopen(req).read())

    def get_image(self, filename: str, subfolder: str, folder_type: str) -> bytes:
        """
        Retrieves an image from the ComfyUI server.
        """
        data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
        url_values = urllib.parse.urlencode(data)
        with urllib.request.urlopen(f"http://{self.server_address}/view?{url_values}") as response:
            return response.read()

    def get_history(self, prompt_id: str) -> Dict[str, Any]:
        """
        Gets the history of a specific prompt execution.
        """
        with urllib.request.urlopen(f"http://{self.server_address}/history/{prompt_id}") as response:
            return json.loads(response.read())
            
    def connect_ws(self):
        """Establishes WebSocket connection for status updates."""
        try:
            self.ws = websocket.WebSocket()
            self.ws.connect(f"ws://{self.server_address}/ws?clientId={self.client_id}")
        except Exception as e:
            print(f"Warning: Could not connect to ComfyUI WS: {e}")

    def wait_for_execution(self, prompt_id: str):
        """
        Waits for the prompt execution to complete via WebSocket.
        """
        if not self.ws:
            self.connect_ws()
            if not self.ws:
                return # Fallback or error if WS unavailable
        
        while True:
            out = self.ws.recv()
            if isinstance(out, str):
                message = json.loads(out)
                if message['type'] == 'executing':
                    data = message['data']
                    if data['node'] is None and data['prompt_id'] == prompt_id:
                        break # Execution finished
        
