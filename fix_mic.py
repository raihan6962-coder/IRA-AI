"""
Ira Mic Diagnostic & Fix Tool
Finds your microphone, tests it, and configures Ira to use it.
"""

import sys
import speech_recognition as sr


def list_mics():
    """List all available microphones."""
    print("\n" + "=" * 55)
    print("  SCANNING AVAILABLE MICROPHONES...")
    print("=" * 55)
    mics = sr.Microphone.list_microphone_names()
    if not mics:
        print("\n  ❌ No microphones found!")
        print("  Check: Is your mic plugged in?")
        print("  Check: Windows Settings > Privacy > Microphone")
        return []
    
    print(f"\n  Found {len(mics)} microphone(s):\n")
    for i, name in enumerate(mics):
        print(f"    [{i}] {name}")
    return mics


def test_mic(index):
    """Test a specific microphone."""
    try:
        r = sr.Recognizer()
        with sr.Microphone(device_index=index) as source:
            print(f"\n  🎤 Testing mic [{index}]...")
            print("  Say something (I'll listen for 3 seconds)...")
            r.adjust_for_ambient_noise(source, duration=0.5)
            audio = r.listen(source, timeout=5, phrase_time_limit=3)
            print("  ✅ Heard you! Trying to recognize...")
            try:
                text = r.recognize_google(audio, language="bn-BD")
                print(f"  ✅ Recognized: {text}")
                return True
            except:
                try:
                    text = r.recognize_google(audio, language="en-US")
                    print(f"  ✅ Recognized: {text}")
                    return True
                except:
                    print("  ⚠️  Heard but couldn't recognize (maybe too quiet)")
                    return True
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def main():
    print()
    print("  ╔══════════════════════════════════════════╗")
    print("  ║        IRA MIC DIAGNOSTIC TOOL           ║")
    print("  ╚══════════════════════════════════════════╝")
    
    mics = list_mics()
    if not mics:
        print("\n  🔧 Troubleshooting tips:")
        print("  1. Press Win + I → Privacy & Security → Microphone → ON")
        print("  2. Check if your mic is plugged in properly")
        print("  3. Try a different USB port")
        print("  4. Right-click speaker icon → Sound Settings → Input")
        print("  5. Buy a cheap USB microphone (under 500 taka)")
        print()
        return

    print("\n  Enter the mic NUMBER you want to test (or 'q' to quit): ", end="")
    try:
        choice = input().strip()
    except:
        choice = "q"
    
    if choice.lower() == "q":
        print("\n  OK, exiting.")
        return
    
    try:
        idx = int(choice)
        if idx < 0 or idx >= len(mics):
            print(f"\n  ❌ Invalid number. Choose 0-{len(mics)-1}")
            return
        test_mic(idx)
    except ValueError:
        print("\n  ❌ Please enter a NUMBER")
        return


if __name__ == "__main__":
    main()
