# Análisis y Documentación: `1drivecloud2usb.py`

Este documento describe el funcionamiento, requisitos y uso del script `1drivecloud2usb.py`, diseñado para automatizar el respaldo de archivos desde la nube (OneDrive) hacia un dispositivo USB local.

## 1. Objetivo del Script

El objetivo principal es proporcionar un sistema de respaldo automático y resiliente que detecte la conexión de una unidad USB específica y sincronice archivos desde una cuenta de OneDrive utilizando `rclone`.

### Características Principales:
- **Detección Automática**: Monitorea continuamente el sistema en busca de un USB con una etiqueta de volumen específica.
- **Sincronización Inteligente**:
    - **Días de semana (Lunes a Sábado)**: Realiza una **copia incremental** (`copy`), agregando archivos nuevos o modificados sin borrar nada en el destino.
    - **Domingos**: Realiza una **sincronización completa** (`sync`), lo que significa que los archivos eliminados en la nube también se eliminarán en el USB para mantener una copia idéntica.
- **Optimización para FAT32**: Limita el tamaño máximo de archivo a 4GB para asegurar compatibilidad con sistemas de archivos antiguos.
- **Resiliencia**: Configurado con múltiples reintentos y tiempos de espera extendidos para manejar conexiones de red inestables.

## 2. Requerimientos y Dependencias

### Requerimientos del Sistema
- **Sistema Operativo**: Windows (debido al uso de `win32api` para detección de discos).
- **Herramienta Externa**: `rclone.exe` instalado en `C:\rclone\rclone.exe`.

### Dependencias de Python
El script requiere las siguientes librerías que pueden instalarse mediante `pip`:
- `pywin32` (proporciona el módulo `win32api`)
- `psutil` (utilizado en scripts de soporte)
- `tqdm` (utilizado en scripts de soporte)

> [!NOTE]
> El archivo `install.py` incluido en la carpeta automatiza la descarga de `rclone` y la instalación de las librerías de Python.

## 3. Configuración (`config.json`)

El archivo `config.json` define el comportamiento del script:
- `remote`: El nombre del remoto configurado en rclone seguido del directorio (ej: `onedrive:/Documentos`).
- `usb_label`: La etiqueta de volumen del USB (ej: `ESD-USB`).
- `usb_folder`: La carpeta dentro del USB donde se guardará el respaldo.
- `check_interval`: Tiempo en segundos entre cada revisión de presencia del USB.
- `transfers` / `checkers`: Configuración de rendimiento para la velocidad de copia.

## 4. Uso del Script

1. **Configuración Inicial**: Asegúrese de tener configurado un remoto en rclone llamado `onedrive` (o el nombre que defina en `config.json`).
2. **Instalación**: Ejecute `python install.py` para preparar el entorno.
3. **Ejecución**: Ejecute el script principal:
   ```bash
   python 1drivecloud2usb.py
   ```
4. **Funcionamiento**: El script entrará en un ciclo infinito. Cuando detecte el USB configurado, iniciará la copia. Al terminar, esperará el intervalo definido para la siguiente revisión.

## 5. Exclusiones (`exclude.txt`)

El script omite automáticamente ciertas carpetas para ahorrar espacio y tiempo, tales como:
- `AppData/**`
- `Microsoft Edge Collections/**`
- `Archivos de chat de Microsoft Copilot/**`

---
*Documentación generada para ABC Geomática Agrícola SRL.*
