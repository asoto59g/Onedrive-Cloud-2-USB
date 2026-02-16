import subprocess
import json
import time
import os
from datetime import datetime
import win32api

CONFIG_FILE = "config.json"
LOG_FILE = "logs/backup.log"


def log(msg):
    os.makedirs("logs", exist_ok=True)
    line = f"{datetime.now()} - {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_config():
    with open(CONFIG_FILE) as f:
        return json.load(f)


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


def get_rclone_mode():
    # Domingo = limpieza completa
    if datetime.today().weekday() == 6:
        return "sync"
    return "copy"


def run_rclone(source, dest, cfg):

    mode = get_rclone_mode()

    log(f"Modo de ejecución: {mode.upper()}")

    cmd = [
        "C:\\rclone\\rclone.exe",
        mode,
        source,
        dest,

        # FAT32 protección
        "--max-size", "4G",

        # Rendimiento incremental
        "--fast-list",
        "--transfers", str(cfg["transfers"]),
        "--checkers", str(cfg["checkers"]),
        "--drive-chunk-size", "64M",
        "--tpslimit", "8",
        "--modify-window", "2s",
        "--size-only",
        "--no-update-modtime",
        "--no-traverse",

        # Seguridad borrados solo en sync
        "--delete-after" if mode == "sync" else "",

        # Exclusiones
        "--exclude-from", "exclude.txt",

        # Resiliencia
        "--retries", "10",
        "--low-level-retries", "10",
        "--timeout", "1h",
        "--contimeout", "60s",

        # Logs y progreso
        "--log-file", LOG_FILE,
        "--log-level", "INFO",
        "--stats", "60s",
        "--stats-one-line",
        "--stats-one-line-date"
    ]

    # eliminar elementos vacíos
    cmd = [c for c in cmd if c != ""]

    log(f"Iniciando sincronización hacia {dest}")

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    for line in process.stdout:
        print(line, end="")

    process.wait()
    return process.returncode


def main():
    cfg = load_config()

    while True:
        usb_path = find_usb_by_label(cfg["usb_label"])

        if not usb_path:
            log("USB no detectado, esperando...")
            time.sleep(cfg["check_interval"])
            continue

        destination = os.path.join(
            usb_path,
            cfg["usb_folder"]
        )

        os.makedirs(destination, exist_ok=True)

        log(f"USB detectado en {usb_path}")

        code = run_rclone(cfg["remote"], destination, cfg)

        if code == 0:
            log("Proceso finalizado correctamente")
        else:
            log("Error detectado, reintentando")

        time.sleep(cfg["check_interval"])


if __name__ == "__main__":
    main()
