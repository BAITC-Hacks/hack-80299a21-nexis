"""Start the local API and Vite together; optional first-run dependency install."""
import argparse
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[2]
PYTHON = ROOT / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0


def run(command, directory=ROOT):
    subprocess.run(command, cwd=directory, check=True, creationflags=NO_WINDOW)


def available_port(port):
    with socket.socket() as listener:
        try:
            listener.bind(('127.0.0.1', port))
        except OSError:
            raise SystemExit(f'Port {port} is already in use. Stop the previous server or select different --api-port/--ui-port.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--install', action='store_true', help='Create .venv and install Python/npm dependencies first')
    parser.add_argument('--api-port', type=int, default=8000)
    parser.add_argument('--ui-port', type=int, default=5173)
    args = parser.parse_args()
    if not all(1 <= port <= 65535 for port in (args.api_port, args.ui_port)) or args.api_port == args.ui_port:
        parser.error('Use two different ports between 1 and 65535.')
    npm = shutil.which('npm.cmd' if os.name == 'nt' else 'npm')
    if not npm:
        raise SystemExit('Node.js/npm are required. Alternatively run docker compose up --build.')
    if args.install:
        if not PYTHON.exists():
            run([sys.executable, '-m', 'venv', str(ROOT / '.venv')])
        run([str(PYTHON), '-m', 'ensurepip', '--upgrade'])
        run([str(PYTHON), '-m', 'pip', 'install', '-r', 'backend/requirements-lock.txt'])
        run([npm, 'ci', '--no-audit', '--no-fund'], ROOT / 'frontend')
    if not PYTHON.exists() or not (ROOT / 'frontend/node_modules').is_dir():
        raise SystemExit('Dependencies missing. Run: python backend/scripts/dev.py --install')
    if not (ROOT / '.env').exists():
        shutil.copyfile(ROOT / '.env.example', ROOT / '.env')
        print('Created .env. Set EKT_API_USER/EKT_API_PASS there for catalog access; OPENAI_API_KEY is optional.', flush=True)
    available_port(args.api_port)
    available_port(args.ui_port)
    env = dict(os.environ, HOST='127.0.0.1', PORT=str(args.api_port), PYTHONUNBUFFERED='1',
               BACKEND_PUBLIC_URL=f'http://localhost:{args.api_port}',
               VITE_API_BASE_URL=f'http://localhost:{args.api_port}/api')
    env['CORS_ORIGINS'] = ','.join(filter(None, [os.getenv('CORS_ORIGINS', ''),
                                               f'http://localhost:{args.ui_port}', f'http://127.0.0.1:{args.ui_port}']))
    commands = [('backend', [str(PYTHON), 'backend/main.py'], ROOT),
                ('frontend', [npm, 'run', 'dev', '--', '--host', '127.0.0.1', '--port', str(args.ui_port), '--strictPort'], ROOT / 'frontend')]
    children = []
    def output(prefix, stream):
        for line in stream:
            print(f'[{prefix}] {line.rstrip()}', flush=True)
    try:
        for name, command, directory in commands:
            process = subprocess.Popen(command, cwd=directory, env=env, stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace',
                                       creationflags=NO_WINDOW, start_new_session=os.name != 'nt')
            children.append(process)
            threading.Thread(target=output, args=(name, process.stdout), daemon=True).start()
        print(f'UI: http://localhost:{args.ui_port} | API: http://localhost:{args.api_port}/docs | Ctrl+C stops both.', flush=True)
        while all(process.poll() is None for process in children):
            time.sleep(.25)
        raise SystemExit('A development server exited; see its output above.')
    except KeyboardInterrupt:
        pass
    finally:
        for process in children:
            if process.poll() is None:
                if os.name == 'nt':
                    subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=NO_WINDOW)
                else:
                    os.killpg(process.pid, signal.SIGTERM)
        for process in children:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()


if __name__ == '__main__':
    main()
