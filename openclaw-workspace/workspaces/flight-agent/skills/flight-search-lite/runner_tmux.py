#!/usr/bin/env python3
import argparse
import subprocess
import shlex
import sys


def build_cmd(args: argparse.Namespace) -> str:
    origin = args.origin
    dest = args.destination
    depart = args.departure
    ret = args.return
    nonstop = True if args.nonstop else False
    cmd = [
        "python3",
        "flight_search.py",
        "--origin", origin,
        "--destination", dest,
        "--departure", depart
    ]
    if ret:
        cmd += ["--return", ret]
    if nonstop:
        cmd += ["--nonstop"]
    return " ".join(shlex.quote(p) for p in cmd)


def run_in_tmux(cmd: str, session_name: str = "flight-search-lite") -> str:
    # Create a detached tmux session that runs the command
    spawn = ["tmux", "new-session", "-d", "-s", session_name, "bash", "-lc", cmd]
    subprocess.run(spawn, check=True)
    # Capture stdout from the session
    capture = ["tmux", "capture-pane", "-pt", session_name]
    subprocess.run(capture, check=True)
    show = ["tmux", "display-message", "-p", "#S - #I:#P#F - #{pane_title} : {pane_index}"]
    # Fallback: print entire pane contents
    raw = subprocess.check_output(["tmux", "through", "-p", session_name]).decode()
    # Clean up: kill the session
    subprocess.run(["tmux", "kill-session", "-t", session_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return raw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--origin", required=True)
    ap.add_argument("--destination", required=True)
    ap.add_argument("--departure", required=True)
    ap.add_argument("--return", required=False)
    ap.add_argument("--nonstop", action="store_true", help="force nonstop only (default true as per spec)")
    args = ap.parse_args()

    # Build and run the underlying flight_search.py via tmux
    cmd = build_cmd(args)
    try:
        output = run_in_tmux(cmd)
        print(output)
    except Exception as e:
        print(str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()

