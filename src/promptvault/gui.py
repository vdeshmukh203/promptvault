"""Tkinter GUI for PromptVault."""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Optional

from .vault import Promptvault, TemplateVersion


class PromptVaultApp(tk.Tk):
    """Main application window."""

    def __init__(self) -> None:
        super().__init__()
        self.vault = Promptvault()
        self.title("PromptVault")
        self.geometry("1050x680")
        self.minsize(700, 480)
        self._current_key: Optional[str] = None
        self._build_ui()
        self._refresh_key_list()

    # ------------------------------------------------------------------ #
    # UI construction                                                       #
    # ------------------------------------------------------------------ #

    def _build_ui(self) -> None:
        self._build_menu()
        self._build_toolbar()
        self._build_main_area()
        self._build_status_bar()

    def _build_menu(self) -> None:
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=False)
        file_menu.add_command(
            label="New Template…", accelerator="Ctrl+N", command=self._on_new
        )
        file_menu.add_separator()
        file_menu.add_command(label="Export Vault…", command=self._on_export)
        file_menu.add_command(label="Import Vault…", command=self._on_import)
        file_menu.add_separator()
        file_menu.add_command(
            label="Quit", accelerator="Ctrl+Q", command=self.destroy
        )
        menubar.add_cascade(label="File", menu=file_menu)

        edit_menu = tk.Menu(menubar, tearoff=False)
        edit_menu.add_command(
            label="Save Version", accelerator="Ctrl+S", command=self._on_save_version
        )
        edit_menu.add_command(label="Rename Template…", command=self._on_rename)
        edit_menu.add_command(label="Delete Template", command=self._on_delete)
        menubar.add_cascade(label="Edit", menu=edit_menu)

        self.bind_all("<Control-n>", lambda _e: self._on_new())
        self.bind_all("<Control-s>", lambda _e: self._on_save_version())
        self.bind_all("<Control-q>", lambda _e: self.destroy())

    def _build_toolbar(self) -> None:
        bar = ttk.Frame(self, padding=(4, 3))
        bar.pack(side=tk.TOP, fill=tk.X)

        for label, cmd in (
            ("New", self._on_new),
            ("Save Version", self._on_save_version),
            ("Rename", self._on_rename),
            ("Delete", self._on_delete),
        ):
            ttk.Button(bar, text=label, command=cmd).pack(side=tk.LEFT, padx=2)

        ttk.Separator(bar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6)

        for label, cmd in (
            ("Export…", self._on_export),
            ("Import…", self._on_import),
        ):
            ttk.Button(bar, text=label, command=cmd).pack(side=tk.LEFT, padx=2)

        ttk.Separator(bar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6)

        ttk.Label(bar, text="Search:").pack(side=tk.LEFT, padx=(0, 2))
        self._search_var = tk.StringVar()
        search_entry = ttk.Entry(bar, textvariable=self._search_var, width=22)
        search_entry.pack(side=tk.LEFT, padx=2)
        search_entry.bind("<Return>", lambda _e: self._on_search())
        ttk.Button(bar, text="Go", command=self._on_search).pack(side=tk.LEFT)
        ttk.Button(bar, text="Clear", command=self._on_search_clear).pack(
            side=tk.LEFT, padx=2
        )

    def _build_main_area(self) -> None:
        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)

        # ---- left: template list ----
        left = ttk.Frame(paned, width=200)
        paned.add(left, weight=1)

        ttk.Label(left, text="Templates", font=("", 10, "bold")).pack(
            anchor=tk.W, pady=(0, 2)
        )

        listframe = ttk.Frame(left)
        listframe.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(listframe, orient=tk.VERTICAL)
        self._key_list = tk.Listbox(
            listframe,
            selectmode=tk.SINGLE,
            activestyle="none",
            yscrollcommand=scrollbar.set,
        )
        scrollbar.config(command=self._key_list.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._key_list.pack(fill=tk.BOTH, expand=True)
        self._key_list.bind("<<ListboxSelect>>", self._on_key_select)

        # ---- right: tabbed editor ----
        right = ttk.Frame(paned)
        paned.add(right, weight=3)

        self._notebook = ttk.Notebook(right)
        self._notebook.pack(fill=tk.BOTH, expand=True)

        self._build_editor_tab()
        self._build_history_tab()
        self._build_render_tab()

    def _build_editor_tab(self) -> None:
        tab = ttk.Frame(self._notebook, padding=8)
        self._notebook.add(tab, text="Editor")

        meta_row = ttk.Frame(tab)
        meta_row.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(meta_row, text="Key:").pack(side=tk.LEFT)
        self._key_label = ttk.Label(meta_row, text="(none)", foreground="grey")
        self._key_label.pack(side=tk.LEFT, padx=6)

        tags_row = ttk.Frame(tab)
        tags_row.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(tags_row, text="Tags (comma-separated):").pack(side=tk.LEFT)
        self._tags_var = tk.StringVar()
        ttk.Entry(tags_row, textvariable=self._tags_var).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=6
        )

        ttk.Label(tab, text="Template Content:").pack(anchor=tk.W)
        cf = ttk.Frame(tab)
        cf.pack(fill=tk.BOTH, expand=True, pady=(2, 0))
        ys = ttk.Scrollbar(cf, orient=tk.VERTICAL)
        self._content_text = tk.Text(
            cf,
            wrap=tk.WORD,
            undo=True,
            font=("Courier", 11),
            yscrollcommand=ys.set,
        )
        ys.config(command=self._content_text.yview)
        ys.pack(side=tk.RIGHT, fill=tk.Y)
        self._content_text.pack(fill=tk.BOTH, expand=True)

    def _build_history_tab(self) -> None:
        tab = ttk.Frame(self._notebook, padding=8)
        self._notebook.add(tab, text="History")

        cols = ("version", "saved_at", "tags")
        self._history_tree = ttk.Treeview(
            tab, columns=cols, show="headings", selectmode="browse"
        )
        self._history_tree.heading("version", text="Ver.")
        self._history_tree.heading("saved_at", text="Saved At (UTC)")
        self._history_tree.heading("tags", text="Tags")
        self._history_tree.column("version", width=55, anchor=tk.CENTER)
        self._history_tree.column("saved_at", width=260)
        self._history_tree.column("tags", width=200)

        ys = ttk.Scrollbar(tab, orient=tk.VERTICAL, command=self._history_tree.yview)
        self._history_tree.configure(yscrollcommand=ys.set)
        ys.pack(side=tk.RIGHT, fill=tk.Y)
        self._history_tree.pack(fill=tk.BOTH, expand=False, pady=(0, 4))
        self._history_tree.bind("<<TreeviewSelect>>", self._on_history_select)

        btn_row = ttk.Frame(tab)
        btn_row.pack(fill=tk.X, pady=(0, 6))
        ttk.Button(
            btn_row,
            text="Load into Editor",
            command=self._on_load_from_history,
        ).pack(side=tk.LEFT)
        ttk.Button(
            btn_row,
            text="Delete Version",
            command=self._on_delete_version,
        ).pack(side=tk.LEFT, padx=6)

        ttk.Label(tab, text="Content Preview:").pack(anchor=tk.W)
        pf = ttk.Frame(tab)
        pf.pack(fill=tk.BOTH, expand=True)
        ps = ttk.Scrollbar(pf, orient=tk.VERTICAL)
        self._history_preview = tk.Text(
            pf,
            height=8,
            wrap=tk.WORD,
            state=tk.DISABLED,
            font=("Courier", 10),
            yscrollcommand=ps.set,
        )
        ps.config(command=self._history_preview.yview)
        ps.pack(side=tk.RIGHT, fill=tk.Y)
        self._history_preview.pack(fill=tk.BOTH, expand=True)

    def _build_render_tab(self) -> None:
        tab = ttk.Frame(self._notebook, padding=8)
        self._notebook.add(tab, text="Render")

        ttk.Label(
            tab, text="Variables (one per line, format:  name=value):"
        ).pack(anchor=tk.W)
        self._vars_text = tk.Text(tab, height=6, font=("Courier", 10))
        self._vars_text.pack(fill=tk.X, pady=(2, 6))

        ttk.Button(tab, text="Render", command=self._on_render).pack(anchor=tk.W)

        ttk.Label(tab, text="Result:").pack(anchor=tk.W, pady=(8, 0))
        rf = ttk.Frame(tab)
        rf.pack(fill=tk.BOTH, expand=True, pady=(2, 0))
        rs = ttk.Scrollbar(rf, orient=tk.VERTICAL)
        self._render_result = tk.Text(
            rf,
            wrap=tk.WORD,
            state=tk.DISABLED,
            font=("Courier", 11),
            yscrollcommand=rs.set,
        )
        rs.config(command=self._render_result.yview)
        rs.pack(side=tk.RIGHT, fill=tk.Y)
        self._render_result.pack(fill=tk.BOTH, expand=True)

    def _build_status_bar(self) -> None:
        self._status_var = tk.StringVar(value="Ready.")
        ttk.Label(
            self,
            textvariable=self._status_var,
            relief=tk.SUNKEN,
            anchor=tk.W,
            padding=(6, 2),
        ).pack(side=tk.BOTTOM, fill=tk.X)

    # ------------------------------------------------------------------ #
    # helpers                                                               #
    # ------------------------------------------------------------------ #

    def _set_status(self, msg: str) -> None:
        self._status_var.set(msg)

    def _refresh_key_list(self, highlight: Optional[str] = None) -> None:
        self._key_list.delete(0, tk.END)
        keys = sorted(self.vault.keys())
        for key in keys:
            self._key_list.insert(tk.END, key)
        if highlight and highlight in keys:
            idx = keys.index(highlight)
            self._key_list.selection_set(idx)
            self._key_list.see(idx)

    def _load_key(self, key: str) -> None:
        self._current_key = key
        self._key_label.config(text=key, foreground="black")
        tv = self.vault.get(key)
        if tv is None:
            return
        self._content_text.delete("1.0", tk.END)
        self._content_text.insert(tk.END, tv.content)
        self._tags_var.set(", ".join(tv.tags))
        self._refresh_history(key)

    def _refresh_history(self, key: str) -> None:
        for row in self._history_tree.get_children():
            self._history_tree.delete(row)
        for v in reversed(self.vault.history(key)):
            self._history_tree.insert(
                "",
                tk.END,
                iid=str(v.version),
                values=(v.version, v.saved_at, ", ".join(v.tags)),
            )

    def _get_selected_version(self) -> Optional[TemplateVersion]:
        sel = self._history_tree.selection()
        if not sel or self._current_key is None:
            return None
        return self.vault.get(self._current_key, int(sel[0]))

    def _clear_editor(self) -> None:
        self._current_key = None
        self._key_label.config(text="(none)", foreground="grey")
        self._content_text.delete("1.0", tk.END)
        self._tags_var.set("")
        for row in self._history_tree.get_children():
            self._history_tree.delete(row)
        self._history_preview.config(state=tk.NORMAL)
        self._history_preview.delete("1.0", tk.END)
        self._history_preview.config(state=tk.DISABLED)

    # ------------------------------------------------------------------ #
    # event handlers                                                        #
    # ------------------------------------------------------------------ #

    def _on_key_select(self, _event: object = None) -> None:
        sel = self._key_list.curselection()
        if not sel:
            return
        key = self._key_list.get(sel[0])
        self._load_key(key)
        self._set_status(f"Loaded '{key}'.")

    def _on_new(self) -> None:
        key = simpledialog.askstring("New Template", "Enter template key:", parent=self)
        if not key:
            return
        if key in self.vault:
            messagebox.showwarning(
                "Duplicate", f"Key '{key}' already exists.", parent=self
            )
            return
        self.vault.save(key, "")
        self._refresh_key_list(highlight=key)
        self._load_key(key)
        self._set_status(f"Created '{key}'.")

    def _on_save_version(self) -> None:
        if not self._current_key:
            messagebox.showinfo(
                "No Template", "Select or create a template first.", parent=self
            )
            return
        content = self._content_text.get("1.0", tk.END).rstrip("\n")
        raw_tags = self._tags_var.get()
        tags = [t.strip() for t in raw_tags.split(",") if t.strip()]
        tv = self.vault.save(self._current_key, content, tags=tags or None)
        self._refresh_history(self._current_key)
        self._set_status(f"Saved version {tv.version} of '{self._current_key}'.")

    def _on_rename(self) -> None:
        if not self._current_key:
            return
        new_key = simpledialog.askstring(
            "Rename", f"Rename '{self._current_key}' to:", parent=self
        )
        if not new_key or new_key == self._current_key:
            return
        if not self.vault.rename(self._current_key, new_key):
            messagebox.showwarning(
                "Conflict", f"Key '{new_key}' already exists.", parent=self
            )
            return
        old = self._current_key
        self._current_key = new_key
        self._key_label.config(text=new_key)
        self._refresh_key_list(highlight=new_key)
        self._set_status(f"Renamed '{old}' → '{new_key}'.")

    def _on_delete(self) -> None:
        if not self._current_key:
            return
        if not messagebox.askyesno(
            "Delete",
            f"Delete all versions of '{self._current_key}'?",
            parent=self,
        ):
            return
        self.vault.delete(self._current_key)
        self._clear_editor()
        self._refresh_key_list()
        self._set_status("Template deleted.")

    def _on_history_select(self, _event: object = None) -> None:
        tv = self._get_selected_version()
        if tv is None:
            return
        self._history_preview.config(state=tk.NORMAL)
        self._history_preview.delete("1.0", tk.END)
        self._history_preview.insert(tk.END, tv.content)
        self._history_preview.config(state=tk.DISABLED)

    def _on_load_from_history(self) -> None:
        tv = self._get_selected_version()
        if tv is None:
            return
        self._content_text.delete("1.0", tk.END)
        self._content_text.insert(tk.END, tv.content)
        self._tags_var.set(", ".join(tv.tags))
        self._notebook.select(0)
        self._set_status(f"Loaded version {tv.version} into editor.")

    def _on_delete_version(self) -> None:
        tv = self._get_selected_version()
        if tv is None:
            return
        if not messagebox.askyesno(
            "Delete Version",
            f"Delete version {tv.version} of '{self._current_key}'?",
            parent=self,
        ):
            return
        ver_num = tv.version
        self.vault.delete_version(self._current_key, ver_num)
        if self._current_key not in self.vault:
            self._clear_editor()
            self._refresh_key_list()
        else:
            latest = self.vault.get(self._current_key)
            assert latest is not None
            self._content_text.delete("1.0", tk.END)
            self._content_text.insert(tk.END, latest.content)
            self._tags_var.set(", ".join(latest.tags))
            self._refresh_history(self._current_key)
        self._set_status(f"Deleted version {ver_num}.")

    def _on_render(self) -> None:
        if not self._current_key:
            return
        kwargs: dict[str, str] = {}
        for line in self._vars_text.get("1.0", tk.END).strip().splitlines():
            if "=" in line:
                k, _, v = line.partition("=")
                kwargs[k.strip()] = v.strip()
        try:
            result = self.vault.render(self._current_key, **kwargs) or ""
        except Exception as exc:
            result = f"[Error] {exc}"
        self._render_result.config(state=tk.NORMAL)
        self._render_result.delete("1.0", tk.END)
        self._render_result.insert(tk.END, result)
        self._render_result.config(state=tk.DISABLED)

    def _on_search(self) -> None:
        query = self._search_var.get().strip()
        if not query:
            self._refresh_key_list(highlight=self._current_key)
            return
        results = self.vault.search(query)
        self._key_list.delete(0, tk.END)
        for key in sorted(results.keys()):
            self._key_list.insert(tk.END, key)
        self._set_status(
            f"Found {len(results)} template(s) matching '{query}'."
        )

    def _on_search_clear(self) -> None:
        self._search_var.set("")
        self._refresh_key_list(highlight=self._current_key)
        self._set_status("Search cleared.")

    def _on_export(self) -> None:
        path = filedialog.asksaveasfilename(
            parent=self,
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Export Vault",
        )
        if path:
            self.vault.export(path)
            self._set_status(f"Vault exported to {path}.")

    def _on_import(self) -> None:
        path = filedialog.askopenfilename(
            parent=self,
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Import Vault",
        )
        if not path:
            return
        try:
            self.vault.load(path)
        except Exception as exc:
            messagebox.showerror("Import Error", str(exc), parent=self)
            return
        self._refresh_key_list()
        self._set_status(f"Vault imported from {path}.")


def run() -> None:
    """Launch the PromptVault GUI."""
    app = PromptVaultApp()
    app.mainloop()
