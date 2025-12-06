import pyautogui
from anthropic import Anthropic
import base64
from io import BytesIO
import os
import dotenv
dotenv.load_dotenv()

def find_element_coordinates(description: str):
    """
    Find the coordinates of an element on the screen using Claude.
    Returns (x, y) tuple if found, None otherwise.
    """
    # 1. Capture screenshot
    screenshot = pyautogui.screenshot()
    
    # 2. Encode for Claude
    buffered = BytesIO()
    screenshot.save(buffered, format="PNG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode()
    
    # 3. Ask Claude to locate element
    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": img_base64
                    }
                },
                {
                    "type": "text",
                    "text": f"""Find the {description} on this screen. IMPORTANT: IGNORE ALL TERMINAL OUTPUT AND CODE BLOCKS.

CRITICAL: If looking for browser icons:
- Safari browser icon: Blue compass-like icon with red/white needle pointing northeast, says "Safari" underneath
- Comet browser icon: Colorful icon (often with comet/tail design), says "Comet" underneath
- Chrome browser icon: Colorful circular icon with red, yellow, green, blue sections, says "Chrome" underneath
- NOT Apple Maps (green icon with map design, says "Maps" underneath)
- Be very careful to distinguish browser icons from Apple Maps app

Return ONLY a JSON object with pixel coordinates:
{{"x": <pixel_x>, "y": <pixel_y>, "found": true/false}}"""
                }
            ]
        }]
    )
    
    # 4. Parse response
    import json
    import re
    
    # Get the response text
    response_text = response.content[0].text
    print(f"📝 Full Claude Response:\n{response_text}\n")
    
    # Extract JSON (handle markdown code blocks)
    content = response_text.strip()
    
    # Try to extract JSON from markdown
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()
    
    # Try to find JSON object with regex
    json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', content, re.DOTALL)
    if json_match:
        content = json_match.group()
    
    print(f"📋 Extracted JSON: {content}\n")
    
    try:
        result = json.loads(content)
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse JSON: {e}")
        print(f"Raw content was: {content}")
        return None
    
    if result.get("found", False):
        x = int(result["x"] * 1135/1100)
        y = int(result["y"] * 860/831)
        print(f"✅ Found at: ({x}, {y})")
        return (x, y)
    else:
        print("❌ Element not found")
        return None


def find_and_click_element(description: str):
    """Legacy function - finds coordinates and clicks. Use find_element_coordinates + Commands.execute_command instead."""
    coords = find_element_coordinates(description)
    if coords:
        x, y = coords
        pyautogui.click(x, y)
        return True
    return False

def parse_response(response_text):
    print("")

if __name__ == "__main__":
    find_and_click_element("Finder logo")