import subprocess
import json
import time
import os
import sys
import threading
import queue
from datetime import datetime
import win32api

CONFIG_FILE = "config.json"
LOG_FILE = "logs/backup.log"

STATS_INTERVAL_SEC = 5
ZERO_SPEED_LIMIT = 4
INACTIVITY_LIMIT = 120


# =============================
# LOG
# =============================

def log(msg):
    os.makedirs("logs", exist_ok=True)
    line = f"{datetime.now()} - {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


# =============================
# CONFIG
# =============================

def load_config():
    with open(CONFIG_FILE) as f:
        return json.load(f)


# =============================
# USB DETECTION
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
# PROCESS START
# =============================

def start_process(cmd):

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True
    )

    q = queue.Queue()

    def reader():
        for line in iter(proc.stdout.readline, ''):
            q.put(line)
        proc.stdout.close()

    threading.Thread(target=reader, daemon=True).start()

    return proc, q


# =============================
# PARSER
# =============================

def has_activity(line):
    return (
        "Transferred:" in line or
        "ETA" in line or
        "Checks:" in line or
        "Copied" in line
    )


def zero_speed(line):
    return " 0 B/s" in line


# =============================
# RCLONE ENGINE V7 PRO
# =============================

def run_rclone(source, dest):

    log("ENTERPRISE V7 PRO iniciado")

    base_cmd = [
        "C:\\rclone\\rclone.exe",
        "copy",
        source,
        dest,

        "--drive-chunk-size", "160M",
        "--onedrive-chunk-size", "160M",

        "--no-traverse",
        "--size-only",
        "--ignore-existing",

        "--tpslimit", "2",
        "--tpslimit-burst", "2",

        "--retries", "10",
        "--low-level-retries", "10",

        "--stats", f"{STATS_INTERVAL_SEC}s",
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
        "--transfers", "6",
        "--checkers", "6",
        "--order-by", "size,ascending"
    ]

    p_large, q_large = start_process(large_cmd)
    log("Proceso GRANDES iniciado")

    time.sleep(2)

    p_small, q_small = start_process(small_cmd)
    log("Proceso PEQUEÑOS iniciado")

    last_activity = time.time()
    zero_counter = 0
    small_paused = False

    while True:

        if p_large.poll() is not None and p_small.poll() is not None:
            break

        for proc, q in [(p_large, q_large), (p_small, q_small)]:

            while not q.empty():
                line = q.get()
                print(line, end="")
                sys.stdout.flush()

                if has_activity(line):
                    last_activity = time.time()
                    zero_counter = 0
                elif zero_speed(line):
                    zero_counter += 1

        inactive = time.time() - last_activity

        # ===== ANTI THROTTLING =====
        if (
            zero_counter >= ZERO_SPEED_LIMIT and
            inactive > INACTIVITY_LIMIT and
            not small_paused
        ):
            if p_small.poll() is None:
                log("Throttling detectado → pausando PEQUEÑOS")
                p_small.terminate()
                small_paused = True

        if zero_counter == 0 and small_paused:
            log("Velocidad recuperada → reiniciando PEQUEÑOS")
            p_small, q_small = start_process(small_cmd)
            small_paused = False

        # ===== AUTO RECOVERY =====
        if p_large.poll() not in (None, 0):
            log("GRANDES murió → reiniciando")
            p_large, q_large = start_process(large_cmd)

        if p_small.poll() not in (None, 0):
            log("PEQUEÑOS murió → reiniciando")
            p_small, q_small = start_process(small_cmd)

        time.sleep(0.5)

    log("Copia finalizada correctamente")


# =============================
# MAIN LOOP
# =============================

def main():

    cfg = load_config()

    while True:

        usb = find_usb_by_label(cfg["usb_label"])

        if not usb:
            log("USB no detectado...")
            time.sleep(cfg["check_interval"])
            continue

        destination = os.path.join(usb, cfg["usb_folder"])
        os.makedirs(destination, exist_ok=True)

        log(f"USB detectado en {usb}")

        run_rclone(cfg["remote"], destination)

        log("Ciclo completado")
        time.sleep(cfg["check_interval"])


if __name__ == "__main__":
    main()
