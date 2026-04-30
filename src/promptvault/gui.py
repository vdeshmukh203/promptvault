"""Tkinter graphical interface for promptvault."""
from __future__ import annotations

import re
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Optional

from .vault import Promptvault, RenderError, TemplateVersion


class _RenderDialog(tk.Toplevel):
    """Modal dialog that collects values for Jinja2 variables and shows the result."""

    def __init__(self, parent: tk.Tk, tv: TemplateVersion) -> None:
        super().__init__(parent)
        self.title("Render template")
        self.resizable(True, True)
        self.grab_set()

        var_names = sorted(set(re.findall(r"\{\{\s*(\w+)\s*\}\}", tv.content)))
        self._entries: dict[str, tk.StringVar] = {}

        frame = ttk.Frame(self, padding=8)
        frame.pack(fill="both", expand=True)

        if var_names:
            ttk.Label(frame, text="Fill in template variables:").grid(
                row=0, column=0, columnspan=2, sticky="w", pady=(0, 6)
            )
            for i, name in enumerate(var_names, start=1):
                ttk.Label(frame, text=f"{name}:").grid(row=i, column=0, sticky="w", pady=2)
                sv = tk.StringVar()
                ttk.Entry(frame, textvariable=sv, width=40).grid(
                    row=i, column=1, sticky="ew", padx=(8, 0), pady=2
                )
                self._entries[name] = sv
            frame.columnconfigure(1, weight=1)
        else:
            ttk.Label(frame, text="No variables detected — click Render to proceed.").grid(
                row=0, column=0, columnspan=2
            )

        btn_row = len(var_names) + 1
        ttk.Button(frame, text="Render", command=lambda: self._do_render(tv)).grid(
            row=btn_row, column=0, pady=(10, 0), sticky="w"
        )
        ttk.Button(frame, text="Cancel", command=self.destroy).grid(
            row=btn_row, column=1, pady=(10, 0), sticky="e"
        )

    def _do_render(self, tv: TemplateVersion) -> None:
        kwargs = {name: sv.get() for name, sv in self._entries.items()}
        try:
            result = tv.render(**kwargs)
        except RenderError as exc:
            messagebox.showerror("Render error", str(exc), parent=self)
            return

        self.destroy()
        win = tk.Toplevel()
        win.title("Rendered output")
        win.geometry("680x420")
        txt = tk.Text(win, wrap="word", font=("Courier", 11))
        txt.pack(fill="both", expand=True, padx=8, pady=8)
        txt.insert("1.0", result)
        txt.config(state="disabled")
        ttk.Button(win, text="Close", command=win.destroy).pack(pady=4)


class PromptVaultApp(tk.Tk):
    """Main promptvault GUI window."""

    def __init__(self) -> None:
        super().__init__()
        self.title("promptvault")
        self.geometry("960x620")
        self.minsize(640, 400)

        self.vault = Promptvault()
        self._vault_path: Optional[Path] = None
        self._current_key: Optional[str] = None

        self._build_menu()
        self._build_toolbar()
        self._build_main_pane()
        self._build_status_bar()

        self._refresh_key_list()

    # ------------------------------------------------------------------ build

    def _build_menu(self) -> None:
        bar = tk.Menu(self)
        file_menu = tk.Menu(bar, tearoff=False)
        file_menu.add_command(label="New vault", command=self._new_vault)
        file_menu.add_command(label="Open vault…", command=self._open_vault)
        file_menu.add_command(label="Save vault", command=self._save_vault, accelerator="Ctrl+S")
        file_menu.add_command(label="Save vault as…", command=self._save_vault_as)
        file_menu.add_separator()
        file_menu.add_command(label="Quit", command=self.quit, accelerator="Ctrl+Q")
        bar.add_cascade(label="File", menu=file_menu)
        self.config(menu=bar)
        self.bind_all("<Control-s>", lambda _e: self._save_vault())
        self.bind_all("<Control-q>", lambda _e: self.quit())

    def _build_toolbar(self) -> None:
        tb = ttk.Frame(self, padding=(6, 4))
        tb.pack(fill="x", side="top")

        ttk.Label(tb, text="Search:").pack(side="left")
        self._search_var = tk.StringVar()
        ttk.Entry(tb, textvariable=self._search_var, width=28).pack(side="left", padx=4)
        ttk.Button(tb, text="Go", command=self._do_search, width=4).pack(side="left")
        ttk.Button(tb, text="Clear", command=self._clear_search, width=5).pack(side="left", padx=(2, 0))

    def _build_main_pane(self) -> None:
        pane = ttk.PanedWindow(self, orient="horizontal")
        pane.pack(fill="both", expand=True, padx=6, pady=6)

        # --- left: key list ---
        left = ttk.Frame(pane, width=190)
        pane.add(left, weight=1)

        ttk.Label(left, text="Templates").pack(anchor="w")

        list_frame = ttk.Frame(left)
        list_frame.pack(fill="both", expand=True)
        sb = ttk.Scrollbar(list_frame, orient="vertical")
        self._key_list = tk.Listbox(
            list_frame,
            selectmode="single",
            exportselection=False,
            yscrollcommand=sb.set,
            activestyle="dotbox",
        )
        sb.config(command=self._key_list.yview)
        sb.pack(side="right", fill="y")
        self._key_list.pack(side="left", fill="both", expand=True)
        self._key_list.bind("<<ListboxSelect>>", self._on_key_select)

        ttk.Button(left, text="+ New template", command=self._new_template).pack(
            fill="x", pady=(4, 0)
        )

        # --- right: editor ---
        right = ttk.Frame(pane)
        pane.add(right, weight=5)

        meta = ttk.Frame(right)
        meta.pack(fill="x", pady=(0, 4))

        ttk.Label(meta, text="Key:").grid(row=0, column=0, sticky="w")
        self._key_var = tk.StringVar()
        self._key_entry = ttk.Entry(meta, textvariable=self._key_var, width=32)
        self._key_entry.grid(row=0, column=1, sticky="w", padx=(4, 16))

        ttk.Label(meta, text="Version:").grid(row=0, column=2, sticky="w")
        self._version_var = tk.StringVar()
        self._version_cb = ttk.Combobox(
            meta, textvariable=self._version_var, width=20, state="readonly"
        )
        self._version_cb.grid(row=0, column=3, sticky="w", padx=4)
        self._version_cb.bind("<<ComboboxSelected>>", self._on_version_select)

        ttk.Label(meta, text="Tags (comma-separated):").grid(
            row=1, column=0, sticky="w", pady=(4, 0)
        )
        self._tags_var = tk.StringVar()
        ttk.Entry(meta, textvariable=self._tags_var, width=50).grid(
            row=1, column=1, columnspan=3, sticky="w", padx=(4, 0), pady=(4, 0)
        )

        ttk.Label(right, text="Content (Jinja2 syntax — use {{ variable }}):").pack(anchor="w")

        text_frame = ttk.Frame(right)
        text_frame.pack(fill="both", expand=True)
        vsb = ttk.Scrollbar(text_frame, orient="vertical")
        self._content_text = tk.Text(
            text_frame,
            wrap="word",
            font=("Courier", 11),
            undo=True,
            yscrollcommand=vsb.set,
        )
        vsb.config(command=self._content_text.yview)
        vsb.pack(side="right", fill="y")
        self._content_text.pack(side="left", fill="both", expand=True)

        btn_frame = ttk.Frame(right)
        btn_frame.pack(fill="x", pady=(6, 0))
        ttk.Button(btn_frame, text="Save version", command=self._save_template).pack(
            side="left", padx=(0, 4)
        )
        ttk.Button(btn_frame, text="Delete key", command=self._delete_key).pack(
            side="left", padx=4
        )
        ttk.Button(btn_frame, text="Delete version", command=self._delete_version).pack(
            side="left", padx=4
        )
        ttk.Button(btn_frame, text="Render…", command=self._render_template).pack(
            side="left", padx=4
        )

    def _build_status_bar(self) -> None:
        self._status_var = tk.StringVar(value="Ready")
        ttk.Label(self, textvariable=self._status_var, relief="sunken", anchor="w").pack(
            fill="x", side="bottom", padx=6, pady=(0, 4)
        )

    # ------------------------------------------------------------------ list

    def _refresh_key_list(self, keys: Optional[list] = None) -> None:
        self._key_list.delete(0, "end")
        for k in (keys if keys is not None else sorted(self.vault.keys())):
            self._key_list.insert("end", k)

    def _on_key_select(self, _event: object = None) -> None:
        sel = self._key_list.curselection()
        if not sel:
            return
        self._load_key(self._key_list.get(sel[0]))

    def _load_key(self, key: str) -> None:
        self._current_key = key
        self._key_var.set(key)
        versions = self.vault.history(key)
        labels = [f"v{v.version}  {v.saved_at[:10]}" for v in versions]
        self._version_cb["values"] = labels
        if labels:
            self._version_cb.current(len(labels) - 1)
        self._load_version(versions[-1] if versions else None)

    def _on_version_select(self, _event: object = None) -> None:
        key = self._key_var.get().strip()
        if not key:
            return
        versions = self.vault.history(key)
        idx = self._version_cb.current()
        if 0 <= idx < len(versions):
            self._load_version(versions[idx])

    def _load_version(self, tv: Optional[TemplateVersion]) -> None:
        self._content_text.delete("1.0", "end")
        self._tags_var.set("")
        if tv is None:
            return
        self._content_text.insert("1.0", tv.content)
        self._tags_var.set(", ".join(tv.tags))

    # ---------------------------------------------------------------- actions

    def _new_template(self) -> None:
        self._current_key = None
        self._key_var.set("")
        self._tags_var.set("")
        self._content_text.delete("1.0", "end")
        self._version_cb.set("")
        self._version_cb["values"] = []
        self._key_entry.focus()
        self._status_var.set("Enter a key name and content, then click 'Save version'.")

    def _save_template(self) -> None:
        key = self._key_var.get().strip()
        if not key:
            messagebox.showerror("Error", "Template key cannot be empty.")
            return
        content = self._content_text.get("1.0", "end-1c")
        raw_tags = self._tags_var.get()
        tags = [t.strip() for t in raw_tags.split(",") if t.strip()]
        self.vault.save(key, content, tags=tags or None)
        self._refresh_key_list()
        self._highlight_key(key)
        self._load_key(key)
        self._status_var.set(f"Saved new version of '{key}'.")

    def _delete_key(self) -> None:
        key = self._key_var.get().strip()
        if not key:
            return
        if not messagebox.askyesno("Confirm", f"Delete all versions of '{key}'?"):
            return
        self.vault.delete(key)
        self._new_template()
        self._refresh_key_list()
        self._status_var.set(f"Deleted '{key}'.")

    def _delete_version(self) -> None:
        key = self._key_var.get().strip()
        if not key:
            return
        idx = self._version_cb.current()
        versions = self.vault.history(key)
        if idx < 0 or idx >= len(versions):
            return
        version_num = versions[idx].version
        if not messagebox.askyesno("Confirm", f"Delete v{version_num} of '{key}'?"):
            return
        self.vault.delete_version(key, version_num)
        remaining = self.vault.history(key)
        if remaining:
            self._load_key(key)
        else:
            self.vault.delete(key)
            self._new_template()
            self._refresh_key_list()
        self._status_var.set(f"Deleted v{version_num} of '{key}'.")

    def _render_template(self) -> None:
        key = self._key_var.get().strip()
        if not key:
            messagebox.showerror("Error", "No template selected.")
            return
        idx = self._version_cb.current()
        versions = self.vault.history(key)
        if not versions:
            return
        tv = versions[idx] if 0 <= idx < len(versions) else versions[-1]
        _RenderDialog(self, tv)

    # ----------------------------------------------------------------- search

    def _do_search(self) -> None:
        query = self._search_var.get().strip()
        if not query:
            self._refresh_key_list()
            return
        results = self.vault.search(query)
        self._refresh_key_list(sorted(results.keys()))
        self._status_var.set(
            f"Found {len(results)} template(s) matching '{query}'."
            if results
            else f"No templates matching '{query}'."
        )

    def _clear_search(self) -> None:
        self._search_var.set("")
        self._refresh_key_list()
        self._status_var.set("Ready")

    # --------------------------------------------------------------- file I/O

    def _new_vault(self) -> None:
        self.vault = Promptvault()
        self._vault_path = None
        self._new_template()
        self._refresh_key_list()
        self._status_var.set("New vault created.")

    def _open_vault(self) -> None:
        path = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            self.vault = Promptvault.load_from_file(path)
            self._vault_path = Path(path)
            self._new_template()
            self._refresh_key_list()
            self._status_var.set(f"Opened '{path}'.")
        except Exception as exc:
            messagebox.showerror("Error", f"Could not open vault:\n{exc}")

    def _save_vault(self) -> None:
        if self._vault_path is None:
            self._save_vault_as()
            return
        try:
            self.vault.save_to_file(self._vault_path)
            self._status_var.set(f"Saved to '{self._vault_path}'.")
        except Exception as exc:
            messagebox.showerror("Error", f"Could not save vault:\n{exc}")

    def _save_vault_as(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        self._vault_path = Path(path)
        self._save_vault()

    # ---------------------------------------------------------------- helpers

    def _highlight_key(self, key: str) -> None:
        keys = sorted(self.vault.keys())
        if key in keys:
            idx = keys.index(key)
            self._key_list.selection_clear(0, "end")
            self._key_list.selection_set(idx)
            self._key_list.see(idx)


def main() -> None:
    """Launch the promptvault GUI."""
    app = PromptVaultApp()
    app.mainloop()


if __name__ == "__main__":
    main()
