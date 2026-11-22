"""Aba Comparar: segunda molécula, similaridade de Tanimoto, subestrutura comum e tipo de isomeria."""

import streamlit as st

from chemio_tools import classificar_par_isomeros, comparar_moleculas, gerar_imagem_2d, resolver_nome, validar_smiles
from rdkit import RDLogger

from .estado import molecula
from .estilo import erro, fundo_escuro_padrao, num, por_que


def _resolver_entrada(texto: str) -> dict:
    """Aceita SMILES ou nome. Devolve {"smiles", "nome"} ou {"erro"} / {"opcoes"}."""
    texto = texto.strip()
    if not texto:
        return {}
    RDLogger.DisableLog("rdApp.*")
    try:
        e_smiles = validar_smiles(texto)
    finally:
        RDLogger.EnableLog("rdApp.*")
    if e_smiles:
        return {"smiles": texto, "nome": ""}
    res = resolver_nome(texto)
    if res["status"] == "encontrado":
        return {"smiles": res["smiles"], "nome": res["nome"]}
    if res["status"] in ("ambiguo", "mistura"):
        return {"opcoes": res.get("opcoes") or res.get("componentes")}
    return {"erro": res.get("mensagem") or f"“{texto}” não foi reconhecido como SMILES nem encontrado pelo nome."}


def renderizar_aba_comparar(smiles_input: str):
    st.markdown("Compare a molécula aberta com outra: digite o **nome** ou o **SMILES** da segunda.")
    with st.form("form_comparar", border=False, enter_to_submit=True):
        c_txt, c_btn = st.columns([4, 1], vertical_alignment="bottom")
        c_txt.text_input("Segunda molécula", key="comparar_texto", placeholder="ex.: ácido propanoico ou CCC(=O)O")
        enviado = c_btn.form_submit_button("Comparar", type="primary", width="stretch")
    if enviado:
        st.session_state.comparar_b = _resolver_entrada(st.session_state.comparar_texto)

    b = st.session_state.get("comparar_b") or {}
    if "opcoes" in b:
        escolha = st.radio("O nome corresponde a mais de uma substância:", b["opcoes"], format_func=lambda o: o["nome"], key="comparar_opcao")
        b = {"smiles": escolha["smiles"], "nome": escolha["nome"]}
    if "erro" in b:
        erro(b["erro"], "Confira a grafia ou use o SMILES.")
        return
    if "smiles" not in b:
        st.caption("A comparação aparece aqui.")
        return

    r = comparar_moleculas(smiles_input, b["smiles"])
    nome_a = molecula().get("nome") or "Molécula aberta"
    nome_b = b["nome"] or b["smiles"]

    c1, c2, c3 = st.columns(3)
    c1.metric("Similaridade (Tanimoto)", num(r["tanimoto"]))
    c2.metric("Átomos em comum (MCS)", r["mcs"]["num_atomos"])
    with c3:
        por_que([
            "**Tanimoto** compara as impressões digitais das moléculas (fragmentos ao redor de cada átomo, "
            "Morgan de raio 2): 1 = mesmas impressões, 0 = nenhuma em comum.",
            "**MCS** é a maior subestrutura comum: o maior pedaço que aparece igual nas duas, destacado nos desenhos.",
        ])

    a_img, b_img = st.columns(2)
    with a_img:
        st.image(gerar_imagem_2d(smiles_input, indices_destaque_extra=r["mcs"]["indices_a"], fundo_escuro=fundo_escuro_padrao()))
        st.caption(nome_a)
    with b_img:
        st.image(gerar_imagem_2d(b["smiles"], indices_destaque_extra=r["mcs"]["indices_b"], fundo_escuro=fundo_escuro_padrao()))
        st.caption(nome_b)
    if not r["mcs"]["completa"]:
        st.caption("A busca da subestrutura comum parou no tempo limite; o destaque pode ser menor que o real.")

    par = classificar_par_isomeros(smiles_input, b["smiles"])
    if par["relacao"] in ("plana", "espacial"):
        st.success(f"São isômeros. Isomeria {par['relacao']}: **{par['tipo']}**" + (f" ({par['subtipo']})" if par["subtipo"] else "") + ".")
        st.markdown(par["explicacao"])
    elif par["relacao"] == "mesma substância":
        st.info("As duas estruturas são a mesma substância.")
    else:
        st.caption(f"Não são isômeros: {par['explicacao'][0].lower()}{par['explicacao'][1:]}")

    if st.session_state.get("tecnico"):
        st.caption(f"SMARTS da MCS: `{r['mcs']['smarts']}` · Morgan raio 2, 2048 bits · tempo limite da MCS: 10 s.")
