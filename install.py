import os
import subprocess
import sys
import platform
import urllib.request
import zipfile

RCLONE_URL_WIN = "https://downloads.rclone.org/rclone-current-windows-amd64.zip"

def install_python_deps():
    subprocess.run([sys.executable, "-m", "pip", "install",
                    "psutil", "tqdm"], check=True)

def install_rclone():
    if os.path.exists("rclone.exe"):
        print("rclone ya instalado")
        return

    print("Descargando rclone...")
    urllib.request.urlretrieve(RCLONE_URL_WIN, "rclone.zip")

    with zipfile.ZipFile("rclone.zip", 'r') as zip_ref:
        zip_ref.extractall(".")

    for root, dirs, files in os.walk("."):
        if "rclone.exe" in files:
            os.rename(os.path.join(root, "rclone.exe"), "rclone.exe")

    print("rclone instalado")

def create_folders():
    os.makedirs("logs", exist_ok=True)

if __name__ == "__main__":
    install_python_deps()
    install_rclone()
    create_folders()
    print("Instalación completa")
