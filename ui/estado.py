"""
Estado da sessão: a molécula aberta, o histórico, o modo de uso e o link compartilhável.

Uma única fonte de verdade: st.session_state.molecula = {"smiles", "nome", "origem"}.
Todas as partes da interface leem daqui e mudam a molécula só por definir_molecula().
"""

from __future__ import annotations

from urllib.parse import urlencode, urlsplit, urlunsplit

import streamlit as st
from rdkit import Chem

from chemio_tools import TIPOS_ATIVIDADE, validar_smiles

MODOS = {"explorar": "🔎 Explorar", "aula": "📽️ Aula", "atividade": "✏️ Atividade"}
ABAS = ["Estrutura", "Propriedades", "Estereoquímica", "Comparar", "Exportar"]  # "Alertas" entra se houver
LIMITE_HISTORICO = 8

EXEMPLOS = [
    ("Ácido láctico", "CC(O)C(=O)O"),
    ("Ácido acetilsalicílico", "CC(=O)Oc1ccccc1C(=O)O"),
    ("Etanol", "CCO"),
    ("But-2-eno", "CC=CC"),
    ("Benzeno", "c1ccccc1"),
    ("Glicose (cadeia aberta)", "O=C[C@H](O)[C@@H](O)[C@H](O)[C@H](O)CO"),
]


def inicializar():
    padroes = {
        "molecula": None,          # {"smiles", "nome", "origem"}
        "historico": [],           # [{"smiles", "nome"}], mais recente primeiro
        "modo": "explorar",
        "tecnico": False,
        "resultado_busca": None,
        "aba_inicial": None,
        "atividade_tipo": "quirais",
        "link_lido": False,
    }
    for chave, valor in padroes.items():
        if chave not in st.session_state:
            st.session_state[chave] = valor


def molecula() -> dict | None:
    return st.session_state.get("molecula")


def _canonico(smiles: str) -> str:
    return Chem.MolToSmiles(Chem.MolFromSmiles(smiles))


def definir_molecula(smiles: str, nome: str = "", origem: str = "") -> bool:
    """Abre uma molécula (valida o SMILES), guarda no histórico e limpa o que dependia da anterior."""
    smiles = (smiles or "").strip()
    if not validar_smiles(smiles):
        return False
    atual = molecula()
    if atual and atual["smiles"] == smiles and (nome or "") == (atual.get("nome") or ""):
        return True
    st.session_state.molecula = {"smiles": smiles, "nome": nome or "", "origem": origem}
    canon = _canonico(smiles)
    historico = [h for h in st.session_state.historico if _canonico(h["smiles"]) != canon]
    st.session_state.historico = ([{"smiles": smiles, "nome": nome or ""}] + historico)[:LIMITE_HISTORICO]
    # Estados que valiam só para a molécula anterior
    for chave in ("grupo_ativo", "atividade", "correcao", "comparar_b"):
        st.session_state.pop(chave, None)
    return True


def espelhar_widget(chave_widget: str, chave_valor: str):
    """Antes de desenhar o widget, copia o valor guardado para a chave do widget."""
    st.session_state[chave_widget] = st.session_state[chave_valor]


def copiar_widget(chave_widget: str, chave_valor: str):
    """Callback do widget: guarda o valor escolhido na chave que não é apagada."""
    st.session_state[chave_valor] = st.session_state[chave_widget]


def definir_modo(modo: str):
    if modo in MODOS:
        st.session_state.modo = modo


# ------------------------------------------------------------------ link compartilhável


def ler_link():
    """Aplica uma vez por sessão os parâmetros do endereço (?smiles=...&modo=...&aba=...&atividade=...)."""
    if st.session_state.link_lido:
        return
    st.session_state.link_lido = True
    p = st.query_params
    if p.get("smiles"):
        definir_molecula(p["smiles"], p.get("nome", ""), origem="link")
    if p.get("modo") in MODOS:
        st.session_state.modo = p["modo"]
    if p.get("aba") in ABAS + ["Alertas"]:
        st.session_state.aba_inicial = p["aba"]
    if p.get("atividade") in TIPOS_ATIVIDADE:
        st.session_state.atividade_tipo = p["atividade"]
    if p.get("tecnico") == "1":
        st.session_state.tecnico = True


def montar_link(modo: str, aba: str | None = None, atividade: str | None = None) -> str | None:
    """Endereço desta página com a molécula e o modo escolhidos (para copiar ou virar QR code)."""
    m = molecula()
    if not m:
        return None
    parametros = {"smiles": m["smiles"]}
    if m.get("nome"):
        parametros["nome"] = m["nome"]
    parametros["modo"] = modo
    if modo == "explorar" and aba:
        parametros["aba"] = aba
    if modo == "atividade" and atividade:
        parametros["atividade"] = atividade
    base = st.context.url or "http://localhost:8501/"
    partes = urlsplit(base)
    return urlunsplit((partes.scheme, partes.netloc, partes.path, urlencode(parametros), ""))
