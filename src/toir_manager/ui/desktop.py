"""
Настольный интерфейс на Tkinter: запуск распределения и просмотр журналов.
"""

from __future__ import annotations

import importlib
import shutil
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable, Iterable

from toir_manager.core.logging_models import TransferLogEntry, TransferStatus
from toir_manager.services.log_reader import list_runs, summarize_entries
from toir_manager.services.log_writer import iter_run_logs

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

pipeline = importlib.import_module("toir_raspredelenije")
DEFAULT_INBOX = pipeline.INBOX_DIR
DESTINATION_CONFIG = (
    ("INBOX", "TOIR_INBOX_DIR", DEFAULT_INBOX),
    ("NOTES", "TOIR_NOTES_DIR", pipeline.NOTES_DIR),
    ("TRA_GST", "TOIR_TRA_GST_DIR", pipeline.TRA_GST_DIR),
    ("TRA_SUB_APP", "TOIR_TRA_SUB_APP_DIR", pipeline.TRA_SUB_APP_DIR),
    ("DEST_ROOT", "TOIR_DEST_ROOT_DIR", pipeline.DEST_ROOT_DIR),
)
DESTINATION_LABELS = {env: name for name, env, _ in DESTINATION_CONFIG}
PIPELINE_SCRIPT = REPO_ROOT / "toir_raspredelenije.py"

BG_COLOR = "#F4F6F5"
FRAME_COLOR = "#FFFFFF"
BUTTON_COLOR = "#4CAF50"
BUTTON_ACTIVE_COLOR = "#45A049"
TEXT_COLOR = "#333333"
DISABLED_TEXT_COLOR = "#AAAAAA"
STATUS_BAR_COLOR = "#E0E0E0"
HEADING_BG_COLOR = "#3F8E47"
SELECTION_COLOR = "#DDEBDD"

FONT_BASE = ("Segoe UI", 9)
FONT_BOLD = ("Segoe UI", 10, "bold")
FONT_LABEL = ("Segoe UI", 8)


def _configure_theme(root: tk.Tk) -> ttk.Style:
    """Настроить единый стиль интерфейса в духе toir_tra_report."""

    root.configure(bg=BG_COLOR)
    root.option_add("*Font", "{Segoe UI} 9")
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    style.configure("TFrame", background=BG_COLOR)
    style.configure("Card.TFrame", background=FRAME_COLOR, relief=tk.FLAT)
    style.configure("TNotebook", background=BG_COLOR, borderwidth=0)
    style.configure(
        "TNotebook.Tab",
        background=FRAME_COLOR,
        foreground=TEXT_COLOR,
        padding=(10, 4),
        font=FONT_LABEL,
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", FRAME_COLOR), ("active", FRAME_COLOR)],
        foreground=[("selected", TEXT_COLOR)],
    )
    style.configure(
        "TButton",
        background=BUTTON_COLOR,
        foreground="white",
        font=FONT_BOLD,
        padding=(8, 6),
        bordercolor=BUTTON_COLOR,
        relief=tk.FLAT,
    )
    style.map(
        "TButton",
        background=[("active", BUTTON_ACTIVE_COLOR), ("pressed", BUTTON_ACTIVE_COLOR)],
        foreground=[("active", "white"), ("pressed", "white")],
    )
    style.configure(
        "Status.TLabel",
        background=STATUS_BAR_COLOR,
        foreground=TEXT_COLOR,
        font=FONT_LABEL,
        padding=(8, 4),
    )
    style.configure(
        "TLabel", background=BG_COLOR, foreground=TEXT_COLOR, font=FONT_BASE
    )
    style.configure(
        "Card.TLabel", background=FRAME_COLOR, foreground=TEXT_COLOR, font=FONT_BASE
    )
    style.configure(
        "Secondary.TLabel",
        background=BG_COLOR,
        foreground="#555555",
        font=FONT_LABEL,
    )
    style.configure(
        "TEntry",
        fieldbackground=FRAME_COLOR,
        background=FRAME_COLOR,
        foreground=TEXT_COLOR,
        insertcolor=TEXT_COLOR,
    )
    style.configure(
        "Treeview",
        background=FRAME_COLOR,
        foreground=TEXT_COLOR,
        fieldbackground=FRAME_COLOR,
        rowheight=22,
        font=FONT_LABEL,
    )
    style.map(
        "Treeview",
        background=[("selected", SELECTION_COLOR)],
        foreground=[("selected", TEXT_COLOR)],
    )
    style.configure(
        "Treeview.Heading",
        background=HEADING_BG_COLOR,
        foreground="white",
        font=FONT_BOLD,
        bordercolor=HEADING_BG_COLOR,
    )
    style.map("Treeview.Heading", background=[("active", BUTTON_COLOR)])
    style.configure(
        "Vertical.TScrollbar",
        background=STATUS_BAR_COLOR,
        troughcolor=FRAME_COLOR,
        arrowsize=12,
    )

    return style


def _collect_processed_projects(
    entries: Iterable[TransferLogEntry], inbox_path: Path
) -> list[Path]:
    """Определить каталоги из INBOX, успешно обработанные без ошибок."""

    resolved_inbox = inbox_path.expanduser()
    try:
        resolved_inbox = resolved_inbox.resolve(strict=False)
    except OSError:
        pass

    states: dict[Path, dict[str, bool]] = {}
    for entry in entries:
        source = entry.source_path
        if source is None:
            continue
        project_dir = source.parent
        try:
            project_dir = project_dir.resolve(strict=False)
        except OSError:
            pass
        if project_dir != resolved_inbox and resolved_inbox not in project_dir.parents:
            continue
        state = states.setdefault(project_dir, {"success": False, "error": False})
        if entry.status == TransferStatus.SUCCESS:
            state["success"] = True
        elif entry.status == TransferStatus.ERROR:
            state["error"] = True
    result = [
        directory
        for directory, flags in states.items()
        if flags["success"] and not flags["error"] and directory.exists()
    ]
    result.sort()
    return result


def _confirm_cleanup_dialog(
    parent: tk.Tk, inbox_path: Path, candidates: list[Path]
) -> bool:
    """Показать диалог подтверждения очистки INBOX с полным списком папок."""

    dialog = tk.Toplevel(parent)
    dialog.title("Очистка INBOX")
    dialog.transient(parent)
    dialog.minsize(520, 320)
    dialog.grab_set()

    frame = ttk.Frame(dialog, padding=12)
    frame.pack(fill=tk.BOTH, expand=True)

    header = ttk.Label(
        frame,
        text=f"Удалить {len(candidates)} папок из {inbox_path}?",
        anchor="w",
        justify=tk.LEFT,
        wraplength=480,
    )
    header.pack(fill=tk.X)

    list_frame = ttk.Frame(frame)
    list_frame.pack(fill=tk.BOTH, expand=True, pady=(12, 12))
    scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL)
    listbox = tk.Listbox(
        list_frame,
        height=min(18, max(6, len(candidates))),
        width=70,
        exportselection=False,
        yscrollcommand=scrollbar.set,
    )
    scrollbar.config(command=listbox.yview)
    listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    resolved_inbox = inbox_path.expanduser()
    try:
        resolved_inbox = resolved_inbox.resolve(strict=False)
    except OSError:
        pass
    for path in candidates:
        try:
            display = path.resolve(strict=False).relative_to(resolved_inbox)
        except ValueError:
            display = Path(path)
        listbox.insert(tk.END, str(display))

    result = tk.BooleanVar(value=False, master=parent)

    def on_confirm() -> None:
        result.set(True)
        dialog.destroy()

    def on_cancel() -> None:
        result.set(False)
        dialog.destroy()

    button_frame = ttk.Frame(frame)
    button_frame.pack(fill=tk.X)
    ttk.Button(button_frame, text="Удалить", command=on_confirm).pack(
        side=tk.RIGHT, padx=(8, 0)
    )
    ttk.Button(button_frame, text="Отмена", command=on_cancel).pack(side=tk.RIGHT)

    dialog.bind("<Return>", lambda _event: on_confirm())
    dialog.bind("<Escape>", lambda _event: on_cancel())
    dialog.protocol("WM_DELETE_WINDOW", on_cancel)

    parent.wait_window(dialog)
    return bool(result.get())


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


def _update_summary(
    summary_var: tk.StringVar, entries: Iterable[TransferLogEntry]
) -> None:
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
    _configure_theme(root)
    is_running = tk.BooleanVar(value=False, master=root)
    root.title("ТОиР: распределение и журналы")
    root.geometry("1200x700")

    notebook = ttk.Notebook(root, style="TNotebook")
    notebook.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

    # --- Вкладка "Распределение" ---
    control_tab = ttk.Frame(notebook, padding=12, style="TFrame")
    notebook.add(control_tab, text="Распределение")

    ttk.Label(control_tab, text="Каталог входных данных").grid(
        row=0, column=0, sticky=tk.W
    )
    inbox_var = tk.StringVar(value=str(DEFAULT_INBOX))
    inbox_entry = ttk.Entry(control_tab, textvariable=inbox_var, width=80)
    inbox_entry.grid(row=1, column=0, sticky=tk.W)

    dest_vars: dict[str, tk.StringVar] = {"TOIR_INBOX_DIR": inbox_var}

    def select_directory(target_var: tk.StringVar, fallback: Path) -> None:
        """Выбрать каталог через диалог и обновить поле."""

        selected = filedialog.askdirectory(initialdir=target_var.get() or str(fallback))
        if selected:
            target_var.set(selected)

    def open_directory(target_var: tk.StringVar) -> None:
        """Открыть каталог, указанный в поле."""

        raw_value = target_var.get().strip()
        if not raw_value:
            messagebox.showinfo("Папка не задана", "Сначала укажите путь.")
            return
        _open_path(Path(raw_value).expanduser())

    def make_select_callback(
        target_var: tk.StringVar, default_path: Path
    ) -> Callable[[], None]:
        """Подготовить обработчик для выбора каталога."""

        def _callback() -> None:
            select_directory(target_var, default_path)

        return _callback

    def make_open_callback(target_var: tk.StringVar) -> Callable[[], None]:
        """Подготовить обработчик для открытия каталога."""

        def _callback() -> None:
            open_directory(target_var)

        return _callback

    def choose_inbox() -> None:
        select_directory(inbox_var, DEFAULT_INBOX)

    ttk.Button(control_tab, text="Выбрать...", command=choose_inbox).grid(
        row=1, column=1, padx=(8, 0)
    )
    ttk.Button(
        control_tab, text="Открыть", command=lambda: open_directory(inbox_var)
    ).grid(row=1, column=2, padx=(8, 0))

    ttk.Label(control_tab, text="Назначения").grid(
        row=2, column=0, sticky=tk.W, pady=(10, 2)
    )

    dest_frame = ttk.Frame(control_tab, style="Card.TFrame", padding=(8, 8))
    dest_frame.grid(row=3, column=0, columnspan=3, sticky=tk.EW, pady=(4, 6))
    for name, env_name, default_path in DESTINATION_CONFIG[1:]:
        row = ttk.Frame(dest_frame, style="Card.TFrame")
        row.pack(fill=tk.X, pady=1)
        ttk.Label(row, text=f"{name}:").pack(side=tk.LEFT, padx=(0, 6))
        var = tk.StringVar(value=str(default_path))
        dest_vars[env_name] = var
        ttk.Entry(row, textvariable=var, width=68).pack(
            side=tk.LEFT, fill=tk.X, expand=True
        )
        ttk.Button(
            row, text="Выбрать...", command=make_select_callback(var, default_path)
        ).pack(
            side=tk.LEFT,
            padx=(4, 0),
        )
        ttk.Button(row, text="Открыть", command=make_open_callback(var)).pack(
            side=tk.LEFT,
            padx=(4, 0),
        )

    status_var = tk.StringVar(value="Готово")
    status_label = ttk.Label(
        control_tab,
        textvariable=status_var,
        style="Status.TLabel",
    )
    status_label.grid(row=4, column=0, columnspan=3, sticky=tk.EW, pady=(10, 0))

    button_frame = ttk.Frame(control_tab)
    button_frame.grid(row=5, column=0, columnspan=3, sticky=tk.E, pady=(6, 0))

    log_frame = ttk.Frame(control_tab, style="Card.TFrame", padding=(8, 8))
    log_frame.grid(row=6, column=0, columnspan=3, sticky=tk.NSEW, pady=(6, 0))
    control_tab.rowconfigure(6, weight=1)
    control_tab.columnconfigure(0, weight=1)

    log_text = tk.Text(
        log_frame,
        wrap=tk.WORD,
        height=15,
        bg=FRAME_COLOR,
        fg=TEXT_COLOR,
        insertbackground=TEXT_COLOR,
        relief=tk.FLAT,
        borderwidth=0,
        highlightthickness=0,
        font=FONT_LABEL,
    )
    log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    log_scroll = ttk.Scrollbar(
        log_frame,
        orient="vertical",
        command=log_text.yview,
        style="Vertical.TScrollbar",
    )
    log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    log_text.configure(yscrollcommand=log_scroll.set)

    log_text.tag_config("info", foreground=TEXT_COLOR)
    log_text.tag_config("stdout", foreground="#2E7D32")
    log_text.tag_config("stderr", foreground="#C62828")
    log_text.tag_config("status", foreground="#1B5E20", font=FONT_BOLD)

    def append_log(message: str, tag: str = "info") -> None:
        if not message:
            return
        log_text.insert(tk.END, message, (tag,))
        log_text.see(tk.END)

    def clear_log() -> None:
        log_text.delete("1.0", tk.END)

    def cleanup_processed_projects() -> None:
        if is_running.get():
            messagebox.showinfo(
                "Очистка INBOX", "Дождитесь завершения текущего запуска."
            )
            return
        inbox_path = Path(inbox_var.get()).expanduser()
        if not inbox_path.exists():
            messagebox.showerror("Очистка INBOX", f"Папка не найдена: {inbox_path}")
            return
        runs = list_runs(base_dir=root_dir)
        if not runs:
            messagebox.showinfo("Очистка INBOX", "Журналы не найдены.")
            return
        entries = _load_entries(root_dir, runs[0].run_id)
        candidates = _collect_processed_projects(entries, inbox_path)
        if not candidates:
            messagebox.showinfo(
                "Очистка INBOX", "Нет завершённых проектов для удаления."
            )
            return
        if not _confirm_cleanup_dialog(root, inbox_path, candidates):
            return
        failures: list[tuple[Path, Exception]] = []
        removed = 0
        for directory in candidates:
            try:
                shutil.rmtree(directory)
                removed += 1
                append_log(f"[cleanup] Удалена папка {directory}\n", tag="stdout")
            except OSError as exc:
                failures.append((directory, exc))
                append_log(
                    f"[cleanup] Ошибка удаления {directory}: {exc}\n", tag="stderr"
                )
        if failures:
            message = "Не удалось удалить:\n" + "\n".join(
                f"• {path.name}: {exc}" for path, exc in failures
            )
            messagebox.showerror("Очистка INBOX", message)
        if removed:
            messagebox.showinfo("Очистка INBOX", f"Удалено папок: {removed}")

    cleanup_button = ttk.Button(
        button_frame, text="Удалить обработанные", command=cleanup_processed_projects
    )
    cleanup_button.pack(side=tk.LEFT, padx=(0, 12))

    def distribution_worker(env_overrides: dict[str, str]) -> None:
        env = os.environ.copy()
        env.setdefault("PYTHONIOENCODING", "utf-8")
        env.update(env_overrides)
        cmd = [sys.executable, str(PIPELINE_SCRIPT)]
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(REPO_ROOT),
            env=env,
        )
        result_queue.put((process.returncode, process.stdout, process.stderr))

    def handle_queue() -> None:
        if result_queue.empty():
            root.after(200, handle_queue)
            return
        returncode, stdout, stderr = result_queue.get()
        append_log(stdout or "", tag="stdout")
        if stderr:
            append_log("\n[stderr]\n" + stderr, tag="stderr")
        if returncode == 0:
            status_var.set("Готово")
            messagebox.showinfo("Распределение", "Обработка завершена успешно.")
            refresh_runs()
        else:
            status_var.set("Завершено с ошибками")
            messagebox.showerror(
                "Распределение", f"Скрипт завершился с кодом {returncode}."
            )
        run_button.config(state=tk.NORMAL)
        reset_button.config(state=tk.NORMAL)
        cleanup_button.config(state=tk.NORMAL)
        is_running.set(False)
        root.after(200, handle_queue)

    def start_distribution() -> None:
        if is_running.get():
            return
        overrides: dict[str, str] = {}
        for env_name, var in dest_vars.items():
            raw_value = var.get().strip()
            if not raw_value:
                label = DESTINATION_LABELS.get(env_name, env_name)
                messagebox.showerror("Ошибка", f"Укажите путь для {label}.")
                return
            resolved = Path(raw_value).expanduser()
            overrides[env_name] = str(resolved)
        inbox_path = Path(overrides["TOIR_INBOX_DIR"])
        if not inbox_path.exists():
            messagebox.showerror("Ошибка", f"Папка не найдена: {inbox_path}")
            return
        clear_log()
        status_var.set("Выполняется...")
        append_log(f"Запуск распределения для {inbox_path}\n\n")
        run_button.config(state=tk.DISABLED)
        reset_button.config(state=tk.DISABLED)
        cleanup_button.config(state=tk.DISABLED)
        is_running.set(True)
        thread = threading.Thread(
            target=distribution_worker, args=(overrides,), daemon=True
        )
        thread.start()

    def reset_paths_to_defaults() -> None:
        if is_running.get():
            messagebox.showinfo(
                "Сброс путей",
                "Дождитесь завершения обработки перед сбросом настроек.",
            )
            return
        for _, env_name, default_path in DESTINATION_CONFIG:
            dest_vars[env_name].set(str(default_path))
        status_var.set("Пути сброшены на значения по умолчанию")
        append_log("Сброс путей на значения по умолчанию\n", tag="status")

    run_button = ttk.Button(
        button_frame, text="Распределить", command=start_distribution
    )
    run_button.pack(side=tk.RIGHT, padx=(4, 0))

    reset_button = ttk.Button(
        button_frame,
        text="Сбросить пути",
        command=reset_paths_to_defaults,
    )
    reset_button.pack(side=tk.RIGHT, padx=(4, 0))

    ttk.Button(button_frame, text="Очистить лог", command=clear_log).pack(
        side=tk.RIGHT, padx=(4, 0)
    )

    # --- Вкладка "Журналы" ---
    logs_tab = ttk.Frame(notebook, padding=12, style="TFrame")
    notebook.add(logs_tab, text="Журналы")

    list_frame = ttk.Frame(logs_tab, style="Card.TFrame", padding=(8, 8))
    list_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

    ttk.Label(list_frame, text="Запуски", style="Card.TLabel").pack(anchor=tk.W)
    run_listbox = tk.Listbox(
        list_frame,
        height=13,
        exportselection=False,
        bg=FRAME_COLOR,
        fg=TEXT_COLOR,
        selectbackground=BUTTON_COLOR,
        selectforeground="white",
        highlightthickness=0,
        borderwidth=0,
        relief=tk.FLAT,
        font=FONT_LABEL,
    )
    run_listbox.pack(fill=tk.BOTH, expand=True)

    refresh_button = ttk.Button(list_frame, text="Обновить")
    refresh_button.pack(fill=tk.X, pady=(6, 0))

    summary_var = tk.StringVar(value="Журналы не найдены")
    ttk.Label(list_frame, textvariable=summary_var, style="Secondary.TLabel").pack(
        anchor=tk.W, pady=(6, 0)
    )

    tree_frame = ttk.Frame(logs_tab, style="Card.TFrame", padding=(8, 8))
    tree_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

    tree_container = ttk.Frame(tree_frame, style="Card.TFrame")
    tree_container.pack(fill=tk.BOTH, expand=True)

    columns = ("time", "action", "status", "source", "target", "message")
    tree = ttk.Treeview(
        tree_container, columns=columns, show="headings", selectmode="browse"
    )
    tree.grid(row=0, column=0, sticky="nsew")

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

    tree_scroll = ttk.Scrollbar(
        tree_container,
        orient="vertical",
        command=tree.yview,
        style="Vertical.TScrollbar",
    )
    tree_scroll.grid(row=0, column=1, sticky="ns")
    tree.configure(yscrollcommand=tree_scroll.set)

    tree_container.columnconfigure(0, weight=1)
    tree_container.rowconfigure(0, weight=1)

    tree_toolbar = ttk.Frame(tree_frame, style="TFrame")
    tree_toolbar.pack(fill=tk.X, pady=(6, 0))

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

    delete_button = ttk.Button(list_frame, text="Удалить все кроме последнего")
    delete_button.pack(fill=tk.X, pady=(4, 0))

    def delete_old_runs() -> None:
        runs = list_runs(base_dir=root_dir)
        if len(runs) <= 1:
            messagebox.showinfo("Журналы", "Нечего удалять.")
            return
        latest = runs[0]
        proceed = messagebox.askyesno(
            "Журналы", f"Удалить {len(runs) - 1} файлов, кроме {latest.run_id}?"
        )
        if not proceed:
            return
        for run in runs[1:]:
            try:
                run.file_path.unlink(missing_ok=True)  # type: ignore[arg-type]
            except OSError as exc:
                messagebox.showerror(
                    "Ошибка", f"Не удалось удалить {run.file_path}: {exc}"
                )
                return
        messagebox.showinfo("Журналы", "Удаление выполнено.")
        refresh_runs()

    delete_button.config(command=delete_old_runs)

    def open_selected_entry() -> None:
        if not current_entries:
            messagebox.showinfo("Подсказка", "Записи не найдены")
            return
        selection = tree.selection()
        if not selection:
            messagebox.showinfo("Подсказка", "Выберите строку в таблице")
            return
        index = int(selection[0])
        if index >= len(current_entries):
            return
        target_path = current_entries[index].target_path
        if target_path is None:
            messagebox.showinfo("Подсказка", "Для записи нет целевого пути")
            return
        _open_path(target_path.parent if target_path.is_file() else target_path)

    def open_all_targets() -> None:
        """Открыть все каталоги, найденные в текущем запуске."""

        if not current_entries:
            messagebox.showinfo("Просмотр", "Нет записей для просмотра")
            return
        unique_paths: list[Path] = []
        seen: set[str] = set()
        missing: list[Path] = []
        for entry in current_entries:
            target = entry.target_path
            if target is None:
                continue
            target_dir = target.parent if target.is_file() else target
            try:
                resolved = target_dir.resolve(strict=False)
            except OSError:
                resolved = target_dir
            key = str(resolved)
            if key in seen:
                continue
            seen.add(key)
            if resolved.exists():
                unique_paths.append(resolved)
            else:
                missing.append(target_dir)
        if missing:
            messagebox.showwarning(
                "Просмотр",
                "Не удалось открыть следующие пути:\n"
                + "\n".join(str(item) for item in missing),
            )
        if not unique_paths:
            if not missing:
                messagebox.showinfo("Просмотр", "Не найдено целевых каталогов")
            return
        for path in unique_paths:
            _open_path(path)

    ttk.Button(tree_toolbar, text="Открыть все папки", command=open_all_targets).pack(
        side=tk.LEFT
    )

    tree.bind("<Double-1>", lambda _event: open_selected_entry())
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
