import subprocess
import json
import time
import os
import re
import sys
from datetime import datetime
import win32api

CONFIG_FILE = "config.json"
LOG_FILE = "logs/backup.log"
LOCK_FILE = "backup.lock"

STATS_INTERVAL = 60
ZERO_SPEED_LIMIT = 4
STALL_TIMEOUT = 300   # segundos sin actividad real


# ==========================================================
# LOG
# ==========================================================

def log(msg):
    os.makedirs("logs", exist_ok=True)
    line = f"{datetime.now()} - {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


# ==========================================================
# SINGLE INSTANCE LOCK
# ==========================================================

def create_lock():
    if os.path.exists(LOCK_FILE):
        log("Otra instancia ya está ejecutándose.")
        sys.exit(1)

    with open(LOCK_FILE, "w") as f:
        f.write(str(os.getpid()))


def remove_lock():
    if os.path.exists(LOCK_FILE):
        os.remove(LOCK_FILE)


# ==========================================================
# CONFIG
# ==========================================================

def load_config():
    with open(CONFIG_FILE) as f:
        return json.load(f)


# ==========================================================
# USB DETECTION
# ==========================================================

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


# ==========================================================
# RCLONE PROCESS
# ==========================================================

def start_rclone(cmd):

    return subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True
    )


def is_zero_speed(line):
    return "0 B/s" in line


def has_activity(line):
    return (
        "Transferred:" in line or
        "Checks:" in line or
        "Copied" in line or
        "Transferred" in line
    )


# ==========================================================
# ENTERPRISE V8 CORE
# ==========================================================

def run_rclone(source, dest):

    log("=== ENTERPRISE V8 DATACENTER INICIADO ===")

    base_cmd = [
        "C:\\rclone\\rclone.exe",
        "copy",
        source,
        dest,

        "--tpslimit", "2",
        "--tpslimit-burst", "2",

        "--onedrive-chunk-size", "160M",

        "--size-only",
        "--modify-window", "2s",
        "--no-update-modtime",
        "--no-traverse",

        "--exclude-from", "exclude.txt",

        "--retries", "10",
        "--low-level-retries", "10",

        "--stats", str(STATS_INTERVAL),
        "--stats-one-line",
        "--stats-one-line-date",
        "--progress",
        "-v"
    ]

    large_cmd = base_cmd + [
        "--min-size", "200M",
        "--transfers", "1",
        "--checkers", "1",
        "--order-by", "size,descending"
    ]

    small_cmd = base_cmd + [
        "--max-size", "200M",
        "--transfers", "4",
        "--checkers", "4",
        "--order-by", "size,ascending"
    ]

    p_large = start_rclone(large_cmd)
    log("Proceso GRANDES iniciado")

    p_small = start_rclone(small_cmd)
    log("Proceso PEQUEÑOS iniciado")

    zero_speed_counter = 0
    last_activity = time.time()
    small_paused = False

    while True:

        finished_large = p_large.poll() is not None
        finished_small = p_small.poll() is not None

        if finished_large and finished_small:
            break

        for proc in (p_large, p_small):

            if proc.stdout is None:
                continue

            line = proc.stdout.readline()

            if not line:
                continue

            print(line, end="")

            if has_activity(line):
                last_activity = time.time()
                zero_speed_counter = 0

            elif is_zero_speed(line):
                zero_speed_counter += 1

        # ===== WATCHDOG =====
        inactive_time = time.time() - last_activity

        if (
            zero_speed_counter >= ZERO_SPEED_LIMIT and
            inactive_time > STALL_TIMEOUT and
            not small_paused
        ):
            if p_small.poll() is None:
                log("Throttling detectado → pausando PEQUEÑOS")
                p_small.terminate()
                small_paused = True

        if zero_speed_counter == 0 and small_paused:
            log("Velocidad recuperada → reanudando PEQUEÑOS")
            p_small = start_rclone(small_cmd)
            small_paused = False

        time.sleep(0.2)

    log("=== BACKUP FINALIZADO ===")
    return 0


# ==========================================================
# MAIN LOOP
# ==========================================================

def main():

    create_lock()

    try:

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

            run_rclone(cfg["remote"], destination)

            log("Ciclo completado")
            time.sleep(cfg["check_interval"])

    finally:
        remove_lock()


if __name__ == "__main__":
    main()
