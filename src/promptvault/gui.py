"""Streamlit GUI for PromptVault."""
from __future__ import annotations

from pathlib import Path

import jinja2
import streamlit as st

from promptvault import Promptvault

_DEFAULT_PATH = "promptvault.json"


# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------

def _get_vault() -> Promptvault:
    path = st.session_state.get("vault_path", _DEFAULT_PATH)
    if "vault" not in st.session_state or st.session_state.get("_loaded_path") != path:
        st.session_state["vault"] = Promptvault(storage_path=path)
        st.session_state["_loaded_path"] = path
    return st.session_state["vault"]


def _reset_vault() -> None:
    st.session_state.pop("vault", None)
    st.session_state.pop("_loaded_path", None)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

def _sidebar(vault: Promptvault) -> None:
    with st.sidebar:
        st.title("PromptVault")
        st.caption("Versioned LLM prompt storage")
        st.divider()

        new_path = st.text_input("Vault file", value=st.session_state.get("vault_path", _DEFAULT_PATH))
        if new_path != st.session_state.get("vault_path"):
            st.session_state["vault_path"] = new_path
            _reset_vault()
            st.rerun()

        path_obj = Path(st.session_state.get("vault_path", _DEFAULT_PATH))
        if path_obj.exists():
            st.caption(f"Loaded from `{path_obj}`")
        else:
            st.caption("(in-memory — file does not exist yet)")

        st.divider()
        keys = vault.keys()
        st.metric("Templates", len(keys))
        st.metric("Tags", len(vault.list_all_tags()))
        if keys:
            st.subheader("Templates")
            for k in keys:
                n = len(vault.history(k))
                st.write(f"• **{k}** &nbsp; `{n}v`")


# ---------------------------------------------------------------------------
# Tab: Templates
# ---------------------------------------------------------------------------

def _tab_templates(vault: Promptvault) -> None:
    st.header("Templates")
    keys = vault.keys()
    choice = st.selectbox("Select template", ["＋ New template"] + keys)

    is_new = choice == "＋ New template"

    left, right = st.columns([1, 2])

    with left:
        if is_new:
            key = st.text_input("Template name", placeholder="e.g. summarize")
        else:
            key = choice
            st.markdown(f"**Key:** `{key}`")
            tv = vault.get(key)
            st.caption(f"Latest: v{tv.version} — {tv.saved_at}")

    with right:
        existing_content = "" if is_new else vault.get(key).content
        existing_tags = [] if is_new else vault.get(key).tags

        content = st.text_area(
            "Content (Jinja2)",
            value=existing_content,
            height=220,
            placeholder="Hello, {{ name }}!\n{% if formal %}Regards{% else %}Cheers{% endif %}",
        )
        tags_raw = st.text_input(
            "Tags (comma-separated)",
            value=", ".join(existing_tags),
        )
        tags = [t.strip() for t in tags_raw.split(",") if t.strip()]

        col_save, col_del = st.columns([1, 1])
        with col_save:
            if st.button("Save", type="primary", use_container_width=True):
                if not (key and key.strip()):
                    st.error("Template name is required.")
                elif not content.strip():
                    st.error("Content is required.")
                else:
                    vault.save(key.strip(), content, tags=tags)
                    saved = vault.get(key.strip())
                    st.success(f"Saved as v{saved.version}.")
                    st.rerun()

        with col_del:
            if not is_new and st.button("Delete all", type="secondary", use_container_width=True):
                vault.delete(key)
                st.warning(f"Deleted `{key}`.")
                st.rerun()

    if not is_new:
        st.divider()
        st.subheader("Rename")
        new_name = st.text_input("New name", key="rename_input")
        if st.button("Rename"):
            if not new_name.strip():
                st.error("New name cannot be empty.")
            elif vault.rename(key, new_name.strip()):
                st.success(f"Renamed to `{new_name.strip()}`.")
                st.rerun()
            else:
                st.error("Rename failed — target name may already exist.")


# ---------------------------------------------------------------------------
# Tab: History
# ---------------------------------------------------------------------------

def _tab_history(vault: Promptvault) -> None:
    st.header("Version History")
    keys = vault.keys()
    if not keys:
        st.info("No templates stored yet.")
        return

    key = st.selectbox("Template", keys, key="history_key")
    history = vault.history(key)

    st.caption(f"{len(history)} version(s) for `{key}`")
    for tv in reversed(history):
        tag_str = f"  `[{', '.join(tv.tags)}]`" if tv.tags else ""
        with st.expander(f"v{tv.version} — {tv.saved_at}{tag_str}"):
            st.code(tv.content, language="django")
            if st.button(f"Delete v{tv.version}", key=f"dv_{key}_{tv.version}"):
                vault.delete_version(key, tv.version)
                st.rerun()


# ---------------------------------------------------------------------------
# Tab: Render
# ---------------------------------------------------------------------------

def _tab_render(vault: Promptvault) -> None:
    st.header("Render Template")
    keys = vault.keys()
    if not keys:
        st.info("No templates stored yet.")
        return

    key = st.selectbox("Template", keys, key="render_key")
    history = vault.history(key)
    version = st.selectbox(
        "Version",
        [v.version for v in history],
        index=len(history) - 1,
        key="render_version",
    )
    tv = vault.get(key, version)

    st.subheader("Template")
    st.code(tv.content, language="django")

    env = jinja2.Environment()
    try:
        ast = env.parse(tv.content)
        variables = sorted(jinja2.meta.find_undeclared_variables(ast))
    except jinja2.exceptions.TemplateSyntaxError:
        variables = []

    kwargs: dict = {}
    if variables:
        st.subheader("Variables")
        cols = st.columns(min(len(variables), 3))
        for i, var in enumerate(variables):
            with cols[i % len(cols)]:
                kwargs[var] = st.text_input(var, key=f"rv_{var}")
    else:
        st.caption("No undeclared variables detected.")

    if st.button("Render", type="primary"):
        try:
            result = tv.render(**kwargs)
            st.subheader("Output")
            st.text_area("Rendered output", value=result, height=180, disabled=True)
        except jinja2.exceptions.TemplateError as exc:
            st.error(f"Jinja2 error: {exc}")


# ---------------------------------------------------------------------------
# Tab: Search
# ---------------------------------------------------------------------------

def _tab_search(vault: Promptvault) -> None:
    st.header("Search")

    query = st.text_input("Search content", placeholder="{{ name }}")
    case_sensitive = st.checkbox("Case-sensitive")
    all_tags = vault.list_all_tags()
    selected_tags = st.multiselect("Filter by tags", all_tags)

    if query:
        results = vault.search(query, case_sensitive=case_sensitive)
        if results:
            st.subheader(f"Content matches — {len(results)} template(s)")
            for k, versions in results.items():
                with st.expander(f"**{k}** ({len(versions)} version(s))"):
                    for v in versions:
                        st.markdown(f"**v{v.version}**")
                        st.code(v.content, language="django")
        else:
            st.info("No content matches.")

    if selected_tags:
        tag_results = vault.search_by_tags(selected_tags)
        if tag_results:
            st.subheader(f"Tag matches — {len(tag_results)} template(s)")
            for k, versions in tag_results.items():
                with st.expander(f"**{k}**"):
                    for v in versions:
                        tag_str = ", ".join(v.tags)
                        st.markdown(f"**v{v.version}** `[{tag_str}]`")
                        st.code(v.content, language="django")
        else:
            st.info("No tag matches.")


# ---------------------------------------------------------------------------
# Tab: Settings
# ---------------------------------------------------------------------------

def _tab_settings(vault: Promptvault) -> None:
    st.header("Settings & Import / Export")

    st.subheader("Export")
    export_path = st.text_input("Export path", "export.json", key="export_path")
    if st.button("Export all templates"):
        try:
            vault.export(export_path)
            st.success(f"Exported to `{export_path}`.")
        except Exception as exc:
            st.error(str(exc))

    st.divider()
    st.subheader("Import")
    import_path = st.text_input("Import path", "import.json", key="import_path")
    overwrite = st.checkbox("Overwrite existing templates")
    if st.button("Import"):
        try:
            n = vault.import_from(import_path, overwrite=overwrite)
            st.success(f"Imported {n} template(s).")
            _reset_vault()
            st.rerun()
        except FileNotFoundError:
            st.error(f"File not found: `{import_path}`")
        except Exception as exc:
            st.error(str(exc))

    st.divider()
    st.subheader("Statistics")
    keys = vault.keys()
    total_versions = sum(len(vault.history(k)) for k in keys)
    c1, c2, c3 = st.columns(3)
    c1.metric("Templates", len(keys))
    c2.metric("Total versions", total_versions)
    c3.metric("Unique tags", len(vault.list_all_tags()))


# ---------------------------------------------------------------------------
# Main entry
# ---------------------------------------------------------------------------

def main() -> None:
    st.set_page_config(
        page_title="PromptVault",
        page_icon="🗄️",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    vault = _get_vault()
    _sidebar(vault)

    tabs = st.tabs(["Templates", "History", "Render", "Search", "Settings"])
    with tabs[0]:
        _tab_templates(vault)
    with tabs[1]:
        _tab_history(vault)
    with tabs[2]:
        _tab_render(vault)
    with tabs[3]:
        _tab_search(vault)
    with tabs[4]:
        _tab_settings(vault)


if __name__ == "__main__":
    main()
