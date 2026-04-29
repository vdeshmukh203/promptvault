"""Tkinter desktop GUI for Promptvault."""
from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Optional

from .vault import Promptvault, TemplateVersion


class VaultGUI:
    """Main application window."""

    def __init__(self, root: tk.Tk, vault_path: Optional[str] = None) -> None:
        self.root = root
        self.root.title("Promptvault")
        self.root.geometry("1150x740")
        self.root.minsize(820, 520)

        self._vault = Promptvault(path=vault_path)
        self._vault_path = vault_path
        self._selected_key: Optional[str] = None
        self._selected_version: Optional[TemplateVersion] = None

        self._build_menu()
        self._build_ui()
        self._refresh_keys()

    # ------------------------------------------------------------------ #
    # Menu
    # ------------------------------------------------------------------ #

    def _build_menu(self) -> None:
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=False)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New Vault…", command=self._new_vault)
        file_menu.add_command(label="Open Vault…", command=self._open_vault)
        file_menu.add_command(label="Save Vault", command=self._cmd_save_vault, accelerator="Ctrl+S")
        file_menu.add_separator()
        file_menu.add_command(label="Export JSON…", command=self._export_json)
        file_menu.add_command(label="Import JSON…", command=self._import_json)
        file_menu.add_separator()
        file_menu.add_command(label="Quit", command=self.root.destroy, accelerator="Ctrl+Q")

        self.root.bind_all("<Control-s>", lambda _e: self._cmd_save_vault())
        self.root.bind_all("<Control-q>", lambda _e: self.root.destroy())

    # ------------------------------------------------------------------ #
    # Layout
    # ------------------------------------------------------------------ #

    def _build_ui(self) -> None:
        # ── Status bar (bottom, packed first so it stays put) ──────────
        status_bar = ttk.Frame(self.root, relief=tk.SUNKEN)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self._status_var = tk.StringVar(value="Ready")
        ttk.Label(status_bar, textvariable=self._status_var, anchor="w", padding=(4, 1)).pack(
            fill=tk.X
        )

        # ── Top-level horizontal pane: key list | main area ────────────
        outer = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        outer.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        outer.add(self._build_keys_panel(outer), weight=1)
        outer.add(self._build_main_area(outer), weight=5)

    # ── Keys panel ─────────────────────────────────────────────────────

    def _build_keys_panel(self, parent) -> ttk.Frame:
        frame = ttk.Frame(parent)

        ttk.Label(frame, text="Templates", font=("", 10, "bold")).pack(
            anchor="w", padx=6, pady=(6, 0)
        )

        # Search
        search_row = ttk.Frame(frame)
        search_row.pack(fill=tk.X, padx=6, pady=(3, 0))
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._refresh_keys())
        ttk.Entry(search_row, textvariable=self._search_var).pack(
            side=tk.LEFT, fill=tk.X, expand=True
        )
        ttk.Button(search_row, text="✕", width=2,
                   command=lambda: self._search_var.set("")).pack(side=tk.LEFT)

        # Tag filter
        tag_row = ttk.Frame(frame)
        tag_row.pack(fill=tk.X, padx=6, pady=(2, 0))
        ttk.Label(tag_row, text="Tag filter:").pack(side=tk.LEFT)
        self._tag_filter_var = tk.StringVar()
        self._tag_filter_var.trace_add("write", lambda *_: self._refresh_keys())
        ttk.Entry(tag_row, textvariable=self._tag_filter_var).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 0)
        )

        # Listbox
        lb_frame = ttk.Frame(frame)
        lb_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)
        self._key_lb = tk.Listbox(lb_frame, selectmode=tk.SINGLE, exportselection=False)
        sb = ttk.Scrollbar(lb_frame, command=self._key_lb.yview)
        self._key_lb.config(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self._key_lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._key_lb.bind("<<ListboxSelect>>", self._on_key_select)

        # Buttons
        btn_row = ttk.Frame(frame)
        btn_row.pack(fill=tk.X, padx=6, pady=(0, 6))
        ttk.Button(btn_row, text="New", command=self._new_template).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Button(btn_row, text="Rename", command=self._rename_template).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Button(btn_row, text="Delete", command=self._delete_template).pack(
            side=tk.LEFT, padx=2
        )

        return frame

    # ── Main area ──────────────────────────────────────────────────────

    def _build_main_area(self, parent) -> ttk.PanedWindow:
        main = ttk.PanedWindow(parent, orient=tk.VERTICAL)

        main.add(self._build_editor_pane(main), weight=3)
        main.add(self._build_render_pane(main), weight=2)

        return main

    def _build_editor_pane(self, parent) -> ttk.PanedWindow:
        pane = ttk.PanedWindow(parent, orient=tk.HORIZONTAL)

        # ── Version list ───────────────────────────────────────────────
        ver_frame = ttk.Frame(pane)
        pane.add(ver_frame, weight=1)

        ttk.Label(ver_frame, text="Versions", font=("", 10, "bold")).pack(
            anchor="w", padx=6, pady=(6, 0)
        )
        lb_f = ttk.Frame(ver_frame)
        lb_f.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)
        self._ver_lb = tk.Listbox(lb_f, selectmode=tk.SINGLE, exportselection=False)
        vsb = ttk.Scrollbar(lb_f, command=self._ver_lb.yview)
        self._ver_lb.config(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self._ver_lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._ver_lb.bind("<<ListboxSelect>>", self._on_version_select)
        ttk.Button(ver_frame, text="Delete Version",
                   command=self._delete_version).pack(fill=tk.X, padx=6, pady=(0, 6))

        # ── Editor ─────────────────────────────────────────────────────
        editor_frame = ttk.Frame(pane)
        pane.add(editor_frame, weight=3)

        ttk.Label(editor_frame, text="Editor", font=("", 10, "bold")).pack(
            anchor="w", padx=6, pady=(6, 0)
        )
        self._editor = tk.Text(editor_frame, wrap=tk.WORD, undo=True, font=("Courier", 11))
        esb = ttk.Scrollbar(editor_frame, command=self._editor.yview)
        self._editor.config(yscrollcommand=esb.set)
        esb.pack(side=tk.RIGHT, fill=tk.Y, pady=4)
        self._editor.pack(fill=tk.BOTH, expand=True, padx=(6, 0), pady=4)

        # Tags + save
        bottom = ttk.Frame(editor_frame)
        bottom.pack(fill=tk.X, padx=6, pady=(0, 6))
        ttk.Label(bottom, text="Tags (comma-separated):").pack(side=tk.LEFT)
        self._tags_var = tk.StringVar()
        ttk.Entry(bottom, textvariable=self._tags_var).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=6
        )
        ttk.Button(bottom, text="Save New Version",
                   command=self._save_version).pack(side=tk.LEFT)

        return pane

    def _build_render_pane(self, parent) -> ttk.LabelFrame:
        render_frame = ttk.LabelFrame(parent, text="Render")

        vars_row = ttk.Frame(render_frame)
        vars_row.pack(fill=tk.X, padx=6, pady=6)
        ttk.Label(vars_row, text="Variables (key=value, …):").pack(side=tk.LEFT)
        self._vars_var = tk.StringVar()
        ttk.Entry(vars_row, textvariable=self._vars_var).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=6
        )
        ttk.Button(vars_row, text="Render", command=self._do_render).pack(side=tk.LEFT)
        self.root.bind_all("<Control-Return>", lambda _e: self._do_render())

        self._render_out = tk.Text(
            render_frame, wrap=tk.WORD, state=tk.DISABLED,
            font=("Courier", 11), bg="#f5f5f5", height=7,
        )
        rsb = ttk.Scrollbar(render_frame, command=self._render_out.yview)
        self._render_out.config(yscrollcommand=rsb.set)
        rsb.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 6), pady=(0, 6))
        self._render_out.pack(fill=tk.BOTH, expand=True, padx=(6, 0), pady=(0, 6))

        return render_frame

    # ------------------------------------------------------------------ #
    # Key helpers
    # ------------------------------------------------------------------ #

    def _visible_keys(self) -> list[str]:
        text_q = self._search_var.get().strip()
        tag_q = [t.strip() for t in self._tag_filter_var.get().split(",") if t.strip()]

        keys = set(self._vault.keys())

        if text_q:
            keys &= set(self._vault.search(text_q).keys())

        if tag_q:
            keys &= set(self._vault.search_by_tags(*tag_q).keys())

        return sorted(keys)

    def _refresh_keys(self, select_key: Optional[str] = None) -> None:
        keys = self._visible_keys()
        self._key_lb.delete(0, tk.END)
        for k in keys:
            self._key_lb.insert(tk.END, k)

        target = select_key or self._selected_key
        if target in keys:
            idx = keys.index(target)
            self._key_lb.selection_set(idx)
            self._key_lb.see(idx)
            if target != self._selected_key:
                self._selected_key = target
                self._refresh_versions()
        elif not keys:
            self._selected_key = None
            self._refresh_versions()

    def _on_key_select(self, _event=None) -> None:
        sel = self._key_lb.curselection()
        if not sel:
            return
        key = self._key_lb.get(sel[0])
        if key == self._selected_key:
            return
        self._selected_key = key
        self._refresh_versions()

    def _new_template(self) -> None:
        key = simpledialog.askstring("New Template", "Template name:", parent=self.root)
        if not key or not key.strip():
            return
        key = key.strip()
        if key in self._vault.keys():
            messagebox.showerror("Error", f"'{key}' already exists.", parent=self.root)
            return
        self._selected_key = key
        self._selected_version = None
        self._ver_lb.delete(0, tk.END)
        self._editor.delete("1.0", tk.END)
        self._tags_var.set("")
        self._status(f"New template '{key}' — write content and save a version.")

    def _rename_template(self) -> None:
        if not self._selected_key:
            return
        new_key = simpledialog.askstring(
            "Rename", f"Rename '{self._selected_key}' to:", parent=self.root
        )
        if not new_key or not new_key.strip():
            return
        new_key = new_key.strip()
        if self._vault.rename(self._selected_key, new_key):
            old = self._selected_key
            self._selected_key = new_key
            self._refresh_keys(select_key=new_key)
            self._status(f"Renamed '{old}' → '{new_key}'.")
        else:
            messagebox.showerror("Error", f"Cannot rename to '{new_key}'.", parent=self.root)

    def _delete_template(self) -> None:
        if not self._selected_key:
            return
        if not messagebox.askyesno(
            "Delete", f"Delete all versions of '{self._selected_key}'?", parent=self.root
        ):
            return
        key = self._selected_key
        self._vault.delete(key)
        self._selected_key = None
        self._selected_version = None
        self._refresh_keys()
        self._refresh_versions()
        self._editor.delete("1.0", tk.END)
        self._status(f"Deleted '{key}'.")

    # ------------------------------------------------------------------ #
    # Version helpers
    # ------------------------------------------------------------------ #

    def _refresh_versions(self) -> None:
        self._ver_lb.delete(0, tk.END)
        if not self._selected_key:
            self._selected_version = None
            return
        versions = self._vault.history(self._selected_key)
        for v in reversed(versions):
            label = f"v{v.version}  {v.saved_at[:19].replace('T', ' ')}"
            if v.tags:
                label += f"  [{', '.join(v.tags)}]"
            self._ver_lb.insert(tk.END, label)
        if versions:
            self._ver_lb.selection_set(0)
            self._load_into_editor(versions[-1])
        else:
            self._selected_version = None
            self._editor.delete("1.0", tk.END)
            self._tags_var.set("")

    def _on_version_select(self, _event=None) -> None:
        sel = self._ver_lb.curselection()
        if not sel or not self._selected_key:
            return
        versions = self._vault.history(self._selected_key)
        # Listbox is newest-first; reverse the index.
        idx = len(versions) - 1 - sel[0]
        self._load_into_editor(versions[idx])

    def _load_into_editor(self, tv: TemplateVersion) -> None:
        self._selected_version = tv
        self._editor.delete("1.0", tk.END)
        self._editor.insert("1.0", tv.content)
        self._tags_var.set(", ".join(tv.tags))

    def _save_version(self) -> None:
        if not self._selected_key:
            messagebox.showwarning(
                "No template", "Select or create a template first.", parent=self.root
            )
            return
        content = self._editor.get("1.0", tk.END).rstrip("\n")
        raw_tags = self._tags_var.get().strip()
        tags = [t.strip() for t in raw_tags.split(",") if t.strip()] if raw_tags else []
        self._vault.save(self._selected_key, content, tags=tags)
        self._refresh_keys(select_key=self._selected_key)
        self._refresh_versions()
        self._status(f"Saved new version of '{self._selected_key}'.")

    def _delete_version(self) -> None:
        if not self._selected_version or not self._selected_key:
            return
        ver = self._selected_version.version
        if not messagebox.askyesno("Delete Version", f"Delete v{ver}?", parent=self.root):
            return
        self._vault.delete_version(self._selected_key, ver)
        self._selected_version = None
        if self._selected_key not in self._vault.keys():
            self._selected_key = None
        self._refresh_keys(select_key=self._selected_key)
        self._refresh_versions()
        self._status(f"Deleted version {ver}.")

    # ------------------------------------------------------------------ #
    # Render
    # ------------------------------------------------------------------ #

    def _do_render(self) -> None:
        if not self._selected_key:
            return
        raw = self._vars_var.get().strip()
        kwargs: dict = {}
        if raw:
            for pair in raw.split(","):
                pair = pair.strip()
                if "=" in pair:
                    k, _, val = pair.partition("=")
                    kwargs[k.strip()] = val.strip()
        ver = self._selected_version.version if self._selected_version else None
        try:
            result = self._vault.render(self._selected_key, version=ver, **kwargs)
            if result is None:
                result = "(template not found)"
        except Exception as exc:
            result = f"Error: {exc}"
        self._render_out.config(state=tk.NORMAL)
        self._render_out.delete("1.0", tk.END)
        self._render_out.insert("1.0", result)
        self._render_out.config(state=tk.DISABLED)

    # ------------------------------------------------------------------ #
    # File operations
    # ------------------------------------------------------------------ #

    def _new_vault(self) -> None:
        path = filedialog.asksaveasfilename(
            title="New Vault File",
            defaultextension=".json",
            filetypes=[("JSON", "*.json"), ("All files", "*")],
            parent=self.root,
        )
        if not path:
            return
        self._vault = Promptvault(path=path)
        self._vault_path = path
        self._selected_key = None
        self._selected_version = None
        self._refresh_keys()
        self.root.title(f"Promptvault — {Path(path).name}")
        self._status(f"New vault: {path}")

    def _open_vault(self) -> None:
        path = filedialog.askopenfilename(
            title="Open Vault",
            filetypes=[("JSON", "*.json"), ("All files", "*")],
            parent=self.root,
        )
        if not path:
            return
        self._vault = Promptvault(path=path)
        self._vault_path = path
        self._selected_key = None
        self._selected_version = None
        self._refresh_keys()
        self.root.title(f"Promptvault — {Path(path).name}")
        self._status(f"Opened: {path}")

    def _cmd_save_vault(self) -> None:
        if self._vault_path is None:
            path = filedialog.asksaveasfilename(
                title="Save Vault As",
                defaultextension=".json",
                filetypes=[("JSON", "*.json"), ("All files", "*")],
                parent=self.root,
            )
            if not path:
                return
            self._vault._path = Path(path)
            self._vault_path = path
            self.root.title(f"Promptvault — {Path(path).name}")
        self._vault.save_to_disk()
        self._status("Vault saved.")

    def _export_json(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Export JSON",
            defaultextension=".json",
            filetypes=[("JSON", "*.json"), ("All files", "*")],
            parent=self.root,
        )
        if not path:
            return
        Path(path).write_text(self._vault.export_json(), encoding="utf-8")
        self._status(f"Exported to {path}.")

    def _import_json(self) -> None:
        path = filedialog.askopenfilename(
            title="Import JSON",
            filetypes=[("JSON", "*.json"), ("All files", "*")],
            parent=self.root,
        )
        if not path:
            return
        imported = Promptvault.import_json(Path(path).read_text(encoding="utf-8"))
        for key in imported.keys():
            for tv in imported.history(key):
                self._vault._store.setdefault(key, []).append(tv)
        if self._vault_path:
            self._vault.save_to_disk()
        self._refresh_keys()
        self._status(f"Imported from {path}.")

    # ------------------------------------------------------------------ #
    # Status bar
    # ------------------------------------------------------------------ #

    def _status(self, msg: str) -> None:
        self._status_var.set(msg)


def main() -> None:
    vault_path = sys.argv[1] if len(sys.argv) > 1 else None
    root = tk.Tk()
    app = VaultGUI(root, vault_path=vault_path)  # noqa: F841
    root.mainloop()


if __name__ == "__main__":
    main()
