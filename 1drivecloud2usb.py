import subprocess
import json
import time
import os
import shutil
from datetime import datetime
import win32api
import win32file
import sys

CONFIG_FILE = "config.json"
LOG_DIR = "logs"
LOCK_FILE = "backup.lock"

os.makedirs(LOG_DIR, exist_ok=True)


# =============================
# LOGGING
# =============================

def log(msg):
    line = f"{datetime.now()} - {msg}"
    print(line)
    with open(os.path.join(LOG_DIR, "backup.log"), "a", encoding="utf-8") as f:
        f.write(line + "\n")


# =============================
# PROTECCION DOBLE INSTANCIA
# =============================

def create_lock():
    if os.path.exists(LOCK_FILE):
        log("Otra instancia ya está ejecutándose. Abortando.")
        sys.exit(1)
    open(LOCK_FILE, "w").close()


def remove_lock():
    if os.path.exists(LOCK_FILE):
        os.remove(LOCK_FILE)


# =============================
# CONFIG
# =============================

def load_config():
    with open(CONFIG_FILE) as f:
        return json.load(f)


# =============================
# VALIDACIONES
# =============================

def check_rclone():
    if not os.path.exists("C:\\rclone\\rclone.exe"):
        log("ERROR: rclone no encontrado en C:\\rclone")
        sys.exit(1)


def get_drive_fs(drive):
    return win32api.GetVolumeInformation(drive)[4]


def check_ntfs(drive):
    fs = get_drive_fs(drive)
    if fs.upper() != "NTFS":
        log(f"ERROR: El disco está en {fs}. Debe ser NTFS.")
        return False
    return True


def check_free_space(path, min_gb=5):
    total, used, free = shutil.disk_usage(path)
    free_gb = free // (2**30)
    log(f"Espacio libre: {free_gb} GB")

    if free_gb < min_gb:
        log("ERROR: Espacio insuficiente.")
        return False
    return True


# =============================
# USB
# =============================

def find_usb_by_label(label):
    drives = win32api.GetLogicalDriveStrings().split('\000')[:-1]

    for drive in drives:
        try:
            volume_name = win32api.GetVolumeInformation(drive)[0]
            if volume_name.lower() == label.lower():
                return drive
        except:
            pass

    return None


# =============================
# MODO
# =============================

def get_rclone_mode():
    if datetime.today().weekday() == 6:
        return "sync"
    return "copy"


# =============================
# RCLONE
# =============================

def run_rclone(source, dest, cfg):

    mode = get_rclone_mode()
    log(f"Modo de ejecución: {mode.upper()}")

    cmd = [
        "C:\\rclone\\rclone.exe",
        mode,
        source,
        dest,

        "--fast-list",
        "--transfers", str(cfg["transfers"]),
        "--checkers", str(cfg["checkers"]),
        "--modify-window", "2s",
        "--size-only",
        "--no-update-modtime",
        "--no-traverse",

        "--exclude-from", "exclude.txt",

        "--retries", "10",
        "--low-level-retries", "10",
        "--timeout", "1h",

        "--log-level", "INFO",
        "--stats", "30s",
        "--stats-one-line",
        "--stats-one-line-date"
    ]

    if mode == "sync":
        cmd.append("--delete-after")

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    for line in process.stdout:
        print(line, end="")

        # Detecta errores críticos en vivo
        if "ERROR" in line.upper():
            log("Error detectado durante transferencia")

    process.wait()
    return process.returncode


# =============================
# MAIN
# =============================

def main():

    create_lock()
    check_rclone()

    cfg = load_config()

    try:
        while True:

            usb_path = find_usb_by_label(cfg["usb_label"])

            if not usb_path:
                log("USB no detectado, esperando...")
                time.sleep(cfg["check_interval"])
                continue

            log(f"USB detectado en {usb_path}")

            if not check_ntfs(usb_path):
                time.sleep(cfg["check_interval"])
                continue

            destination = os.path.join(usb_path, cfg["usb_folder"])
            os.makedirs(destination, exist_ok=True)

            if not check_free_space(destination, min_gb=5):
                time.sleep(cfg["check_interval"])
                continue

            code = run_rclone(cfg["remote"], destination, cfg)

            if code == 0:
                log("Backup completado correctamente")
            else:
                log("Backup terminó con errores")

            time.sleep(cfg["check_interval"])

    finally:
        remove_lock()


if __name__ == "__main__":
    main()
