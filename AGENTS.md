## Commands

```bash
# Use bash launcher (auto-activates venv)
./kitty_remote start                    # Launch kitty with socket
./kitty_remote run "ls -la"             # Execute command
./kitty_remote exec-file tareas.txt     # Run commands from file (stops on error)
./kitty_remote exec-hosts hosts.txt     # Run tasks for each host (default: hosts.txt)
./kitty_remote send "text"              # Send text to active window
./kitty_remote launch "bash"            # New window
./kitty_remote tab "htop"               # New tab
./kitty_remote ls                       # List windows
```

## Architecture

- **kitty_remote.py**: Main script, all logic in one file (~150 lines)
- **Socket**: `/tmp/my_kitty` (configured in `SOCKET` constant)
- **Logs**: `logs/kitty_remote_YYYYMMDD_HHMMSS.log` per execution
- **Virtual env**: `venv/` (standard library only, no pip installs needed)

## Key behaviors

- `exec-file` runs commands sequentially, stops immediately if any command fails (exit code ≠ 0)
- Commands from file skip empty lines and `#` comments
- `start` launches kitty detached via `nohup`, check socket exists with `ls -la /tmp/my_kitty`
- Logging goes to both console and `logs/` directory

## Socket not working?

Check if kitty is running: `lsof -U | grep my_kitty`
Recreate socket: `./kitty_remote.py start`
