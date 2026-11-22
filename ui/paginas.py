"""Páginas do app: Molécula (com os modos Explorar, Aula e Atividade) e Isomeria."""

import streamlit as st

from chemio_tools import buscar_alertas_estruturais

from .cartao import renderizar_cartao
from .estado import ABAS, EXEMPLOS, definir_molecula, molecula
from .inputs import renderizar_busca
from .modo_atividade import _sortear_molecula, renderizar_modo_atividade
from .modo_aula import renderizar_modo_aula
from .tab_comparar import renderizar_aba_comparar
from .tab_estereoquimica import renderizar_aba_estereoquimica
from .tab_exportes import renderizar_aba_exportacao
from .tab_isomeria import renderizar_aba_isomeria
from .tab_properties import renderizar_aba_propriedades
from .tab_seguranca import renderizar_aba_seguranca
from .tab_visualization import renderizar_aba_visualizacao

ROTULO_ALERTAS = "⚠️ Alertas"


def _boas_vindas():
    st.markdown("# 🧪 ChemioKit")
    st.markdown("Ferramenta de química para explorar moléculas em 2D e 3D, estereoquímica, propriedades e isomeria.")
    with st.container(border=True):
        st.markdown("#### Para começar")
        renderizar_busca(destaque=True)
        st.markdown("**Ou experimente:**")
        cols = st.columns(3)
        for i, (nome, smiles) in enumerate(EXEMPLOS):
            cols[i % 3].button(nome, key=f"bv_{i}", on_click=definir_molecula, args=(smiles, nome, "exemplo"), width="stretch")
    c1, c2, c3 = st.columns(3)
    with c1.container(border=True):
        st.markdown("**🔎 Explorar**")
        st.caption("Estrutura, propriedades, estereoquímica, comparação e exportação, com explicações em cada resultado.")
    with c2.container(border=True):
        st.markdown("**📽️ Aula**")
        st.caption("Para projetar: estrutura grande, letra grande e comparação lado a lado.")
    with c3.container(border=True):
        st.markdown("**✏️ Atividade**")
        st.caption("O estudante responde e o ChemioKit confere e explica. Nada é gravado.")
    if st.session_state.modo == "atividade":
        st.button("🎲 Começar a atividade com uma molécula sorteada", on_click=_sortear_molecula, type="primary")


def pagina_molecula():
    m = molecula()
    if not m:
        _boas_vindas()
        return
    smiles = m["smiles"]
    modo = st.session_state.modo
    if modo == "aula":
        renderizar_modo_aula(smiles)
        return
    if modo == "atividade":
        renderizar_modo_atividade(smiles)
        return

    renderizar_busca()
    renderizar_cartao()
    alertas = buscar_alertas_estruturais(smiles)
    nomes = ABAS[:3] + ([ROTULO_ALERTAS] if alertas["total"] else []) + ABAS[3:]
    inicial = st.session_state.pop("aba_inicial", None)
    inicial = ROTULO_ALERTAS if inicial == "Alertas" else inicial
    abas = dict(zip(nomes, st.tabs(nomes, default=inicial if inicial in nomes else None)))

    with abas["Estrutura"]:
        renderizar_aba_visualizacao(smiles)
    with abas["Propriedades"]:
        renderizar_aba_propriedades(smiles)
    with abas["Estereoquímica"]:
        renderizar_aba_estereoquimica(smiles)
    if ROTULO_ALERTAS in abas:
        with abas[ROTULO_ALERTAS]:
            renderizar_aba_seguranca(smiles, alertas)
    with abas["Comparar"]:
        renderizar_aba_comparar(smiles)
    with abas["Exportar"]:
        renderizar_aba_exportacao(smiles)


def pagina_isomeria():
    st.markdown("# 🔀 Isomeria")
    renderizar_aba_isomeria()
