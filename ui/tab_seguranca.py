"""Aba Alertas (Segurança): alertas estruturais do FilterCatalog, sempre apresentados como alertas."""

import streamlit as st

from .visor import janela



def renderizar_aba_seguranca(smiles_input: str, alertas: dict):
    st.warning(
        f"**{alertas['total']} alerta(s) estrutural(is).** {alertas['aviso']} "
        "Muitos fármacos seguros têm algum desses grupos.",
        icon="⚠️",
    )
    por_catalogo: dict[str, list[dict]] = {}
    for a in alertas["alertas"]:
        por_catalogo.setdefault(a["descricao_catalogo"], []).append(a)

    for catalogo, lista in por_catalogo.items():
        st.markdown(f"#### {catalogo}")
        cols = st.columns(3)
        for k, a in enumerate(lista):
            with cols[k % 3]:
                janela(smiles_input, f"alerta_{catalogo}_{k}", indices=a["indices"], altura_3d=260)
                st.markdown(f"**{a['nome'].replace('_', ' ')}**")
    if st.session_state.get("tecnico"):
        st.caption("Catálogos do RDKit (FilterCatalog): Brenk et al., ChemMedChem 2008; Baell e Holloway, J. Med. Chem. 2010 (PAINS); "
                   "Jadhav et al., J. Med. Chem. 53 (NIH). Os nomes dos alertas são os originais dos catálogos, em inglês.")
