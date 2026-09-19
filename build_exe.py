"""Build script to compile the Desktop App into a standalone Windows .exe using PyInstaller."""
import os
import subprocess
import sys


def build_standalone_exe():
    print("=" * 60)
    print("BUILDING STANDALONE WINDOWS EXECUTABLE FOR CODECANYON")
    print("=" * 60)

    base_dir = os.path.abspath(os.path.dirname(__file__))
    icon_path = os.path.join(base_dir, "logo.ico")
    logo_path = os.path.join(base_dir, "logo.jpg")
    main_script = os.path.join(base_dir, "app_gui.py")

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--name", "WhatsApp_Telegram_Validator",
        "--icon", icon_path,
        "--add-data", f"{logo_path};.",
        "--add-data", f"{icon_path};.",
        "--collect-all", "customtkinter",
        "--collect-all", "phonenumbers",
        "--collect-all", "playwright",
        main_script,
    ]

    print("Running command:")
    print(" ".join(cmd))
    print("\nCompiling... (this may take 1-2 minutes)")

    result = subprocess.run(cmd, cwd=base_dir)
    if result.returncode == 0:
        exe_path = os.path.join(base_dir, "dist", "WhatsApp_Telegram_Validator.exe")
        print("\n" + "=" * 60)
        print("SUCCESS! Standalone Executable created at:")
        print(exe_path)
        print("=" * 60)
    else:
        print("\n[ERROR] Build failed with return code:", result.returncode)


if __name__ == "__main__":
    build_standalone_exe()
