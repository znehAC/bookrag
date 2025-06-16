import sys
import time
import uuid
from itertools import zip_longest
from typing import List, Tuple

import requests
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

API_URL = "http://localhost:8000/chat/completion"
console = Console()
chat_id = uuid.uuid4().hex[:8]
history: List[Tuple[str, str]] = []


def grouper(seq, n):
    it = iter(seq)
    return zip_longest(*[it] * n)


def create_chat_table(hist=None) -> Table:
    data = hist or history
    table = Table.grid(expand=True)
    table.add_column(justify="left")
    table.add_column(justify="right")
    for u, b in grouper(data, 2):
        if u:
            table.add_row("", f"{u[1].strip()} <- USUÁRIO")
        if b:
            table.add_row(f"IA -> {b[1].strip()}", "")
    return table


def stream_reply(prompt: str):
    with requests.post(
        API_URL,
        json={"chat_id": chat_id, "prompt": prompt},
        stream=True,
        timeout=None,
    ) as resp:
        resp.raise_for_status()
        for chunk in resp.iter_content(decode_unicode=True):
            if chunk:
                yield chunk


def display_chat():
    console.clear()
    table = create_chat_table()
    console.print(Panel(table, title=f"chat {chat_id}", padding=(1, 2)))


def main():
    try:
        display_chat()

        while True:
            try:
                prompt = console.input("[bold cyan]you▸ [/]").strip()
            except (KeyboardInterrupt, EOFError):
                break

            if not prompt:
                continue

            history.append(("user", prompt))
            display_chat()

            answer = ""
            last_update = time.time()
            update_interval = 0.1

            for tok in stream_reply(prompt):
                answer += tok
                current_time = time.time()

                if current_time - last_update > update_interval:
                    console.clear()
                    temp_table = create_chat_table(history + [("bot", answer)])
                    console.print(
                        Panel(temp_table, title=f"chat {chat_id}", padding=(1, 2))
                    )
                    last_update = current_time

            history.append(("bot", answer))
            display_chat()
    finally:
        pass


if __name__ == "__main__":
    main()
