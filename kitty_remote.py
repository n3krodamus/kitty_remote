#!/usr/bin/env python3
"""kitty_remote - Send commands to kitty terminal via socket."""

import argparse
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

SOCKET = "unix:/tmp/my_kitty"
LOGS_DIR = Path(__file__).parent / "logs"


def setup_logging():
    """Create independent log file for this execution."""
    LOGS_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = LOGS_DIR / f"kitty_remote_{timestamp}.log"

    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__), log_file


def kitty_cmd(args, check=True):
    """Run kitty @ command."""
    cmd = ["kitty", "@", "--to", SOCKET] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    if check and result.returncode != 0:
        logger.error(f"kitty command failed: {' '.join(cmd)}")
        logger.error(f"stderr: {result.stderr.strip()}")
    return result


def start_kitty():
    """Launch kitty with socket."""
    cmd = ["nohup", "kitty", "--listen-on", SOCKET, ">/dev/null", "2>&1", "&"]
    subprocess.Popen(" ".join(cmd), shell=True)
    logger.info(f"Kitty started with socket {SOCKET}")


def send_text(text):
    """Send text to active kitty window."""
    kitty_cmd(["send-text", f"{text}\n"])


def run_command(cmd):
    """Execute command in kitty."""
    send_text(cmd)


def exec_file(filepath, host=None):
    """Execute commands from file with error checking. Optionally prefix with SSH to host."""
    path = Path(filepath)
    if not path.exists():
        logger.error(f"File not found: {filepath}")
        sys.exit(1)

    tmp_script = tempfile.NamedTemporaryFile(
        mode='w', suffix='.sh', prefix='kitty-cmds-', delete=False
    )
    result_file = f"{tmp_script.name}.result"

    with open(filepath, 'r') as f:
        lines = f.readlines()

    tmp_script.write("#!/bin/bash\nset -e\n")
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        tmp_script.write(f"{stripped}\n")
    tmp_script.close()

    os.chmod(tmp_script.name, 0o755)

    if host and host != "localhost":
        cmd = f"ssh {host} 'bash -s' < {tmp_script.name}; echo $? > {result_file}"
    else:
        cmd = f"bash {tmp_script.name}; echo $? > {result_file}"

    kitty_cmd(["send-text", f"{cmd}\n"])

    timeout = 300
    elapsed = 0
    while not os.path.exists(result_file) and elapsed < timeout:
        time.sleep(0.5)
        elapsed += 1

    if not os.path.exists(result_file):
        logger.error("Timeout: comandos no terminaron a tiempo")
        os.unlink(tmp_script.name)
        sys.exit(1)

    with open(result_file, 'r') as f:
        exit_code = int(f.read().strip())

    os.unlink(tmp_script.name)
    os.unlink(result_file)

    if exit_code != 0:
        logger.error(f"Error: comando falló (exit code: {exit_code})")
        sys.exit(exit_code)

    logger.info("Todos los comandos ejecutados correctamente")


def exec_hosts(hosts_file, tasks_file, connect_cmd="tt"):
    """Execute tasks for each host using configured connection command."""
    hosts_path = Path(hosts_file)
    if not hosts_path.exists():
        logger.error(f"Hosts file not found: {hosts_file}")
        sys.exit(1)

    with open(hosts_file, 'r') as f:
        hosts = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]

    if not hosts:
        logger.error("No hosts found in file")
        sys.exit(1)

    logger.info(f"Procesando {len(hosts)} host(s): {', '.join(hosts)}")
    logger.info(f"Comando de conexión: {connect_cmd}")

    failed_hosts = []
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    for host in hosts:
        logger.info(f"Conectando a host: {host}")
        kitty_cmd(["send-text", f"{connect_cmd} {host}\n"])
        time.sleep(3)

        logger.info(f"Ejecutando tareas en host: {host}")
        success = exec_file_tt(tasks_file, host)

        if not success:
            logger.error(f"Host {host} falló, agregado a lista de fallidos")
            failed_hosts.append(host)
            continue

        logger.info(f"Host {host} completado exitosamente")

    if failed_hosts:
        failed_file = LOGS_DIR / f"failed_hosts_{timestamp}.txt"
        with open(failed_file, 'w') as f:
            f.write("# Hosts que fallaron durante la ejecución\n")
            for h in failed_hosts:
                f.write(f"{h}\n")
        logger.info(f"Hosts fallidos guardados en: {failed_file}")
        logger.info(f"Hosts fallidos: {', '.join(failed_hosts)}")


def get_last_exit_code():
    """Get exit code from remote using a temp file."""
    result_file = "/tmp/kitty_exit_code"
    kitty_cmd(["send-text", f"echo $? > {result_file}\n"])
    time.sleep(0.5)
    kitty_cmd(["send-text", f"cat {result_file}\n"])
    time.sleep(0.5)
    return True


def exec_file_tt(filepath, expected_host):
    """Execute commands via tt-connected session. Stop on failure."""
    path = Path(filepath)
    if not path.exists():
        logger.error(f"File not found: {filepath}")
        sys.exit(1)

    with open(filepath, 'r') as f:
        commands = [line.strip() for line in f
                   if line.strip() and not line.strip().startswith('#')]

    if not commands:
        logger.error("No commands found in file")
        sys.exit(1)

    marker = "KITTY_EXIT_"
    for cmd in commands:
        logger.info(f"Ejecutando: {cmd}")
        kitty_cmd(["send-text", f"{cmd}\n"])
        time.sleep(2)

        kitty_cmd(["send-text", f"echo {marker}$?\n"])
        time.sleep(0.5)
        result = kitty_cmd(["get-text", "--self"], check=False)

        import re
        match = re.search(rf"{marker}(\d+)", result.stdout)
        if not match or match.group(1) != "0":
            exit_code = match.group(1) if match else "unknown"
            logger.error(f"Comando falló (exit code: {exit_code}): {cmd}")
            return False

        logger.info(f"Comando exitoso: {cmd}")

    return True


def launch_window(cmd):
    """Launch new kitty window."""
    kitty_cmd(["launch", "--type=window", cmd])


def new_tab(cmd):
    """Create new tab."""
    kitty_cmd(["launch", "--type=tab", cmd])


def list_windows():
    """List kitty windows."""
    result = kitty_cmd(["ls"], check=False)
    print(result.stdout)


def main():
    global logger
    logger, log_file = setup_logging()
    logger.info(f"Log file: {log_file}")

    parser = argparse.ArgumentParser(
        description="Send commands to kitty terminal via socket"
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    subparsers.add_parser("start", help="Launch kitty listening on socket")

    parser_send = subparsers.add_parser("send", help="Send text to active window")
    parser_send.add_argument("text", nargs="+", help="Text to send")

    parser_run = subparsers.add_parser("run", help="Execute command in kitty")
    parser_run.add_argument("cmd", nargs="+", help="Command to run")

    parser_exec = subparsers.add_parser("exec-file", help="Execute commands from file")
    parser_exec.add_argument("file", help="File with commands (one per line)")

    parser_hosts = subparsers.add_parser("exec-hosts", help="Execute tasks for each host in hosts file")
    parser_hosts.add_argument("hosts_file", nargs="?", default="conf/hosts.txt", help="Hosts file (default: conf/hosts.txt)")
    parser_hosts.add_argument("tasks_file", nargs="?", default="conf/tareas.txt", help="Tasks file (default: conf/tareas.txt)")
    parser_hosts.add_argument("--connect-cmd", default="tt", help="Connection command (default: tt). Use 'ssh' or 'telnet' as needed")

    parser_launch = subparsers.add_parser("launch", help="Launch new window")
    parser_launch.add_argument("cmd", nargs="+", help="Command to run")

    parser_tab = subparsers.add_parser("tab", help="Create new tab")
    parser_tab.add_argument("cmd", nargs="+", help="Command to run")

    subparsers.add_parser("focus-window", help="Focus kitty window")
    subparsers.add_parser("focus-tab", help="Focus kitty tab")
    subparsers.add_parser("ls", help="List kitty windows")

    parser_raw = subparsers.add_parser("@", help="Raw kitty @ command")
    parser_raw.add_argument("args", nargs=argparse.REMAINDER, help="kitty @ arguments")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    if args.command == "start":
        start_kitty()
    elif args.command == "send":
        send_text(" ".join(args.text))
    elif args.command == "run":
        run_command(" ".join(args.cmd))
    elif args.command == "exec-file":
        exec_file(args.file)
    elif args.command == "exec-hosts":
        exec_hosts(args.hosts_file, args.tasks_file, args.connect_cmd)
    elif args.command == "launch":
        launch_window(" ".join(args.cmd))
    elif args.command == "tab":
        new_tab(" ".join(args.cmd))
    elif args.command == "focus-window":
        kitty_cmd(["focus-window"])
    elif args.command == "focus-tab":
        kitty_cmd(["focus-tab"])
    elif args.command == "ls":
        list_windows()
    elif args.command == "@":
        kitty_cmd(args.args)

    logger.info("Command completed")


if __name__ == "__main__":
    main()
