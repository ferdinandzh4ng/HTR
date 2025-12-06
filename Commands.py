"""
Command Executor - Execute pyautogui commands and take screenshots
"""
import pyautogui
import os
from datetime import datetime
from typing import Optional, Tuple
import sys
import subprocess
import platform


# Create screenshots directory if it doesn't exist
SCREENSHOTS_DIR = "screenshots"
if not os.path.exists(SCREENSHOTS_DIR):
    os.makedirs(SCREENSHOTS_DIR)


def take_screenshot() -> str:
    """
    Takes a screenshot and saves it locally with a timestamp.
    
    Returns:
        Path to the saved screenshot file
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"screenshot_{timestamp}.png"
    filepath = os.path.join(SCREENSHOTS_DIR, filename)
    
    screenshot = pyautogui.screenshot()
    screenshot.save(filepath)
    print(f"Screenshot saved: {filepath}")
    return filepath


def execute_command(command: str, x: Optional[int] = None, y: Optional[int] = None, 
                   text: Optional[str] = None, scroll_amount: Optional[int] = None,
                   key: Optional[str] = None) -> bool:
    """
    Executes a pyautogui command based on the command string.
    
    Args:
        command: The command to execute (e.g., "left click", "right click", "scroll", etc.)
        x: X coordinate (required for click commands)
        y: Y coordinate (required for click commands)
        text: Text to type (required for "type" command)
        scroll_amount: Amount to scroll (optional, defaults to 3)
        key: Key name to press (required for "press" command)
    
    Returns:
        True if command executed successfully, False otherwise
    """
    command_lower = command.lower().strip()
    
    try:
        if command_lower == "left click" or command_lower == "click":
            if x is None or y is None:
                print("Error: x and y coordinates required for click command")
                return False
            pyautogui.click(x, y)
            print(f"Left clicked at ({x}, {y})")
            
        elif command_lower == "right click":
            if x is None or y is None:
                print("Error: x and y coordinates required for right click command")
                return False
            pyautogui.rightClick(x, y)
            print(f"Right clicked at ({x}, {y})")
            
        elif command_lower == "middle click":
            if x is None or y is None:
                print("Error: x and y coordinates required for middle click command")
                return False
            pyautogui.middleClick(x, y)
            print(f"Middle clicked at ({x}, {y})")
            
        elif command_lower == "double click":
            if x is None or y is None:
                print("Error: x and y coordinates required for double click command")
                return False
            pyautogui.doubleClick(x, y)
            print(f"Double clicked at ({x}, {y})")
            
        elif command_lower == "scroll" or command_lower == "scroll down":
            scroll = scroll_amount if scroll_amount is not None else 3
            pyautogui.scroll(-scroll)
            print(f"Scrolled down {scroll} units")
            
        elif command_lower == "scroll up":
            scroll = scroll_amount if scroll_amount is not None else 3
            pyautogui.scroll(scroll)
            print(f"Scrolled up {scroll} units")
            
        elif command_lower == "type":
            pyautogui.write(text)
            print(f"Typed: {text}")
            
        elif command_lower == "volume up":
            # Volume up - use system command for macOS, keyboard shortcut for others
            if platform.system() == "Darwin":  # macOS
                subprocess.run(["osascript", "-e", "set volume output volume (output volume of (get volume settings) + 10)"])
            else:
                try:
                    pyautogui.press('volumeup')
                except:
                    # Fallback: try keyboard shortcut
                    pyautogui.hotkey('fn', 'f12') if platform.system() != "Darwin" else None
            print("Volume up")
            
        elif command_lower == "volume down":
            # Volume down - use system command for macOS, keyboard shortcut for others
            if platform.system() == "Darwin":  # macOS
                subprocess.run(["osascript", "-e", "set volume output volume (output volume of (get volume settings) - 10)"])
            else:
                try:
                    pyautogui.press('volumedown')
                except:
                    # Fallback: try keyboard shortcut
                    pyautogui.hotkey('fn', 'f11') if platform.system() != "Darwin" else None
            print("Volume down")
            
        elif command_lower == "type" or command_lower == "type text":
            if text is None:
                print("Error: text parameter required for type command")
                return False
            pyautogui.write(text, interval=0.05)
            print(f"Typed: {text}")
            
        elif command_lower == "press":
            if key is None:
                print("Error: key parameter required for press command")
                print("Usage: press <key_name>")
                print("Example: press enter, press escape, press tab, press space")
                return False
            pyautogui.press(key.lower())
            print(f"Pressed key: {key}")
            
        elif command_lower == "move mouse" or command_lower == "move":
            if x is None or y is None:
                print("Error: x and y coordinates required for move mouse command")
                return False
            pyautogui.moveTo(x, y)
            print(f"Mouse moved to ({x}, {y})")
            
        elif command_lower == "drag":
            if x is None or y is None:
                print("Error: x and y coordinates required for drag command")
                return False
            pyautogui.dragTo(x, y, duration=0.5)
            print(f"Dragged to ({x}, {y})")
        
        elif command_lower == "open tab" or command_lower == "new tab":
            # Open new tab: Ctrl+T (Windows/Linux) or Cmd+T (macOS)
            if platform.system() == "Darwin":  # macOS
                pyautogui.keyDown('command')
                pyautogui.press('t')
                pyautogui.keyUp('command')
            else:
                pyautogui.keyDown('ctrl')
                pyautogui.press('t')
                pyautogui.keyUp('ctrl')
            print("Opened new tab")
        
        elif command_lower == "close tab":
            # Close tab: Ctrl+W (Windows/Linux) or Cmd+W (macOS)
            if platform.system() == "Darwin":  # macOS
                pyautogui.keyDown('command')
                pyautogui.press('w')
                pyautogui.keyUp('command')
            else:
                pyautogui.keyDown('ctrl')
                pyautogui.press('w')
                pyautogui.keyUp('ctrl')
            print("Closed tab")
        
        else:
            print(f"Error: Unknown command '{command}'")
            print("Supported commands: left click, right click, middle click, double click,")
            print("  scroll, scroll up, volume up, volume down, type, press <key>,")
            print("  move mouse, drag, open tab, close tab")
            return False
        
        return True
        
    except Exception as e:
        print(f"Error executing command: {e}")
        return False


def parse_command_line():
    """
    Parses command line arguments and executes the command.
    Expected format:
    python screen_finder.py <command> [x] [y] [--text "text"] [--scroll N] [--key "key"]
    """
    if len(sys.argv) < 2:
        print("Usage: python screen_finder.py <command> [x] [y] [--text \"text\"] [--scroll N] [--key \"key\"]")
        print("\nCommands:")
        print("  left click, right click, middle click, double click - requires x, y")
        print("  scroll, scroll up - optional --scroll N (default: 3)")
        print("  volume up, volume down")
        print("  type - requires --text \"text to type\"")
        print("  press - requires --key \"key_name\" (e.g., enter, escape, tab, space, etc.)")
        print("  move mouse, drag - requires x, y")
        print("  open tab, close tab - keyboard shortcuts (Ctrl+T/Ctrl+W or Cmd+T/Cmd+W on macOS)")
        print("\nExamples:")
        print("  python screen_finder.py left_click 100 200")
        print("  python screen_finder.py type --text \"Hello World\"")
        print("  python screen_finder.py scroll --scroll 5")
        print("  python screen_finder.py volume_up")
        print("  python screen_finder.py press --key enter")
        sys.exit(1)
    
    command = sys.argv[1].replace("_", " ")
    x = None
    y = None
    text = None
    scroll_amount = None
    key = None
    
    # Parse arguments
    i = 2
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == "--text" and i + 1 < len(sys.argv):
            text = sys.argv[i + 1]
            i += 2
        elif arg == "--scroll" and i + 1 < len(sys.argv):
            try:
                scroll_amount = int(sys.argv[i + 1])
                i += 2
            except ValueError:
                print(f"Error: --scroll requires an integer value")
                sys.exit(1)
        elif arg == "--key" and i + 1 < len(sys.argv):
            key = sys.argv[i + 1]
            i += 2
        elif arg.isdigit():
            if x is None:
                x = int(arg)
            elif y is None:
                y = int(arg)
            i += 1
        else:
            i += 1
    
    # Execute command
    success = execute_command(command, x, y, text, scroll_amount, key)
    
    if success:
        # Take screenshot after command execution
        take_screenshot()
    else:
        sys.exit(1)


if __name__ == "__main__":
    parse_command_line()

