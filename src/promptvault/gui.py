"""Tkinter GUI for promptvault — browse, edit, render, and persist templates."""
from __future__ import annotations

import sys
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Optional

from .vault import Promptvault, RenderError


class PromptVaultApp(tk.Tk):
    def __init__(self, vault: Optional[Promptvault] = None):
        super().__init__()
        self.title("promptvault")
        self.geometry("960x640")
        self.minsize(720, 480)
        self._vault_path: Optional[str] = None
        self.vault = vault or Promptvault()
        self._build_menu()
        self._build_ui()
        self._refresh_key_list()

    # ------------------------------------------------------------------
    # Menu bar
    # ------------------------------------------------------------------

    def _build_menu(self):
        mb = tk.Menu(self)
        self.config(menu=mb)

        file_menu = tk.Menu(mb, tearoff=False)
        mb.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New Vault", command=self._new_vault)
        file_menu.add_command(label="Open Vault…", command=self._open_vault)
        file_menu.add_command(label="Save Vault As…", command=self._save_vault_as)
        file_menu.add_separator()
        file_menu.add_command(label="Quit", command=self.destroy)

        tmpl_menu = tk.Menu(mb, tearoff=False)
        mb.add_cascade(label="Template", menu=tmpl_menu)
        tmpl_menu.add_command(label="New Template…", command=self._new_template)
        tmpl_menu.add_command(label="Rename Template…", command=self._rename_template)
        tmpl_menu.add_command(label="Delete Template", command=self._delete_template)

    # ------------------------------------------------------------------
    # Main UI layout
    # ------------------------------------------------------------------

    def _build_ui(self):
        # Top toolbar
        toolbar = ttk.Frame(self, padding=4)
        toolbar.pack(side=tk.TOP, fill=tk.X)

        ttk.Label(toolbar, text="Search:").pack(side=tk.LEFT)
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._on_search())
        ttk.Entry(toolbar, textvariable=self._search_var, width=28).pack(side=tk.LEFT, padx=(4, 12))

        ttk.Label(toolbar, text="Tag filter:").pack(side=tk.LEFT)
        self._tag_var = tk.StringVar()
        self._tag_var.trace_add("write", lambda *_: self._on_search())
        ttk.Entry(toolbar, textvariable=self._tag_var, width=16).pack(side=tk.LEFT, padx=(4, 0))

        ttk.Button(toolbar, text="New Template", command=self._new_template).pack(side=tk.RIGHT, padx=4)

        # Main pane: key list (left) + editor (right)
        pane = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        pane.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)

        # Left: key list
        left = ttk.Frame(pane, width=220)
        pane.add(left, weight=1)

        ttk.Label(left, text="Templates").pack(anchor=tk.W, padx=4)
        self._key_list = tk.Listbox(left, selectmode=tk.SINGLE, activestyle="dotbox")
        self._key_list.pack(fill=tk.BOTH, expand=True, padx=4, pady=(0, 4))
        self._key_list.bind("<<ListboxSelect>>", lambda _: self._on_key_select())

        # Right: editor panel
        right = ttk.Frame(pane)
        pane.add(right, weight=4)

        # Version chooser row
        ver_row = ttk.Frame(right)
        ver_row.pack(fill=tk.X, padx=4, pady=(0, 2))
        ttk.Label(ver_row, text="Version:").pack(side=tk.LEFT)
        self._version_var = tk.StringVar()
        self._version_cb = ttk.Combobox(ver_row, textvariable=self._version_var,
                                        state="readonly", width=10)
        self._version_cb.pack(side=tk.LEFT, padx=(4, 16))
        self._version_cb.bind("<<ComboboxSelected>>", lambda _: self._on_version_select())

        ttk.Label(ver_row, text="Tags:").pack(side=tk.LEFT)
        self._tags_label = ttk.Label(ver_row, text="", foreground="#0066cc")
        self._tags_label.pack(side=tk.LEFT, padx=(4, 0))

        # Template content editor
        ttk.Label(right, text="Template content (Jinja2 syntax: {{ variable }})").pack(
            anchor=tk.W, padx=4)
        self._content_text = tk.Text(right, wrap=tk.WORD, undo=True,
                                     font=("Courier", 11), height=10)
        self._content_text.pack(fill=tk.BOTH, expand=True, padx=4, pady=(0, 4))

        # Save / tag row
        save_row = ttk.Frame(right)
        save_row.pack(fill=tk.X, padx=4, pady=(0, 6))
        ttk.Label(save_row, text="Tags (comma-sep):").pack(side=tk.LEFT)
        self._new_tags_var = tk.StringVar()
        ttk.Entry(save_row, textvariable=self._new_tags_var, width=30).pack(
            side=tk.LEFT, padx=(4, 12))
        ttk.Button(save_row, text="Save as new version",
                   command=self._save_version).pack(side=tk.LEFT)

        # Render section
        ttk.Separator(right, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=4, pady=4)
        ttk.Label(right, text="Render variables (key=value, one per line):").pack(
            anchor=tk.W, padx=4)
        self._vars_text = tk.Text(right, wrap=tk.WORD, height=4,
                                  font=("Courier", 10))
        self._vars_text.pack(fill=tk.X, padx=4, pady=(0, 4))

        render_row = ttk.Frame(right)
        render_row.pack(fill=tk.X, padx=4, pady=(0, 4))
        ttk.Button(render_row, text="Render", command=self._render).pack(side=tk.LEFT)
        ttk.Label(render_row, text="Output:").pack(side=tk.LEFT, padx=(16, 0))

        self._render_text = tk.Text(right, wrap=tk.WORD, height=5,
                                    font=("Courier", 10), state=tk.DISABLED,
                                    background="#f5f5f5")
        self._render_text.pack(fill=tk.X, padx=4, pady=(0, 6))

        # Status bar
        self._status_var = tk.StringVar(value="Ready")
        ttk.Label(self, textvariable=self._status_var, relief=tk.SUNKEN,
                  anchor=tk.W).pack(side=tk.BOTTOM, fill=tk.X)

    # ------------------------------------------------------------------
    # State helpers
    # ------------------------------------------------------------------

    def _selected_key(self) -> Optional[str]:
        sel = self._key_list.curselection()
        if not sel:
            return None
        return self._key_list.get(sel[0])

    def _selected_version_num(self) -> Optional[int]:
        val = self._version_var.get()
        if not val:
            return None
        try:
            return int(val.split()[0])
        except (ValueError, IndexError):
            return None

    def _set_status(self, msg: str):
        self._status_var.set(msg)

    # ------------------------------------------------------------------
    # Refresh helpers
    # ------------------------------------------------------------------

    def _refresh_key_list(self, select_key: Optional[str] = None):
        query = self._search_var.get().strip()
        tag = self._tag_var.get().strip()

        if tag:
            matched_keys = set(self.vault.search_by_tag(tag).keys())
        else:
            matched_keys = None

        if query:
            content_keys = set(self.vault.search(query).keys())
        else:
            content_keys = None

        keys = self.vault.keys()
        if matched_keys is not None:
            keys = [k for k in keys if k in matched_keys]
        if content_keys is not None:
            keys = [k for k in keys if k in content_keys]

        self._key_list.delete(0, tk.END)
        for k in sorted(keys):
            self._key_list.insert(tk.END, k)

        if select_key:
            for i in range(self._key_list.size()):
                if self._key_list.get(i) == select_key:
                    self._key_list.selection_set(i)
                    self._key_list.see(i)
                    self._on_key_select()
                    break

    def _refresh_version_list(self, key: str):
        history = self.vault.history(key)
        values = [f"{v.version}  ({v.saved_at[:10]})" for v in history]
        self._version_cb["values"] = values
        if values:
            self._version_cb.current(len(values) - 1)
        self._on_version_select()

    def _load_version_into_editor(self, key: str, version_num: Optional[int]):
        tv = self.vault.get(key, version_num)
        if tv is None:
            return
        self._content_text.delete("1.0", tk.END)
        self._content_text.insert("1.0", tv.content)
        self._tags_label.config(text=", ".join(tv.tags) if tv.tags else "(none)")
        self._new_tags_var.set(", ".join(tv.tags))
        self._render_text.config(state=tk.NORMAL)
        self._render_text.delete("1.0", tk.END)
        self._render_text.config(state=tk.DISABLED)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_key_select(self):
        key = self._selected_key()
        if key:
            self._refresh_version_list(key)

    def _on_version_select(self):
        key = self._selected_key()
        if key:
            self._load_version_into_editor(key, self._selected_version_num())

    def _on_search(self):
        self._refresh_key_list()

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _save_version(self):
        key = self._selected_key()
        if not key:
            messagebox.showwarning("No template selected",
                                   "Select or create a template first.")
            return
        content = self._content_text.get("1.0", tk.END).rstrip("\n")
        raw_tags = self._new_tags_var.get()
        tags = [t.strip() for t in raw_tags.split(",") if t.strip()]
        self.vault.save(key, content, tags=tags)
        self._refresh_version_list(key)
        self._set_status(f"Saved new version of '{key}'.")

    def _render(self):
        key = self._selected_key()
        if not key:
            return
        version_num = self._selected_version_num()
        raw = self._vars_text.get("1.0", tk.END).strip()
        kwargs = {}
        for line in raw.splitlines():
            line = line.strip()
            if "=" in line:
                k, _, v = line.partition("=")
                kwargs[k.strip()] = v.strip()
        try:
            result = self.vault.render(key, version=version_num, **kwargs)
        except RenderError as exc:
            messagebox.showerror("Render error", str(exc))
            return
        self._render_text.config(state=tk.NORMAL)
        self._render_text.delete("1.0", tk.END)
        self._render_text.insert("1.0", result or "")
        self._render_text.config(state=tk.DISABLED)
        self._set_status("Rendered successfully.")

    def _new_template(self):
        key = simpledialog.askstring("New Template", "Template key:")
        if not key or not key.strip():
            return
        key = key.strip()
        if key in self.vault.keys():
            messagebox.showwarning("Exists", f"Template '{key}' already exists.")
            return
        self.vault.save(key, "")
        self._refresh_key_list(select_key=key)
        self._set_status(f"Created template '{key}'.")

    def _rename_template(self):
        key = self._selected_key()
        if not key:
            return
        new_key = simpledialog.askstring("Rename", f"New name for '{key}':")
        if not new_key or not new_key.strip():
            return
        new_key = new_key.strip()
        if not self.vault.rename(key, new_key):
            messagebox.showerror("Rename failed",
                                 f"Could not rename: '{new_key}' may already exist.")
            return
        self._refresh_key_list(select_key=new_key)
        self._set_status(f"Renamed '{key}' → '{new_key}'.")

    def _delete_template(self):
        key = self._selected_key()
        if not key:
            return
        if not messagebox.askyesno("Delete", f"Delete all versions of '{key}'?"):
            return
        self.vault.delete(key)
        self._refresh_key_list()
        self._set_status(f"Deleted '{key}'.")

    # ------------------------------------------------------------------
    # File operations
    # ------------------------------------------------------------------

    def _new_vault(self):
        if not messagebox.askyesno("New Vault", "Discard current vault and start fresh?"):
            return
        self.vault = Promptvault()
        self._vault_path = None
        self.title("promptvault")
        self._refresh_key_list()
        self._set_status("New vault created.")

    def _open_vault(self):
        path = filedialog.askopenfilename(
            title="Open Vault",
            filetypes=[("JSON files", "*.json"), ("All files", "*")],
        )
        if not path:
            return
        try:
            self.vault = Promptvault(path=path)
            self._vault_path = path
            self.title(f"promptvault — {path}")
            self._refresh_key_list()
            self._set_status(f"Opened '{path}'.")
        except Exception as exc:
            messagebox.showerror("Open failed", str(exc))

    def _save_vault_as(self):
        path = filedialog.asksaveasfilename(
            title="Save Vault As",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*")],
        )
        if not path:
            return
        try:
            self.vault.save_to_file(path)
            self._vault_path = path
            self.title(f"promptvault — {path}")
            self._set_status(f"Saved to '{path}'.")
        except Exception as exc:
            messagebox.showerror("Save failed", str(exc))


def main():
    app = PromptVaultApp()
    app.mainloop()


if __name__ == "__main__":
    main()
