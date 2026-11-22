"""Cartão fixo no topo: nome, fórmula, massa e SMILES copiável da molécula aberta."""

import streamlit as st

from chemio_tools import obter_propriedades_basicas

from .compartilhar import dialogo_compartilhar
from .estado import molecula
from .estilo import formula_bonita, num

ORIGENS = {"glossario": "glossário", "pubchem": "PubChem", "cache": "PubChem", "arquivo": "arquivo", "link": "link compartilhado"}


def renderizar_cartao():
    m = molecula()
    dados = obter_propriedades_basicas(m["smiles"])
    with st.container(key="cartao"):
        c_nome, c_dados, c_acoes = st.columns([3, 2, 1.5], vertical_alignment="center")
        with c_nome:
            st.markdown(f"### {m['nome'] or 'Molécula sem nome'}")
            st.code(m["smiles"], language="text")
        with c_dados:
            st.markdown(f"**{formula_bonita(dados['formula'])}** · {num(dados['massa_molecular'])} g/mol")
            if m.get("origem") in ORIGENS:
                st.caption(f"Origem: {ORIGENS[m['origem']]}")
        with c_acoes:
            if st.button("Compartilhar", icon="🔗", width="stretch", key="btn_compartilhar"):
                dialogo_compartilhar()
