import os
import subprocess
import sys
from pathlib import Path

VENV_DIR = ".venv"


def run(cmd):
    print(f"> {' '.join(cmd)}")
    subprocess.check_call(cmd)


def main():
    python = sys.executable
    venv_path = Path(VENV_DIR)

    # 1. Create venv if it doesn't exist
    if not venv_path.exists():
        run([python, "-m", "venv", VENV_DIR])
    else:
        print("✔ venv already exists")

    # 2. Determine venv python path
    if os.name == "nt":  # Windows
        venv_python = venv_path / "Scripts" / "python.exe"
    else:  # Linux / macOS / Raspberry Pi
        venv_python = venv_path / "bin" / "python"

    # 3. Upgrade pip
    run([str(venv_python), "-m", "pip", "install", "--upgrade", "pip"])

    # 4. Install requirements.txt if present
    if Path("requirements.txt").exists():
        run([str(venv_python), "-m", "pip", "install", "-r", "requirements.txt"])

    # 5. Install project in editable mode
    run([str(venv_python), "-m", "pip", "install", "-e", "."])

    print("\n✅ Setup complete!")
    print(f"To activate the venv:")
    if os.name == "nt":
        print(rf"  .\{VENV_DIR}\Scripts\activate")
    else:
        print(f"  source {VENV_DIR}/bin/activate")


if __name__ == "__main__":
    main()
