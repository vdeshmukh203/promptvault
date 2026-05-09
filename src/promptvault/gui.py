"""Tkinter GUI for PromptVault — browse, edit, and render prompt templates."""
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Optional

from .vault import Promptvault, RenderError, TemplateNotFoundError


class _HistoryDialog(tk.Toplevel):
    """Modal showing the full version history of one template key."""

    def __init__(self, parent: tk.Widget, vault: Promptvault, key: str):
        super().__init__(parent)
        self.title(f"History — {key}")
        self.resizable(True, True)
        self.geometry("640x400")
        self.grab_set()

        cols = ("version", "saved_at", "tags", "content")
        tree = ttk.Treeview(self, columns=cols, show="headings")
        tree.heading("version", text="Ver")
        tree.heading("saved_at", text="Saved at (UTC)")
        tree.heading("tags", text="Tags")
        tree.heading("content", text="Content (first 80 chars)")
        tree.column("version", width=40, anchor=tk.CENTER)
        tree.column("saved_at", width=200)
        tree.column("tags", width=120)
        tree.column("content", width=260)

        for tv in vault.history(key):
            tree.insert(
                "",
                tk.END,
                values=(
                    tv.version,
                    tv.saved_at,
                    ", ".join(tv.tags),
                    tv.content[:80].replace("\n", "↵"),
                ),
            )

        sb = ttk.Scrollbar(self, command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        ttk.Button(self, text="Close", command=self.destroy).pack(pady=4)


class PromptVaultApp(tk.Tk):
    """Main PromptVault desktop application window."""

    def __init__(self, vault: Optional[Promptvault] = None):
        super().__init__()
        self.vault = vault or Promptvault()
        self.title("PromptVault")
        self.geometry("940x680")
        self.minsize(700, 520)
        self._current_key: Optional[str] = None
        self._build_ui()
        self._refresh_key_list()

    # ------------------------------------------------------------------ #
    # UI construction
    # ------------------------------------------------------------------ #

    def _build_ui(self) -> None:
        self._build_menu()

        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=4, pady=(4, 0))

        left = ttk.Frame(paned, width=210)
        paned.add(left, weight=1)
        self._build_left_panel(left)

        right = ttk.Frame(paned)
        paned.add(right, weight=4)
        self._build_right_panel(right)

        self._status_var = tk.StringVar(value="Ready")
        ttk.Label(self, textvariable=self._status_var, relief=tk.SUNKEN,
                  anchor=tk.W).pack(fill=tk.X, side=tk.BOTTOM, padx=2, pady=2)

    def _build_menu(self) -> None:
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=False)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New Template…", command=self._new_template,
                              accelerator="Ctrl+N")
        file_menu.add_separator()
        file_menu.add_command(label="Open Vault JSON…", command=self._open_vault)
        file_menu.add_command(label="Export Vault JSON…", command=self._export_json)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.destroy)

        edit_menu = tk.Menu(menubar, tearoff=False)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Rename Template…", command=self._rename_template)
        edit_menu.add_command(label="Delete Template", command=self._delete_template)
        edit_menu.add_command(label="View History…", command=self._show_history)

        self.bind_all("<Control-n>", lambda _e: self._new_template())

    def _build_left_panel(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text="Templates", font=("", 11, "bold")).pack(
            fill=tk.X, padx=6, pady=(6, 0))

        search_frame = ttk.Frame(parent)
        search_frame.pack(fill=tk.X, padx=6, pady=4)
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._on_search())
        ttk.Entry(search_frame, textvariable=self._search_var).pack(
            side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(search_frame, text="✕", width=2,
                   command=self._clear_search).pack(side=tk.LEFT, padx=(2, 0))

        list_frame = ttk.Frame(parent)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=6)
        self._key_listbox = tk.Listbox(list_frame, selectmode=tk.SINGLE,
                                        exportselection=False)
        sb = ttk.Scrollbar(list_frame, command=self._key_listbox.yview)
        self._key_listbox.configure(yscrollcommand=sb.set)
        self._key_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self._key_listbox.bind("<<ListboxSelect>>", self._on_key_select)

        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X, padx=6, pady=6)
        ttk.Button(btn_frame, text="New", command=self._new_template).pack(
            side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(btn_frame, text="Delete", command=self._delete_template).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 0))

    def _build_right_panel(self, parent: ttk.Frame) -> None:
        # Header: key name + version selector
        header = ttk.Frame(parent)
        header.pack(fill=tk.X, padx=6, pady=(6, 0))
        ttk.Label(header, text="Key:").pack(side=tk.LEFT)
        self._key_label = ttk.Label(header, text="—", font=("", 10, "bold"))
        self._key_label.pack(side=tk.LEFT, padx=(4, 20))
        ttk.Label(header, text="Version:").pack(side=tk.LEFT)
        self._version_var = tk.StringVar()
        self._version_combo = ttk.Combobox(header, textvariable=self._version_var,
                                            width=7, state="readonly")
        self._version_combo.pack(side=tk.LEFT)
        self._version_combo.bind("<<ComboboxSelected>>", self._on_version_select)
        ttk.Button(header, text="History…", command=self._show_history).pack(
            side=tk.LEFT, padx=(8, 0))

        # Tags row
        tag_frame = ttk.Frame(parent)
        tag_frame.pack(fill=tk.X, padx=6, pady=(4, 0))
        ttk.Label(tag_frame, text="Tags:").pack(side=tk.LEFT)
        self._tags_var = tk.StringVar()
        ttk.Entry(tag_frame, textvariable=self._tags_var).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 4))
        ttk.Label(tag_frame, text="(comma-separated)",
                  foreground="gray").pack(side=tk.LEFT)

        # Template content editor
        content_lf = ttk.LabelFrame(parent, text="Template Content  (Jinja2 syntax)")
        content_lf.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)
        self._content_text = tk.Text(content_lf, wrap=tk.WORD, undo=True,
                                      font=("Courier", 11))
        cs = ttk.Scrollbar(content_lf, command=self._content_text.yview)
        self._content_text.configure(yscrollcommand=cs.set)
        self._content_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        cs.pack(side=tk.RIGHT, fill=tk.Y)

        # Action buttons
        action_frame = ttk.Frame(parent)
        action_frame.pack(fill=tk.X, padx=6, pady=(0, 2))
        ttk.Button(action_frame, text="Save New Version",
                   command=self._save_version).pack(side=tk.LEFT)
        ttk.Button(action_frame, text="Rename…",
                   command=self._rename_template).pack(side=tk.LEFT, padx=6)

        # Render preview
        preview_lf = ttk.LabelFrame(parent, text="Render Preview")
        preview_lf.pack(fill=tk.X, padx=6, pady=(0, 6))
        var_row = ttk.Frame(preview_lf)
        var_row.pack(fill=tk.X, padx=4, pady=(4, 2))
        ttk.Label(var_row, text="Variables (key=value, …):").pack(side=tk.LEFT)
        self._vars_var = tk.StringVar()
        ttk.Entry(var_row, textvariable=self._vars_var).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        ttk.Button(var_row, text="Render", command=self._render_preview).pack(side=tk.LEFT)
        self._preview_text = tk.Text(preview_lf, height=4, wrap=tk.WORD,
                                      state=tk.DISABLED, font=("Courier", 11),
                                      background="#f5f5f5")
        ps = ttk.Scrollbar(preview_lf, command=self._preview_text.yview)
        self._preview_text.configure(yscrollcommand=ps.set)
        self._preview_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True,
                                 padx=(4, 0), pady=(0, 4))
        ps.pack(side=tk.RIGHT, fill=tk.Y, pady=(0, 4))

    # ------------------------------------------------------------------ #
    # Key-list helpers
    # ------------------------------------------------------------------ #

    def _refresh_key_list(self, keys: Optional[list] = None) -> None:
        if keys is None:
            keys = sorted(self.vault.keys())
        self._key_listbox.delete(0, tk.END)
        for k in keys:
            self._key_listbox.insert(tk.END, k)

    def _on_search(self) -> None:
        query = self._search_var.get().strip()
        if not query:
            self._refresh_key_list()
            return
        results = self.vault.search(query)
        self._refresh_key_list(sorted(results.keys()))

    def _clear_search(self) -> None:
        self._search_var.set("")

    def _on_key_select(self, _event=None) -> None:
        sel = self._key_listbox.curselection()
        if not sel:
            return
        self._load_key(self._key_listbox.get(sel[0]))

    def _load_key(self, key: str) -> None:
        self._current_key = key
        self._key_label.configure(text=key)
        history = self.vault.history(key)
        self._version_combo["values"] = [str(tv.version) for tv in history]
        if history:
            self._version_combo.set(str(history[-1].version))
            self._load_version(history[-1])

    def _on_version_select(self, _event=None) -> None:
        if not self._current_key or not self._version_var.get():
            return
        tv = self.vault.get(self._current_key, int(self._version_var.get()))
        if tv:
            self._load_version(tv)

    def _load_version(self, tv) -> None:
        self._content_text.delete("1.0", tk.END)
        self._content_text.insert("1.0", tv.content)
        self._tags_var.set(", ".join(tv.tags))
        self._set_status(
            f"Loaded '{self._current_key}' v{tv.version}  |  saved {tv.saved_at}")

    # ------------------------------------------------------------------ #
    # User actions
    # ------------------------------------------------------------------ #

    def _new_template(self) -> None:
        key = simpledialog.askstring("New Template", "Template key:", parent=self)
        if not key:
            return
        key = key.strip()
        if not key:
            return
        if key in self.vault.keys():
            messagebox.showwarning("Duplicate", f"Key '{key}' already exists.")
            return
        self.vault.save(key, "")
        self._refresh_key_list()
        keys = sorted(self.vault.keys())
        idx = keys.index(key)
        self._key_listbox.selection_clear(0, tk.END)
        self._key_listbox.selection_set(idx)
        self._key_listbox.see(idx)
        self._load_key(key)
        self._content_text.focus_set()

    def _save_version(self) -> None:
        if not self._current_key:
            messagebox.showinfo("No template selected",
                                "Select or create a template first.")
            return
        content = self._content_text.get("1.0", tk.END).rstrip("\n")
        raw_tags = self._tags_var.get()
        tags = [t.strip() for t in raw_tags.split(",") if t.strip()] or None
        tv = self.vault.save(self._current_key, content, tags=tags)
        self._load_key(self._current_key)
        self._version_combo.set(str(tv.version))
        self._set_status(f"Saved version {tv.version} of '{self._current_key}'")

    def _delete_template(self) -> None:
        if not self._current_key:
            return
        if not messagebox.askyesno(
                "Confirm delete",
                f"Delete all versions of '{self._current_key}'?",
                icon="warning"):
            return
        self.vault.delete(self._current_key)
        self._current_key = None
        self._key_label.configure(text="—")
        self._content_text.delete("1.0", tk.END)
        self._version_combo["values"] = []
        self._version_combo.set("")
        self._tags_var.set("")
        self._refresh_key_list()
        self._set_status("Template deleted.")

    def _rename_template(self) -> None:
        if not self._current_key:
            return
        new_key = simpledialog.askstring(
            "Rename", f"New name for '{self._current_key}':", parent=self)
        if not new_key:
            return
        new_key = new_key.strip()
        if not self.vault.rename(self._current_key, new_key):
            messagebox.showerror(
                "Cannot rename",
                f"Key '{new_key}' already exists or source key not found.")
            return
        old = self._current_key
        self._current_key = new_key
        self._key_label.configure(text=new_key)
        self._refresh_key_list()
        keys = sorted(self.vault.keys())
        idx = keys.index(new_key)
        self._key_listbox.selection_clear(0, tk.END)
        self._key_listbox.selection_set(idx)
        self._key_listbox.see(idx)
        self._set_status(f"Renamed '{old}' → '{new_key}'")

    def _show_history(self) -> None:
        if not self._current_key:
            return
        _HistoryDialog(self, self.vault, self._current_key)

    def _render_preview(self) -> None:
        if not self._current_key:
            return
        kwargs: dict = {}
        raw = self._vars_var.get().strip()
        if raw:
            for pair in raw.split(","):
                if "=" in pair:
                    k, _, val = pair.partition("=")
                    kwargs[k.strip()] = val.strip()
        ver = int(self._version_var.get()) if self._version_var.get() else None
        try:
            result = self.vault.render(self._current_key, ver, **kwargs)
        except (TemplateNotFoundError, RenderError) as exc:
            result = f"[Error] {exc}"
        self._preview_text.configure(state=tk.NORMAL)
        self._preview_text.delete("1.0", tk.END)
        self._preview_text.insert("1.0", result)
        self._preview_text.configure(state=tk.DISABLED)

    def _open_vault(self) -> None:
        path = filedialog.askopenfilename(
            title="Open Vault JSON",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")])
        if not path:
            return
        self.vault = Promptvault(path=path)
        self._current_key = None
        self._key_label.configure(text="—")
        self._content_text.delete("1.0", tk.END)
        self._version_combo["values"] = []
        self._version_combo.set("")
        self._tags_var.set("")
        self._refresh_key_list()
        self._set_status(f"Opened: {path}")

    def _export_json(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Export Vault JSON",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")])
        if path:
            self.vault.export_json(path)
            self._set_status(f"Exported to {path}")

    def _set_status(self, msg: str) -> None:
        self._status_var.set(msg)


def launch_gui(vault: Optional[Promptvault] = None) -> None:
    """Launch the PromptVault desktop GUI.

    Parameters
    ----------
    vault:
        An existing :class:`Promptvault` instance to edit.  A new
        in-memory vault is created when omitted.
    """
    app = PromptVaultApp(vault=vault)
    app.mainloop()
