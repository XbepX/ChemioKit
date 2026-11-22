"""
Modo Aula: para projetar. Sem barra lateral, letra grande, estrutura grande e poucos
controles. A vista "Lado a lado" mostra a molécula e a imagem especular, dois
estereoisômeros ou outra molécula do histórico, com a relação entre elas.
"""

import base64

import streamlit as st

from chemio_tools import (
    analisar_hibridizacao_e_ligacoes,
    analisar_isomeria_espacial,
    classificar_par_isomeros,
    exportar_imagem_2d,
    gerar_estereoisomeros,
    gerar_html_3d,
    identificar_centros_quirais,
    obter_enantiomero,
    obter_propriedades_basicas,
)

from .estado import definir_modo, molecula
from .estilo import ESCALA_ROTULOS, formula_bonita, num


def _sair():
    definir_modo("explorar")


def _imagem_2d(smiles: str, largura: int, altura: int, quirais: bool, hib: bool, hs: bool) -> bytes:
    r = exportar_imagem_2d(smiles, "png", largura=largura, altura=altura, mostrar_indices=True,
                           destacar_quirais=quirais, colorir_hibridizacao=hib, mostrar_h=hs, espessura_linha=2, tamanho_fonte=14, escala_rotulos=ESCALA_ROTULOS)
    return base64.b64decode(r["conteudo"])


def _mostrar(smiles: str, dim: str, largura: int, altura: int, op: dict):
    if dim == "2D":
        st.image(_imagem_2d(smiles, largura, altura, op["quirais"], op["hib"], op["hs"]), width="stretch")
    else:
        html = gerar_html_3d(smiles, mostrar_h=op["hs"], destacar_quirais=op["quirais"], auto_spin=op["girar"], largura=largura, altura=altura)
        if html:
            st.iframe(html, height=altura + 20)
        else:
            st.warning("Não foi possível calcular a geometria 3D.", icon="⚠️")


def _legenda(smiles: str) -> str:
    dados = identificar_centros_quirais(smiles)
    esp = analisar_isomeria_espacial(smiles)
    partes = [dados["atividade_optica"]]
    if dados["total_centros"]:
        partes.append(f"{dados['total_centros']} C quiral: " + ", ".join(
            f"{c['rotulo_carbono']}" + (f" ({c['configuracao']})" if c["configuracao"] in ("R", "S") else "") for c in dados["centros"]))
    duplas = [e for x in esp["estereoisomeros"] if x["smiles"] == smiles for e in x["configuracoes_duplas"]]
    if duplas:
        partes.append("dupla " + ", ".join(duplas))
    return " · ".join(partes)


def renderizar_modo_aula(smiles: str):
    m = molecula()
    dados = obter_propriedades_basicas(smiles)
    c_titulo, c_sair = st.columns([6, 1], vertical_alignment="center")
    with c_titulo:
        st.markdown(f"# {m['nome'] or smiles}")
        st.markdown(f"**{formula_bonita(dados['formula'])}** · {num(dados['massa_molecular'])} g/mol")
    c_sair.button("Sair", icon="✖️", on_click=_sair, width="stretch", help="Sair do modo aula")

    with st.container(horizontal=True, vertical_alignment="center"):
        vista = st.segmented_control("Mostrar", ["Estrutura", "Lado a lado"], default="Estrutura", key="aula_vista", required=True)
        dim = st.segmented_control("Dimensão", ["2D", "3D"], default="2D", key="aula_dim", required=True)
        op = {
            "quirais": st.toggle("Quirais", key="aula_quirais"),
            "hs": st.toggle("Hidrogênios", key="aula_hs"),
            "hib": st.toggle("Hibridização", key="aula_hib", disabled=dim == "3D"),
            "girar": st.toggle("Girar", key="aula_girar", disabled=dim == "2D"),
        }

    if vista == "Estrutura":
        _mostrar(smiles, dim, 1100, 640, op)
        st.markdown(f"**{_legenda(smiles)}**")
        if op["hib"] and dim == "2D":
            h = analisar_hibridizacao_e_ligacoes(smiles)
            c = h["contagem_hibridizacao"]
            st.markdown(f"🔵 sp³: **{c['sp3']}** · 🟠 sp²: **{c['sp2']}** · 🟣 sp: **{c['sp']}** · σ: **{h['sigma']}** · π: **{h['pi']}**")
        return

    # Lado a lado
    fonte = st.segmented_control("Comparar com", ["Imagem especular", "Estereoisômeros", "Outra molécula"],
                                 default="Imagem especular", key="aula_fonte", required=True)
    estereo = gerar_estereoisomeros(smiles)
    if fonte == "Imagem especular":
        definida = identificar_centros_quirais(smiles)["atividade_optica"] != "Indefinida"
        base = smiles if definida or len(estereo) == 1 else estereo[0]
        if base != smiles:
            st.caption("O SMILES não define a configuração; foi usado o primeiro estereoisômero.")
        outra = obter_enantiomero(base) or base
        rotulos = ("Molécula", "Imagem especular")
    elif fonte == "Estereoisômeros":
        if len(estereo) < 2:
            st.info("Esta molécula não tem estereoisômeros.", icon="ℹ️")
            return
        ca, cb = st.columns(2)
        base = ca.selectbox("Esquerda", estereo, key="aula_e1", format_func=lambda s: f"{estereo.index(s) + 1}. {s}")
        outra = cb.selectbox("Direita", estereo, index=1, key="aula_e2", format_func=lambda s: f"{estereo.index(s) + 1}. {s}")
        rotulos = ("Estereoisômero A", "Estereoisômero B")
    else:
        historico = [h for h in st.session_state.historico if h["smiles"] != smiles]
        if not historico:
            st.info("Abra outra molécula antes (no modo Explorar) para compará-la aqui.", icon="ℹ️")
            return
        escolha = st.selectbox("Molécula", historico, format_func=lambda h: h["nome"] or h["smiles"], key="aula_outra")
        base, outra = smiles, escolha["smiles"]
        rotulos = (m["nome"] or "Molécula", escolha["nome"] or escolha["smiles"])

    esquerda, direita = st.columns(2)
    with esquerda:
        _mostrar(base, dim, 640, 520, op)
        st.markdown(f"**{rotulos[0]}** · {_legenda(base)}")
    with direita:
        _mostrar(outra, dim, 640, 520, op)
        st.markdown(f"**{rotulos[1]}** · {_legenda(outra)}")

    par = classificar_par_isomeros(base, outra)
    if par["relacao"] == "mesma substância":
        texto = "São a mesma substância: as duas imagens se sobrepõem." if fonte == "Imagem especular" else "São a mesma substância."
    elif par["relacao"] in ("plana", "espacial"):
        texto = f"Isomeria {par['relacao']}: {par['tipo']}" + (f" ({par['subtipo']})" if par["subtipo"] else "") + "."
    else:
        texto = par["explicacao"]
    st.markdown(f"## {texto}")
