import speech_recognition as sr
import threading
import time
import queue

TASK_DURATION = 5
COOLDOWN_TIME = 5

command_queue = queue.Queue()
is_processing = False


def run_gemini_task(command):
    print(f"\n▶ Processing: '{command}'")
    time.sleep(TASK_DURATION)
    print("✓ Task complete")


def task_processor():
    global is_processing
    while True:
        command = command_queue.get()
        is_processing = True
        
        run_gemini_task(command)
        
        print(f"⏸ Cooldown: {COOLDOWN_TIME}s...")
        time.sleep(COOLDOWN_TIME)
        
        is_processing = False
        print("🎤 Ready\n")
        command_queue.task_done()


def callback(recognizer, audio):
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
    recognizer = sr.Recognizer()
    microphone = sr.Microphone()
    
    recognizer.energy_threshold = 4000
    recognizer.dynamic_energy_threshold = True
    recognizer.pause_threshold = 0.8
    recognizer.phrase_threshold = 0.3
    recognizer.non_speaking_duration = 0.5

    with microphone as source:
        print("Calibrating microphone...")
        recognizer.adjust_for_ambient_noise(source, duration=2)
    
    print("✓ Voice system active\n🎤 Ready\n")

    stop_listening = recognizer.listen_in_background(microphone, callback, phrase_time_limit=10)
    
    processor_thread = threading.Thread(target=task_processor, daemon=True)
    processor_thread.start()

    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        stop_listening(wait_for_stop=False)
        print("\n\nShutting down...")


if __name__ == "__main__":
    main()