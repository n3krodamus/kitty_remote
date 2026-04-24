# kitty_remote

Herramienta para enviar comandos al terminal [kitty](https://sw.kovidgoyal.net/kitty/) vía socket local en Linux.

## Lenguajes utilizados

- **Python 3** (lógica principal) - `kitty_remote.py`
- **Bash** (launcher) - `kitty_remote`

## Librerías requeridas

Ninguna. El proyecto usa solo la biblioteca estándar de Python:
- `argparse`, `os`, `subprocess`, `sys`, `tempfile`, `time`, `datetime`, `pathlib`, `logging`

## Instalación

```bash
cd /home/n3krodamus/work/opencode/kitty_remote
python3 -m venv venv
```

## Uso

```bash
# Usar el launcher (activa venv automáticamente)
./kitty_remote [comando] [parámetros]

# Comandos disponibles:
./kitty_remote start                    # Inicia kitty con socket en /tmp/my_kitty
./kitty_remote run "ls -la"             # Ejecuta comando en kitty
./kitty_remote exec-file conf/tareas.txt     # Ejecuta comandos desde archivo (corta si falla)
./kitty_remote exec-hosts conf/hosts.txt     # Ejecuta tareas para cada host (default: tt)
./kitty_remote exec-hosts --connect-cmd ssh conf/hosts.txt    # Usa ssh para conectar
./kitty_remote exec-hosts --connect-cmd telnet conf/hosts.txt  # Usa telnet para conectar
./kitty_remote send "texto"             # Envía texto a ventana activa
./kitty_remote launch "bash"            # Nueva ventana
./kitty_remote tab "htop"               # Nueva pestaña
./kitty_remote ls                       # Lista ventanas
./kitty_remote focus-window              # Enfoca ventana
./kitty_remote focus-tab                # Enfoca pestaña
./kitty_remote @ [subcomando]           # Comando raw de kitty @
```

## Comportamiento ante fallos en exec-hosts

Cuando se usa `exec-hosts`:
- Si un comando falla en un host, se detiene la ejecución para **ese host**
- El host fallido se guarda en `logs/failed_hosts_YYYYMMDD_HHMMSS.txt`
- La ejecución continúa con el siguiente host automáticamente

## Configuración

- `conf/hosts.txt` - Lista de hosts (uno por línea, `#` para comentarios)
- `conf/tareas.txt` - Comandos a ejecutar (uno por línea, `#` para comentarios)

## Logs

Cada ejecución genera un log independiente en `logs/kitty_remote_YYYYMMDD_HHMMSS.log`

## Estructura

```
kitty_remote/
├── conf/           # Archivos de configuración
├── logs/           # Logs por ejecución
├── venv/           # Entorno virtual Python
├── kitty_remote    # Launcher Bash
├── kitty_remote.py # Script principal Python
├── AGENTS.md       # Instrucciones para agentes
└── README.md       # Este archivo
```
