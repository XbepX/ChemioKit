"""
Aba Estereoquímica: atividade óptica, carbonos quirais (com os quatro ligantes),
comparação com o máximo teórico 2^n e galeria de estereoisômeros.
"""

import streamlit as st

from chemio_tools import (
    LIMITE_ESTEREOISOMEROS,
    analisar_isomeria_espacial,
    contar_elementos_estereogenicos,
    explicar_atividade_optica,
    explicar_carbonos_quirais,
    gerar_estereoisomeros,
    identificar_centros_quirais,
)

from .estado import definir_molecula
from .estilo import TEXTO_CARREGANDO, por_que
from .visor import janela

ICONES = {"Opticamente Ativa": "✨", "Inativa (composto meso)": "⚪", "Inativa": "⚪", "Indefinida": "❔"}


def _abrir(smiles: str):
    definir_molecula(smiles, "", origem="estereoisomero")


def renderizar_aba_estereoquimica(smiles_input: str):
    dados = identificar_centros_quirais(smiles_input)
    optica = explicar_atividade_optica(smiles_input)
    quirais = explicar_carbonos_quirais(smiles_input)

    col_img, col_txt = st.columns([1, 1.3], gap="large")
    with col_img:
        dim = janela(smiles_input, "estereo_principal", quirais=True, rotulos=True, altura_3d=380)
        st.caption("Carbonos quirais marcados com * e a configuração (R/S), quando definida."
                   if dim == "2D" else "Carbonos quirais envolvidos por uma malha azul. Gire o modelo com o mouse.")
    with col_txt:
        atividade = dados["atividade_optica"]
        st.markdown(f"### {ICONES.get(atividade, '')} {atividade}")
        st.markdown(optica["texto"])
        st.markdown(f"**{quirais['texto']}**")
        for c in quirais["centros"]:
            config = f" — configuração **{c['configuracao']}**" if c["configuracao"] else " — configuração não definida"
            st.markdown(f"- **{c['rotulo']}**: {', '.join(c['ligantes'])}{config}")
        if quirais["centros"]:
            por_que([c["texto"] for c in quirais["centros"]]
                    + ["Um carbono é quiral quando os quatro grupos ligados a ele são diferentes entre si."])
        esp = analisar_isomeria_espacial(smiles_input)
        if esp["duplas_cis_trans"]:
            st.markdown(f"- {esp['duplas_cis_trans']} ligação(ões) dupla(s) com isomeria geométrica (cis/trans, E/Z).")
        elif esp["geometrica"]:
            st.markdown("- Isomeria geométrica em ciclo (substituintes do mesmo lado ou em lados opostos do anel).")
        if st.session_state.get("tecnico"):
            st.caption("Índices RDKit dos centros: " + ", ".join(f"{c['rotulo_carbono']}={c['indice_rdkit']}" for c in dados["centros"])
                       if dados["centros"] else "Sem centros.")

    st.divider()
    st.markdown("#### Estereoisômeros possíveis")
    with st.spinner(TEXTO_CARREGANDO):
        isomeros = gerar_estereoisomeros(smiles_input)
    n = contar_elementos_estereogenicos(smiles_input)
    maximo = 2 ** n
    total = len(isomeros)

    st.success(f"Estereoisômeros únicos encontrados: **{total}**")
    if n == 0:
        st.info("A molécula não possui elementos estereogênicos.")
    elif maximo > LIMITE_ESTEREOISOMEROS:
        st.warning(
            f"O máximo teórico é $2^n$ = {maximo} (n = {n} elementos estereogênicos). "
            f"A enumeração foi limitada a {LIMITE_ESTEREOISOMEROS} combinações (limite padrão do RDKit), "
            f"por isso a galeria pode não mostrar todos os estereoisômeros."
        )
    elif total < maximo:
        st.info(
            f"O máximo teórico é $2^n$ = {maximo} (n = {n} elementos estereogênicos). "
            f"Foram encontrados {total} estereoisômeros únicos porque algumas combinações "
            f"descrevem a mesma molécula, como ocorre em compostos meso."
        )
    else:
        st.info(f"O máximo teórico é $2^n$ = {maximo} (n = {n}), e todas as combinações correspondem a estereoisômeros distintos.")

    if total > 1:
        atividades = {s: identificar_centros_quirais(s)["atividade_optica"] for s in isomeros[:48]}
        cols_por_linha = 4
        for i in range(0, min(total, 48), cols_por_linha):
            cols = st.columns(cols_por_linha)
            for j, smi in enumerate(isomeros[i:i + cols_por_linha]):
                with cols[j]:
                    janela(smi, f"estereo_{i + j}", quirais=True, altura_3d=230)
                    st.caption(f"Isômero {i + j + 1} · {ICONES.get(atividades[smi], '')} {atividades[smi]}")
                    st.code(smi, language="text", wrap_lines=True)
                    st.button("Abrir", key=f"estereo_abrir_{i + j}", on_click=_abrir, args=(smi,), type="tertiary")
        if total > 48:
            st.caption(f"Mostrando 48 de {total}.")
