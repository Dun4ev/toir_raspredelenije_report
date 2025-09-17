"""
Настольный интерфейс на Tkinter: запуск распределения и просмотр журналов.
"""
from __future__ import annotations

import importlib
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Iterable

from toir_manager.core.logging_models import TransferLogEntry
from toir_manager.services.log_reader import list_runs, summarize_entries
from toir_manager.services.log_writer import iter_run_logs

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

pipeline = importlib.import_module("toir_raspredelenije")
DEFAULT_INBOX = pipeline.INBOX_DIR
DESTINATIONS = {
    "INBOX": DEFAULT_INBOX,
    "NOTES": pipeline.NOTES_DIR,
    "TRA_GST": pipeline.TRA_GST_DIR,
    "TRA_SUB_APP": pipeline.TRA_SUB_APP_DIR,
    "DEST_ROOT": pipeline.DEST_ROOT_DIR,
}
PIPELINE_SCRIPT = REPO_ROOT / "toir_raspredelenije.py"


def _format_row(entry: TransferLogEntry) -> tuple[str, str, str, str, str, str]:
    """Подготовить строку для таблицы."""

    target = str(entry.target_path) if entry.target_path else "-"
    return (
        entry.timestamp.strftime("%H:%M:%S"),
        entry.action.value,
        entry.status.value,
        str(entry.source_path),
        target,
        entry.message or "",
    )


def _load_entries(base_dir: Path, run_id: str) -> list[TransferLogEntry]:
    """Загрузить записи одного запуска и отсортировать по времени."""

    entries = list(iter_run_logs(run_id, base_dir=base_dir))
    entries.sort(key=lambda item: item.timestamp)
    return entries


def _update_summary(summary_var: tk.StringVar, entries: Iterable[TransferLogEntry]) -> None:
    """Обновить текст сводки."""

    summary = summarize_entries(entries)
    summary_var.set(
        "Всего: {total} | Успехов: {success} | Ошибок: {errors}".format(**summary)
    )


def _open_path(path: Path) -> None:
    """Открыть папку или файл в системном проводнике."""

    target_path = path if path.exists() else path.parent
    if not target_path.exists():
        messagebox.showerror("Ошибка", f"Путь не найден: {path}")
        return

    try:
        if sys.platform.startswith("win"):
            os.startfile(target_path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.run(["open", str(target_path)], check=False)
        else:
            subprocess.run(["xdg-open", str(target_path)], check=False)
    except OSError as exc:  # pragma: no cover
        messagebox.showerror("Ошибка", f"Не удалось открыть {target_path}: {exc}")


def launch(base_dir: Path | None = None) -> None:
    """Запустить главный цикл Tkinter UI."""

    if os.environ.get("APP_HEADLESS") == "1":
        raise RuntimeError("UI запрещён в режиме APP_HEADLESS=1")

    root_dir = (base_dir or Path("logs") / "dispatch").resolve()
    result_queue: queue.Queue[tuple[int, str, str]] = queue.Queue()

    root = tk.Tk()
    is_running = tk.BooleanVar(value=False, master=root)
    root.title("ТОиР: распределение и журналы")
    root.geometry("1200x700")

    notebook = ttk.Notebook(root)
    notebook.pack(fill=tk.BOTH, expand=True)

    # --- Вкладка "Распределение" ---
    control_tab = ttk.Frame(notebook, padding=10)
    notebook.add(control_tab, text="Распределение")

    ttk.Label(control_tab, text="Каталог входных данных").grid(row=0, column=0, sticky=tk.W)
    inbox_var = tk.StringVar(value=str(DEFAULT_INBOX))
    inbox_entry = ttk.Entry(control_tab, textvariable=inbox_var, width=80)
    inbox_entry.grid(row=1, column=0, sticky=tk.W)

    def choose_inbox() -> None:
        selected = filedialog.askdirectory(initialdir=inbox_var.get() or str(DEFAULT_INBOX))
        if selected:
            inbox_var.set(selected)

    ttk.Button(control_tab, text="Выбрать...", command=choose_inbox).grid(row=1, column=1, padx=(8, 0))

    ttk.Label(control_tab, text="Назначения").grid(row=2, column=0, sticky=tk.W, pady=(10, 2))

    dest_frame = ttk.Frame(control_tab)
    dest_frame.grid(row=3, column=0, columnspan=2, sticky=tk.W)
    for idx, (label, path) in enumerate(DESTINATIONS.items()):
        row = ttk.Frame(dest_frame)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text=f"{label}: {path}").pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(row, text="Открыть", command=lambda p=path: _open_path(p)).pack(side=tk.RIGHT, padx=(4, 0))

    status_var = tk.StringVar(value="Готово")
    ttk.Label(control_tab, textvariable=status_var).grid(row=4, column=0, sticky=tk.W, pady=(10, 0))

    log_frame = ttk.Frame(control_tab)
    log_frame.grid(row=5, column=0, columnspan=2, sticky=tk.NSEW, pady=(8, 0))
    control_tab.rowconfigure(5, weight=1)
    control_tab.columnconfigure(0, weight=1)

    log_text = tk.Text(log_frame, wrap=tk.WORD, height=18)
    log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    log_scroll = ttk.Scrollbar(log_frame, orient="vertical", command=log_text.yview)
    log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    log_text.configure(yscrollcommand=log_scroll.set)

    def append_log(message: str) -> None:
        log_text.insert(tk.END, message)
        log_text.see(tk.END)

    def clear_log() -> None:
        log_text.delete("1.0", tk.END)

    button_frame = ttk.Frame(control_tab)
    button_frame.grid(row=6, column=0, columnspan=2, sticky=tk.E, pady=(8, 0))

    def distribution_worker(selected_dir: Path) -> None:
        env = os.environ.copy()
        env.setdefault("PYTHONIOENCODING", "utf-8")
        if selected_dir:
            env["TOIR_INBOX_DIR"] = str(selected_dir)
        cmd = [sys.executable, str(PIPELINE_SCRIPT)]
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            env=env,
        )
        result_queue.put((process.returncode, process.stdout, process.stderr))

    def handle_queue() -> None:
        if result_queue.empty():
            root.after(200, handle_queue)
            return
        returncode, stdout, stderr = result_queue.get()
        append_log(stdout or "")
        if stderr:
            append_log("\n[stderr]\n" + stderr)
        if returncode == 0:
            status_var.set("Готово")
            messagebox.showinfo("Распределение", "Обработка завершена успешно.")
            refresh_runs()
        else:
            status_var.set("Завершено с ошибками")
            messagebox.showerror("Распределение", f"Скрипт завершился с кодом {returncode}.")
        run_button.config(state=tk.NORMAL)
        cancel_button.config(state=tk.DISABLED)
        is_running.set(False)
        root.after(200, handle_queue)

    def start_distribution() -> None:
        if is_running.get():
            return
        selected_dir = Path(inbox_var.get()).expanduser()
        if not selected_dir.exists():
            messagebox.showerror("Ошибка", f"Каталог не найден: {selected_dir}")
            return
        clear_log()
        status_var.set("Выполняется...")
        append_log(f"Запуск распределения для {selected_dir}\n\n")
        run_button.config(state=tk.DISABLED)
        cancel_button.config(state=tk.DISABLED)
        is_running.set(True)
        thread = threading.Thread(target=distribution_worker, args=(selected_dir,), daemon=True)
        thread.start()

    def cancel_distribution() -> None:
        messagebox.showinfo("Отмена", "Остановка выполняется по завершении текущего запуска.")

    run_button = ttk.Button(button_frame, text="Распределить", command=start_distribution)
    run_button.pack(side=tk.RIGHT, padx=(4, 0))

    cancel_button = ttk.Button(button_frame, text="Отмена", command=cancel_distribution, state=tk.DISABLED)
    cancel_button.pack(side=tk.RIGHT, padx=(4, 0))

    ttk.Button(button_frame, text="Очистить лог", command=clear_log).pack(side=tk.RIGHT, padx=(4, 0))

    # --- Вкладка "Журналы" ---
    logs_tab = ttk.Frame(notebook, padding=10)
    notebook.add(logs_tab, text="Журналы")

    list_frame = ttk.Frame(logs_tab)
    list_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))

    ttk.Label(list_frame, text="Запуски").pack(anchor=tk.W)
    run_listbox = tk.Listbox(list_frame, height=15, exportselection=False)
    run_listbox.pack(fill=tk.BOTH, expand=True)

    refresh_button = ttk.Button(list_frame, text="Обновить")
    refresh_button.pack(fill=tk.X, pady=(8, 0))

    summary_var = tk.StringVar(value="Журналы не найдены")
    ttk.Label(list_frame, textvariable=summary_var).pack(anchor=tk.W, pady=(8, 0))

    tree_frame = ttk.Frame(logs_tab)
    tree_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

    columns = ("time", "action", "status", "source", "target", "message")
    tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse")
    tree.pack(fill=tk.BOTH, expand=True)

    headings = {
        "time": "Время",
        "action": "Действие",
        "status": "Статус",
        "source": "Источник",
        "target": "Назначение",
        "message": "Комментарий",
    }
    widths = {
        "time": 80,
        "action": 160,
        "status": 90,
        "source": 320,
        "target": 320,
        "message": 240,
    }

    for col in columns:
        tree.heading(col, text=headings[col])
        tree.column(col, width=widths[col], anchor=tk.W)

    tree_scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
    tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    tree.configure(yscrollcommand=tree_scroll.set)

    current_entries: list[TransferLogEntry] = []

    def load_entries(run_id: str) -> None:
        nonlocal current_entries
        current_entries = _load_entries(root_dir, run_id)
        tree.delete(*tree.get_children())
        for idx, entry in enumerate(current_entries):
            tree.insert("", tk.END, iid=str(idx), values=_format_row(entry))
        _update_summary(summary_var, current_entries)

    def on_run_select(_event: tk.Event) -> None:
        selection = run_listbox.curselection()
        if selection:
            run_id = run_listbox.get(selection[0])
            load_entries(run_id)

    def refresh_runs() -> None:
        runs = list_runs(base_dir=root_dir)
        run_ids = [run.run_id for run in runs]
        run_listbox.delete(0, tk.END)
        for run_id in run_ids:
            run_listbox.insert(tk.END, run_id)
        if run_ids:
            run_listbox.selection_set(0)
            load_entries(run_ids[0])
        else:
            tree.delete(*tree.get_children())
            summary_var.set("Журналы не найдены")

    refresh_button.config(command=refresh_runs)
    run_listbox.bind("<<ListboxSelect>>", on_run_select)

    refresh_runs()
    root.after(200, handle_queue)

    try:
        root.mainloop()
    finally:
        try:
            root.destroy()
        except tk.TclError:
            pass


if __name__ == "__main__":
    launch()
