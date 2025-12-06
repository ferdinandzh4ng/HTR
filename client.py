"""
Client - Speech recognition that communicates with the server
"""
import os
import subprocess
import platform
import speech_recognition as sr
import threading
import time
import queue
import requests
import uuid

SERVER_URL = os.getenv("SERVER_URL", "http://localhost:5001")
TASK_DURATION = 5
COOLDOWN_TIME = 2

command_queue = queue.Queue()
is_processing = False


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


def send_request_to_server(user_request: str):
    """Send user request to server and handle response."""
    global is_processing
    
    task_id = str(uuid.uuid4())
    print(f"\n📤 Sending request to server: '{user_request}'")
    print(f"🆔 Task ID: {task_id}")
    
    try:
        response = requests.post(
            f"{SERVER_URL}/execute",
            json={
                "request": user_request,
                "task_id": task_id
            },
            timeout=300  # 5 minute timeout for long tasks
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                commands_executed = result.get('commands_executed', 0)
                iterations = result.get('iterations', 0)
                print(f"\n✅ Task completed successfully!")
                print(f"📊 Executed {commands_executed} commands in {iterations} iterations")
                show_notification("✅ Task Completed", f"'{user_request}'\nCompleted successfully!")
            else:
                error_msg = result.get('error', 'Unknown error')
                commands_executed = result.get('commands_executed', 0)
                print(f"\n⚠️  Task ended with: {error_msg}")
                print(f"📊 Executed {commands_executed} commands")
                show_notification("⚠️ Task Ended", f"'{user_request}'\n{error_msg}")
        else:
            print(f"\n❌ Server error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print(f"\n❌ Cannot connect to server at {SERVER_URL}")
        print("💡 Make sure server.py is running!")
    except requests.exceptions.Timeout:
        print(f"\n⏱️  Request timed out (task took too long)")
    except Exception as e:
        print(f"\n❌ Error: {e}")


def check_server_health():
    """Check if server is running."""
    try:
        response = requests.get(f"{SERVER_URL}/health", timeout=2)
        return response.status_code == 200
    except:
        return False


def task_processor():
    """Process commands from the queue."""
    global is_processing
    
    while True:
        command = command_queue.get()
        is_processing = True
        
        print(f"\n▶ Processing: '{command}'")
        send_request_to_server(command)
        
        print(f"\n⏸ Cooldown: {COOLDOWN_TIME}s...")
        time.sleep(COOLDOWN_TIME)
        
        is_processing = False
        print("🎤 Ready for next command\n")
        command_queue.task_done()


def callback(recognizer, audio):
    """Callback for speech recognition."""
    if is_processing:
        return
    
    try:
        text = recognizer.recognize_google(audio)
        if text.strip():
            print(f"🎙 Heard: {text}")
            command_queue.put(text)
    except sr.UnknownValueError:
        pass
    except sr.RequestError:
        print("⚠️ Speech service error")


def main():
    """Main function to start the client."""
    # Check server health
    print("🔍 Checking server connection...")
    if not check_server_health():
        print(f"❌ Cannot connect to server at {SERVER_URL}")
        print("💡 Please start server.py first:")
        print("   python server.py")
        return
    print("✅ Server is running!\n")
    
    # Setup speech recognition
    recognizer = sr.Recognizer()
    microphone = sr.Microphone()
    
    recognizer.energy_threshold = 4000
    recognizer.dynamic_energy_threshold = True
    recognizer.pause_threshold = 0.8
    recognizer.phrase_threshold = 0.3
    recognizer.non_speaking_duration = 0.5

    with microphone as source:
        print("🎤 Calibrating microphone...")
        recognizer.adjust_for_ambient_noise(source, duration=2)
    
    print("✓ Voice system active")
    print("🎤 Ready - speak your command!\n")
    print("💡 Example commands:")
    print("   - 'Open Spotify and play a song'")
    print("   - 'Open Chrome and search for Python'")
    print("   - 'Click on the settings icon'\n")

    stop_listening = recognizer.listen_in_background(
        microphone, 
        callback, 
        phrase_time_limit=15  # Allow longer phrases for complex commands
    )
    
    processor_thread = threading.Thread(target=task_processor, daemon=True)
    processor_thread.start()

    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        stop_listening(wait_for_stop=False)
        print("\n\n🛑 Shutting down...")


if __name__ == "__main__":
    main()

