"""
Visual comum: CSS do cartão fixo e do Modo Aula, e mensagens padronizadas
(tela vazia, erro, aviso, carregando).
"""

from __future__ import annotations

import streamlit as st

# Mesmas cores de .streamlit/config.toml
FUNDO = {"light": "#FFFFFF", "dark": "#0F172A"}
BORDA = {"light": "#CBD5E1", "dark": "#334155"}

TEXTO_CARREGANDO = "Calculando…"
ESCALA_ROTULOS = 0.8  # rótulos C1, C2..., R/S e sp³ maiores que o padrão do RDKit (0,5)
_SUB = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")


def formula_bonita(formula: str) -> str:
    """C9H8O4 -> C₉H₈O₄."""
    return formula.translate(_SUB)


def num(valor, casas: int = 2) -> str:
    """Número no formato brasileiro (vírgula decimal)."""
    if isinstance(valor, int):
        return str(valor)
    return f"{valor:.{casas}f}".replace(".", ",")


def fundo_escuro_padrao() -> bool:
    """Desenhos com fundo escuro quando o app está no tema escuro."""
    return _tema() == "dark"


def _tema() -> str:
    try:
        return st.context.theme.type or "light"
    except Exception:
        return "light"


def aplicar_css(modo: str):
    tema = _tema()
    css = f"""
    <style>
    /* Cartão da molécula: fica no topo ao rolar a página */
    .st-key-cartao {{
        position: sticky; top: 3.75rem; z-index: 50;
        background: {FUNDO[tema]};
        border-bottom: 1px solid {BORDA[tema]};
        padding: 0.5rem 0 0.25rem 0;
    }}
    .st-key-cartao h3 {{ margin: 0; padding: 0; }}
    """
    if modo == "aula":
        css += """
    /* Modo Aula: sem barra lateral e com letra grande para projeção */
    [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] { display: none; }
    .block-container { padding-top: 2.5rem; max-width: 100%; }
    .stApp [data-testid="stMarkdownContainer"] p,
    .stApp [data-testid="stMarkdownContainer"] li { font-size: 1.45rem; line-height: 1.5; }
    .stApp [data-testid="stCaptionContainer"] { font-size: 1.15rem; }
    .stApp h1 { font-size: 2.6rem; }
    .stApp h2 { font-size: 2.1rem; }
    .stApp [data-testid="stMetricValue"] { font-size: 2.4rem; }
    .stApp button p { font-size: 1.2rem; }
    """
    css += "</style>"
    st.html(css)


def tela_vazia(titulo: str, texto: str, icone: str = "🧪"):
    with st.container(border=True):
        st.markdown(f"### {icone} {titulo}")
        st.markdown(texto)


def erro(texto: str, dica: str | None = None):
    st.error(texto, icon="🚫")
    if dica:
        st.caption(dica)


def aviso(texto: str):
    st.warning(texto, icon="⚠️")


def cabecalho(titulo: str, explicacao: list[str] | str | None = None):
    """Título de seção com o botão "Por quê?" ao lado (sem espremer o botão)."""
    with st.container(horizontal=True, vertical_alignment="center", gap="small"):
        st.markdown(f"#### {titulo}", width="content")
        if explicacao:
            por_que(explicacao)


def por_que(textos: list[str] | str, rotulo: str = "Por quê?"):
    """Botão que abre a explicação de um resultado."""
    if isinstance(textos, str):
        textos = [textos]
    with st.popover(rotulo, icon="💡"):
        for t in textos:
            st.markdown(t)
