"""Streamlit web app for Pick Counter."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import streamlit as st

from src import counter_picks
from src.config import COLOR_ORDER, CONSOLE_NAMES


def _counter_picks_from_bytes(data: bytes, filename: str) -> dict:
    """Run counter_picks on uploaded bytes by writing to a temp file."""
    suffix = Path(filename).suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png"}:
        suffix = ".jpg"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
        f.write(data)
        tmp_path = Path(f.name)
    try:
        return counter_picks(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)


def _format_result(result: dict) -> str:
    """Format result dict as human-readable Spanish text."""
    lines = [f"Número de púas: {result['n_picks']}"]
    for color in COLOR_ORDER:
        count = result.get("colors", {}).get(color)
        if count:
            lines.append(f"{CONSOLE_NAMES[color]}: {count}")
    return "\n".join(lines)


def _merge_results(results: list[dict]) -> dict:
    """Merge multiple result dicts into one with summed counts."""
    merged_colors: dict[str, int] = {c: 0 for c in COLOR_ORDER}
    total = 0
    for r in results:
        total += r["n_picks"]
        for color, count in r.get("colors", {}).items():
            merged_colors[color] = merged_colors.get(color, 0) + count
    ordered = {c: merged_colors[c] for c in COLOR_ORDER if merged_colors[c] > 0}
    return {"n_picks": total, "colors": ordered}


def _render_info_tab() -> None:
    """Render the usage/info tab."""
    st.markdown("## Contador de púas")
    st.markdown(
        """
        Esta aplicación cuenta **púas de guitarra** en imágenes que subas.

        ### Cómo usar
        1. Ve a la pestaña **Analizar imágenes**.
        2. Sube una o varias fotos (JPG, JPEG o PNG).
        3. Espera a que se procese cada imagen.
        4. Revisa el resultado por imagen y el total global.
        5. Usa el botón **Descargar resultado** para guardar el JSON.

        ### Formatos soportados
        - JPEG (.jpg, .jpeg)
        - PNG (.png)

        ### Colores detectados
        El contador clasifica las púas por color aproximado: negra, gris, blanca,
        marrón, roja, naranja, amarilla, verde, cian, azul, morada, rosa.
        """
    )


def _render_analyze_tab() -> None:
    """Render the upload and analysis tab."""
    st.markdown("## Analizar imágenes")

    uploaded = st.file_uploader(
        "Sube una o varias fotos",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True,
    )

    if not uploaded:
        st.info("Sube al menos una imagen para comenzar.")
        return

    results: list[tuple[str, dict]] = []
    errors: list[tuple[str, str]] = []

    for f in uploaded:
        with st.spinner(f"Analizando {f.name}..."):
            try:
                data = f.read()
                result = _counter_picks_from_bytes(data, f.name)
                results.append((f.name, result))
            except Exception as e:
                errors.append((f.name, str(e)))

    for name, err in errors:
        st.error(f"Error en **{name}**: {err}")

    if not results:
        return

    st.markdown("---")
    st.markdown("### Resultados por imagen")

    for name, result in results:
        with st.expander(f"📷 {name} — {result['n_picks']} púas"):
            st.text(_format_result(result))

    st.markdown("---")
    st.markdown("### Resultado global")

    merged = _merge_results([r for _, r in results])
    st.markdown(f"**Total de púas: {merged['n_picks']}**")
    st.text(_format_result(merged))

    json_str = json.dumps(merged, indent=4, ensure_ascii=False)
    st.download_button(
        "Descargar resultado (JSON)",
        data=json_str,
        file_name="resultado_puas.json",
        mime="application/json",
    )


def main() -> None:
    """Entry point for the Streamlit app."""
    st.set_page_config(
        page_title="Pick Counter",
        page_icon="🎸",
        layout="wide",
    )

    tab_info, tab_analyze = st.tabs(["Información", "Analizar imágenes"])

    with tab_info:
        _render_info_tab()

    with tab_analyze:
        _render_analyze_tab()


if __name__ == "__main__":
    main()
