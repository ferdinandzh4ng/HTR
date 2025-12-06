# Screen Finder

A Python tool that takes a screenshot of your screen, sends it to ChatGPT's vision API, and returns the coordinates of objects you're looking for.

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set your OpenAI API key:
```bash
export OPENAI_API_KEY="your-api-key-here"
```

Or create a `.env` file (not included in git) with:
```
OPENAI_API_KEY=your-api-key-here
```

## Usage

### As a Python function:

```python
from screen_finder import find_object_coordinates

# Find coordinates of a button
coords = find_object_coordinates("submit button")
if coords:
    x, y = coords
    print(f"Found at: ({x}, {y})")
```

### As a command-line tool:

```bash
python screen_finder.py "submit button"
python screen_finder.py "login button"
python screen_finder.py "close icon"
```

## How it works

1. Takes a screenshot of your entire screen using `pyautogui`
2. Encodes the screenshot as base64
3. Sends it to ChatGPT's vision API (gpt-4o) with a prompt asking for coordinates
4. Parses the response to extract the (x, y) coordinates
5. Returns the coordinates as a tuple

## Notes

- The function returns the center coordinates of the object
- If the object is not found, it returns `None`
- Make sure you have a valid OpenAI API key with access to vision models
- The default model is `gpt-4o` which supports vision

