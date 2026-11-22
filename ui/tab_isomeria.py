import streamlit as st
from chemio_tools import (
    analisar_isomeria_espacial,
    buscar_nomes_isomeros,
    classificar_par_isomeros,
    gerar_isomeros,
)

from .estado import definir_molecula
from .visor import janela

POR_PAGINA = 24
COLUNAS = 4


@st.cache_data(show_spinner=False, max_entries=20)
def _gerar(formula: str) -> dict:
    return gerar_isomeros(formula)


def _abrir_no_chemiokit(smiles: str, nome: str = ""):
    """Abre o isômero na página Molécula (a troca de página é feita pelo app.py)."""
    definir_molecula(smiles, nome or "", origem="isomeria")
    st.session_state.ir_para_molecula = True


def _rotulo(iso: dict, nomes: dict) -> str:
    nome = iso.get("nome") or nomes.get(iso["chave_conectividade"], {}).get("nome")
    return f"{nome} — {iso['smiles']}" if nome else iso["smiles"]


def _selos_estereo(e: dict) -> str:
    selos = []
    if e["geometrica"]:
        selos.append("geométrica")
    if e["possivel_optica"]:
        selos.append("óptica")
    return " · ".join(selos) if selos else "sem isomeria espacial"


def renderizar_aba_isomeria():
    """Aba Isomeria: isômeros a partir da fórmula molecular, classificação de pares e isomeria espacial."""
    st.subheader("Isômeros a partir da fórmula molecular")
    st.caption(
        "Gera todos os isômeros constitucionais (planos) da fórmula, com C, H, N, O, S e halogênios. "
        "Fórmulas com muitas insaturações ou heteroátomos podem ter milhares de isômeros e levar alguns segundos."
    )

    with st.form("form_isomeria", border=False):
        c_formula, c_botao, _ = st.columns([2, 1, 2], vertical_alignment="bottom")
        if "iso_formula" not in st.session_state:  # a busca da página Molécula pode preencher antes
            st.session_state.iso_formula = "C4H10O"
        formula = c_formula.text_input("Fórmula molecular:", key="iso_formula")
        c_botao.form_submit_button("Gerar")

    with st.spinner("Gerando as estruturas..."):
        res = _gerar(formula.strip())

    if res["status"] != "ok":
        st.warning(res["mensagem"])
        return

    isomeros = res["isomeros"]
    st.success(
        f"**{res['formula']}**: {res['total']} isômeros constitucionais possíveis. "
        f"Insaturações (anéis + ligações π): {res['insaturacoes']}."
    )
    st.caption(
        "Todas as estruturas matematicamente possíveis aparecem, inclusive as muito tensionadas ou instáveis "
        "que não existem na prática."
    )

    # Nomes do PubChem (opcional, precisa de internet)
    chave_nomes = f"iso_nomes_{res['formula']}"
    if st.button("🌐 Buscar nomes no PubChem", help="Identifica quais isômeros são substâncias já cadastradas."):
        with st.spinner("Consultando o PubChem..."):
            st.session_state[chave_nomes] = buscar_nomes_isomeros(res["formula"])
    busca = st.session_state.get(chave_nomes)
    nomes = busca["nomes"] if busca and busca["status"] == "ok" else {}
    if busca and busca["status"] != "ok":
        st.warning(f"{busca['mensagem']} Os nomes do glossário continuam aparecendo.")
    elif busca:
        conhecidos = sum(1 for i in isomeros if i["chave_conectividade"] in nomes)
        st.caption(f"{conhecidos} de {len(isomeros)} isômeros estão cadastrados no PubChem (nomes em inglês).")

    # Grupos por função
    grupos = res["grupos"]
    st.markdown("**Isômeros por função:** " + " · ".join(f"{g} ({len(ix)})" for g, ix in grupos.items()))
    chave = res["formula"]
    grupo = st.selectbox("Mostrar:", ["Todos"] + list(grupos), key=f"iso_grupo_{chave}")
    indices = list(range(len(isomeros))) if grupo == "Todos" else grupos[grupo]

    paginas = max(1, -(-len(indices) // POR_PAGINA))
    pagina = st.number_input(f"Página (de {paginas})", 1, paginas, 1, key=f"iso_pagina_{chave}_{grupo}") if paginas > 1 else 1
    visiveis = indices[(pagina - 1) * POR_PAGINA: pagina * POR_PAGINA]

    for inicio in range(0, len(visiveis), COLUNAS):
        cols = st.columns(COLUNAS)
        for col, i in zip(cols, visiveis[inicio: inicio + COLUNAS]):
            iso = isomeros[i]
            with col:
                janela(iso["smiles"], f"iso_{chave}_{i}", altura_3d=230)
                nome = iso.get("nome") or nomes.get(iso["chave_conectividade"], {}).get("nome")
                st.markdown(f"**{i + 1}. {nome}**" if nome else f"**{i + 1}.**")
                st.code(iso["smiles"], language="text")
                st.caption(f"{iso['grupo']} · cadeia {iso['descricao_cadeia']}")
                st.caption(f"Isomeria espacial: {_selos_estereo(iso['estereo'])}")
                st.button("Abrir no ChemioKit", key=f"iso_abrir_{chave}_{i}", on_click=_abrir_no_chemiokit,
                          args=(iso["smiles"], nome or ""))

    st.divider()

    # Comparar dois isômeros
    st.subheader("⚖️ Que tipo de isomeria há entre dois isômeros?")
    opcoes = list(range(len(isomeros)))
    c_a, c_b = st.columns(2)
    a = c_a.selectbox("Isômero A", opcoes, format_func=lambda i: f"{i + 1}. {_rotulo(isomeros[i], nomes)}", key=f"iso_par_a_{chave}")
    b = c_b.selectbox(
        "Isômero B", opcoes, index=min(1, len(opcoes) - 1),
        format_func=lambda i: f"{i + 1}. {_rotulo(isomeros[i], nomes)}", key=f"iso_par_b_{chave}",
    )
    par = classificar_par_isomeros(isomeros[a]["smiles"], isomeros[b]["smiles"])
    if par["relacao"] == "mesma substância":
        st.info("Escolha dois isômeros diferentes.")
    else:
        titulo = f"Isomeria {par['relacao']}: **{par['tipo']}**"
        if par["subtipo"]:
            titulo += f" ({par['subtipo']})"
        st.success(titulo)
        st.write(par["explicacao"])

    st.divider()

    # Isomeria espacial de um isômero
    st.subheader("🪞 Isomeria espacial de um isômero")
    escolhido = st.selectbox(
        "Isômero:", opcoes, format_func=lambda i: f"{i + 1}. {_rotulo(isomeros[i], nomes)}", key=f"iso_espacial_{chave}"
    )
    esp = analisar_isomeria_espacial(isomeros[escolhido]["smiles"])
    c1, c2, c3 = st.columns(3)
    c1.metric("Estereoisômeros", esp["total_estereoisomeros"])
    c2.metric("Opticamente ativos", esp["opticamente_ativos"])
    c3.metric("Meso", esp["meso"])
    detalhes = []
    if esp["duplas_cis_trans"]:
        detalhes.append(f"{esp['duplas_cis_trans']} dupla(s) com isomeria cis-trans")
    if esp["geometrica"] and not esp["duplas_cis_trans"]:
        detalhes.append("isomeria cis-trans em ciclo")
    if esp["centros_estereogenicos"]:
        detalhes.append(f"{esp['centros_estereogenicos']} centro(s) estereogênico(s)")
    st.write("; ".join(detalhes).capitalize() + "." if detalhes else "Este isômero não tem isomeria espacial.")

    if esp["total_estereoisomeros"] > 1:
        cols = st.columns(min(COLUNAS, esp["total_estereoisomeros"]))
        for k, e in enumerate(esp["estereoisomeros"]):
            with cols[k % len(cols)]:
                janela(e["smiles"], f"iso_esp_{chave}_{escolhido}_{k}", quirais=True, altura_3d=230)
                legenda = e["atividade_optica"]
                if e["configuracoes_duplas"]:
                    legenda += " · dupla(s) " + ", ".join(e["configuracoes_duplas"])
                st.caption(legenda)
                st.code(e["smiles"], language="text")
