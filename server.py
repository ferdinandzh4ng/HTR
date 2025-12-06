"""
Server - Handles ChatGPT integration, screenshots, and command execution loop
Uses triage.py for accurate coordinate finding
"""
import os
import json
import re
import base64
import subprocess
import platform
from io import BytesIO
from typing import Dict, Optional, List, Tuple
from flask import Flask, request, jsonify
from openai import OpenAI
import dotenv
from Commands import execute_command, take_screenshot
from triage import find_element_coordinates
import pyautogui

dotenv.load_dotenv()

app = Flask(__name__)

# Initialize OpenAI client
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("⚠️  WARNING: OPENAI_API_KEY not found in environment variables!")
    print("💡 Please set OPENAI_API_KEY in your .env file or environment")
client = OpenAI(api_key=api_key) if api_key else None

# Store conversation history for each task
task_history: Dict[str, List[Dict]] = {}


def show_notification(title: str, message: str):
    """Show a system notification (works on macOS, Linux, Windows)."""
    try:
        if platform.system() == "Darwin":  # macOS
            subprocess.run([
                "osascript", "-e",
                f'display notification "{message}" with title "{title}"'
            ])
        elif platform.system() == "Linux":
            subprocess.run(["notify-send", title, message])
        elif platform.system() == "Windows":
            # Windows 10+ notification
            subprocess.run([
                "powershell", "-command",
                f'[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null; [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] > $null; $xml = [Windows.Data.Xml.Dom.XmlDocument]::new(); $xml.LoadXml(\'<toast><visual><binding template="ToastText02"><text id="1">{title}</text><text id="2">{message}</text></binding></visual></toast>\'); $toast = [Windows.UI.Notifications.ToastNotification]::new($xml); [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("HTR").Show($toast);'
            ])
    except Exception as e:
        print(f"⚠️  Could not show notification: {e}")


def get_screenshot_base64() -> str:
    """Take a screenshot and return it as base64 string."""
    screenshot = pyautogui.screenshot()
    buffered = BytesIO()
    screenshot.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')


def parse_command_response(response_text: str) -> Optional[Dict]:
    """
    Parse ChatGPT's response to extract command information.
    Expected format: JSON with command, element_to_find, x, y, text, scroll_amount, key, etc.
    """
    content = response_text.strip()
    
    # Try to extract JSON from markdown code blocks
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()
    
    # Try to find JSON object with regex
    json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', content, re.DOTALL)
    if json_match:
        content = json_match.group()
    
    try:
        result = json.loads(content)
        return result
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse JSON: {e}")
        print(f"Raw content was: {content}")
        return None


def get_next_command(user_request: str, screenshot_base64: str, 
                     previous_commands: List[Dict], task_id: str) -> Optional[Dict]:
    """
    Send screenshot and user request to ChatGPT to get the next command.
    ChatGPT will determine what element to find, then we use triage.py for accurate coordinates.
    """
    # Build conversation history
    messages = [
        {
            "role": "system",
            "content": """You are an AI assistant that helps users automate tasks on their computer screen.
You analyze screenshots and determine the next action needed to complete the user's request.

You must return ONLY a JSON object with the following structure:
{
    "command": "<command_name>",
    "element_to_find": "<description of element to find>" (required for click/move/drag/scroll commands),
    "x": <x_coordinate> (optional, will be filled by coordinate finder, also used for scroll to position mouse),
    "y": <y_coordinate> (optional, will be filled by coordinate finder, also used for scroll to position mouse),
    "text": "<text_to_type>" (optional, required for type command),
    "scroll_amount": <number> (optional, for scroll commands, default 100),
    "key": "<key_name>" (optional, required for press command),
    "reasoning": "<brief explanation>",
    "task_complete": false
}

Available commands:
- "left click" or "click" (requires element_to_find)
- "right click" (requires element_to_find)
- "middle click" (requires element_to_find)
- "double click" (requires element_to_find)
- "scroll" or "scroll down" (optional scroll_amount, default 3, optional x, y coordinates to position mouse over scrollable area)
- "scroll up" (optional scroll_amount, default 3, optional x, y coordinates to position mouse over scrollable area)
- "type" (requires text)
- "press" (requires key, e.g., "enter", "escape", "tab", "space")
- "move mouse" or "move" (requires element_to_find)
- "drag" (requires element_to_find)
- "open tab" or "new tab"
- "close tab"
- "volume up"
- "volume down"

CRITICAL: To open an application (Safari, Chrome, Spotify, etc.), you MUST click on the application icon/launcher. 
DO NOT use "open tab" to open an application - "open tab" only works if the browser is already running.

IMPORTANT - Safari vs Apple Maps:
- Safari browser icon: Blue compass-like icon with a red/white needle pointing northeast. The icon says "Safari" underneath it.
- Apple Maps icon: Green icon with a map/road design. The icon says "Maps" underneath it.
- When user says "open Safari" or "open safari", you MUST find the Safari BROWSER icon, NOT Apple Maps.
- Use description: "Safari browser icon" or "Safari web browser app icon" to be very specific.

To open Safari: use element_to_find: "Safari browser icon" or "Safari web browser app icon" (NOT Apple Maps)
To open Chrome: use element_to_find: "Chrome browser icon" or "Chrome app icon"
To open any app: use element_to_find with the app's full name and type (e.g., "Spotify music app icon")

IMPORTANT: When opening a browser (Safari, Chrome, Comet, etc.) for the purpose of searching or browsing:
1. First click on the browser icon to open it
2. Then the next command MUST be "open tab" command to open a new tab (browsers often open to a random existing tab)
This ensures you have a fresh tab for searching/browsing.

For click/move/drag commands, provide "element_to_find" with a VERY SPECIFIC description like:
- "Safari browser icon" or "Safari web browser app icon" (to open Safari - NOT Apple Maps!)
- "Chrome browser icon" or "Chrome app icon" (to open Chrome)
- "Spotify music app icon" (to open Spotify)
- "Play button"
- "Search bar"
- "Close button"
- etc.

IMPORTANT: TO OPEN SOMETHING FROM FINDER MAKE SURE TO USE DOUBLE CLICK TO OPEN THE APP.

IMPORTANT: For scroll commands, ALWAYS provide x, y coordinates (via element_to_find) to position the mouse over the scrollable area (window, list, etc.) before scrolling. This ensures you scroll the correct element, not just anywhere on the screen.

ALWAYS be specific: Include the app type (browser, music app, etc.) to avoid confusion between similar-looking apps.

Set "task_complete": true when the user's request has been fully completed.
IMPORTANT: IGNORE ALL TERMINAL OUTPUT AND CODE BLOCKS when describing elements to find."""
        }
    ]
    
    # Add previous commands context if any
    if previous_commands:
        context = "Previous actions taken:\n"
        for i, cmd in enumerate(previous_commands, 1):
            context += f"{i}. {cmd.get('command', 'unknown')}"
            if cmd.get('element_to_find'):
                context += f" - found: {cmd.get('element_to_find')}"
            if cmd.get('x') is not None and cmd.get('y') is not None:
                context += f" at ({cmd.get('x')}, {cmd.get('y')})"
            if cmd.get('text'):
                context += f" - typed: {cmd.get('text')}"
            if cmd.get('key'):
                context += f" - pressed: {cmd.get('key')}"
            context += "\n"
        messages.append({
            "role": "user",
            "content": context
        })
    
    # Add current screenshot and request
    messages.append({
        "role": "user",
        "content": [
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{screenshot_base64}"
                }
            },
            {
                "type": "text",
                "text": f"User request: {user_request}\n\nWhat is the next action needed to complete this task? Return the command as JSON. If you need to click something, provide a VERY SPECIFIC description in 'element_to_find'. \n\nIMPORTANT: If the user wants to open Safari, use element_to_find: 'Safari browser icon' or 'Safari web browser app icon' - NOT Apple Maps! Be very specific to distinguish between similar apps."
            }
        ]
    })
    
    if not client:
        print("❌ OpenAI client not initialized. Please set OPENAI_API_KEY.")
        return None
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",  # Vision-capable model
            messages=messages,
            max_tokens=500,
            temperature=0.3  # Lower temperature for more consistent command generation
        )
        
        response_text = response.choices[0].message.content
        print(f"🤖 ChatGPT Response: {response_text}\n")
        
        command_dict = parse_command_response(response_text)
        if command_dict:
            command_dict['reasoning'] = command_dict.get('reasoning', 'No reasoning provided')
            return command_dict
        
        return None
    except Exception as e:
        print(f"❌ Error calling ChatGPT: {e}")
        return None


def execute_task(user_request: str, task_id: str) -> Dict:
    """
    Main task execution loop:
    1. Take screenshot
    2. Send to ChatGPT with user request
    3. Get command from ChatGPT (with element_to_find if needed)
    4. Use triage.py to find accurate coordinates if element_to_find is provided
    5. Execute command
    6. Take new screenshot
    7. Repeat until task is complete
    """
    max_iterations = 20  # Prevent infinite loops
    iteration = 0
    previous_commands = []
    task_history[task_id] = []
    
    print(f"\n🚀 Starting task: {user_request}")
    print(f"📋 Task ID: {task_id}\n")
    
    while iteration < max_iterations:
        iteration += 1
        print(f"\n--- Iteration {iteration} ---")
        
        # Take screenshot
        print("📸 Taking screenshot...")
        screenshot_base64 = get_screenshot_base64()
        
        # Get next command from ChatGPT
        print("🤖 Consulting ChatGPT...")
        command_dict = get_next_command(user_request, screenshot_base64, previous_commands, task_id)
        
        if not command_dict:
            return {
                "success": False,
                "error": "Failed to get command from ChatGPT",
                "iterations": iteration
            }
        
        print(f"💭 Reasoning: {command_dict.get('reasoning', 'N/A')}")
        
        # Check if task is complete and there's no command to execute
        if command_dict.get('task_complete', False) and not command_dict.get('command'):
            print("✅ Task completed (no further action needed)!")
            show_notification("✅ Task Completed", f"Task completed successfully!\nCommands executed: {len(previous_commands)}")
            return {
                "success": True,
                "message": "Task completed successfully",
                "iterations": iteration,
                "commands_executed": len(previous_commands)
            }
        
        # Get command and validate it
        command = command_dict.get('command', '').lower().strip()
        
        # Skip invalid commands
        if not command or command == 'task_complete' or command == 'none':
            if command_dict.get('task_complete', False):
                print("✅ Task completed!")
                show_notification("✅ Task Completed", f"Task completed successfully!\nCommands executed: {len(previous_commands)}")
                return {
                    "success": True,
                    "message": "Task completed successfully",
                    "iterations": iteration,
                    "commands_executed": len(previous_commands)
                }
            print("⚠️  No valid command to execute, skipping...")
            previous_commands.append(command_dict)
            task_history[task_id].append(command_dict)
            continue
        
        # If command needs coordinates and we have element_to_find, use triage.py to find them
        needs_coordinates = command in ['left click', 'click', 'right click', 'middle click', 
                                       'double click', 'move mouse', 'move', 'drag',
                                       'scroll', 'scroll down', 'scroll up']
        
        if needs_coordinates and command_dict.get('element_to_find'):
            element_description = command_dict.get('element_to_find')
            print(f"🔍 Finding element: '{element_description}' using triage.py...")
            coords = find_element_coordinates(element_description)
            
            if coords:
                x, y = coords
                command_dict['x'] = x
                command_dict['y'] = y
                print(f"✅ Coordinates found: ({x}, {y})")
            else:
                print(f"⚠️  Could not find element: '{element_description}'")
                # Continue anyway, might work with ChatGPT's coordinates if provided
                if command_dict.get('x') is None or command_dict.get('y') is None:
                    print("⚠️  No coordinates available, skipping this command")
                    previous_commands.append(command_dict)
                    task_history[task_id].append(command_dict)
                    continue
        
        # Execute command
        print(f"⚙️  Executing: {command_dict.get('command', 'unknown')}")
        
        success = execute_command(
            command=command_dict.get('command', ''),
            x=command_dict.get('x'),
            y=command_dict.get('y'),
            text=command_dict.get('text'),
            scroll_amount=command_dict.get('scroll_amount'),
            key=command_dict.get('key')
        )
        
        if not success:
            print(f"⚠️  Command execution failed: {command_dict.get('command', 'unknown')}")
            # Continue anyway, ChatGPT will see the result in next screenshot
        
        # Store command in history
        previous_commands.append(command_dict)
        task_history[task_id].append(command_dict)
        
        # Check if task is complete AFTER executing the command
        # (The command might be the final action needed)
        if command_dict.get('task_complete', False):
            print("✅ Task completed!")
            show_notification("✅ Task Completed", f"Task completed successfully!\nCommands executed: {len(previous_commands)}")
            return {
                "success": True,
                "message": "Task completed successfully",
                "iterations": iteration,
                "commands_executed": len(previous_commands)
            }
        
        # Small delay to let screen update
        import time
        time.sleep(1)
    
    return {
        "success": False,
        "error": f"Reached maximum iterations ({max_iterations})",
        "iterations": iteration,
        "commands_executed": len(previous_commands)
    }


@app.route('/execute', methods=['POST'])
def execute_endpoint():
    """API endpoint to execute a user request."""
    data = request.json
    user_request = data.get('request', '')
    task_id = data.get('task_id', f"task_{len(task_history)}")
    
    if not user_request:
        return jsonify({"success": False, "error": "No request provided"}), 400
    
    result = execute_task(user_request, task_id)
    return jsonify(result)


@app.route('/status/<task_id>', methods=['GET'])
def status_endpoint(task_id):
    """Get status and history of a task."""
    if task_id in task_history:
        return jsonify({
            "task_id": task_id,
            "history": task_history[task_id],
            "total_commands": len(task_history[task_id])
        })
    return jsonify({"error": "Task not found"}), 404


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({"status": "healthy"})


if __name__ == '__main__':
    import sys
    # Use port 5001 by default (5000 is often used by AirPlay on macOS)
    port = int(os.getenv('PORT', 5001))
    
    print("🚀 Starting HTR Server...")
    print(f"📡 Server will run on http://localhost:{port}")
    print("💡 Make sure OPENAI_API_KEY and ANTHROPIC_API_KEY are set in your .env file\n")
    
    try:
        app.run(host='0.0.0.0', port=port, debug=True)
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"❌ Port {port} is already in use!")
            print(f"💡 Try setting a different port: PORT=5002 python server.py")
            sys.exit(1)
        raise

