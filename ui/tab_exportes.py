"""Aba Exportar: identificadores para copiar, desenho 2D (PNG/SVG) e coordenadas 3D (SDF/PDB)."""

import base64

import streamlit as st

from chemio_tools import exportar_bloco_3d, exportar_imagem_2d, obter_identificadores

OPCOES_2D_PADRAO = dict(mostrar_indices=True)


def renderizar_aba_exportacao(smiles_input: str):
    ids = obter_identificadores(smiles_input)
    st.markdown("#### Identificadores")
    st.caption("Clique no ícone de copiar no canto de cada caixa.")
    st.markdown("**SMILES canônico**")
    st.code(ids["smiles_canonico"], language="text", wrap_lines=True)
    st.markdown("**InChI**")
    st.code(ids["inchi"] or "—", language="text", wrap_lines=True)
    st.markdown("**InChIKey** (usado para buscar a estrutura em bancos de dados)")
    st.code(ids["inchikey"] or "—", language="text")

    st.divider()
    st.markdown("#### Desenho 2D")
    usar_opcoes = st.toggle("Usar as opções escolhidas na aba Estrutura", value=True, key="exp_usar_opcoes",
                            help="Hidrogênios, numeração, destaques, hibridização, espessura e fundo.")
    opcoes = st.session_state.get("opcoes_2d", OPCOES_2D_PADRAO) if usar_opcoes else OPCOES_2D_PADRAO
    st.caption("Alta resolução (1200 × 1000 px). O SVG pode ser ampliado sem perder qualidade (slides, provas, documentos).")
    c_png, c_svg, _ = st.columns([1.2, 1.2, 2])
    png = exportar_imagem_2d(smiles_input, formato="png", **opcoes)
    svg = exportar_imagem_2d(smiles_input, formato="svg", **opcoes)
    if png:
        c_png.download_button("⬇️ Imagem PNG (.png)", base64.b64decode(png["conteudo"]), file_name="molecula_2d.png", mime=png["mime"])
    if svg:
        c_svg.download_button("⬇️ Imagem SVG (.svg)", svg["conteudo"], file_name="molecula_2d.svg", mime=svg["mime"])

    st.divider()
    st.markdown("#### Coordenadas 3D")
    st.caption("Geometria otimizada (MMFF) para abrir no Avogadro, PyMOL, ChemSketch etc.")
    c_sdf, c_pdb, _ = st.columns([1.2, 1.2, 2])
    sdf = exportar_bloco_3d(smiles_input, formato="SDF")
    if sdf:
        c_sdf.download_button("⬇️ Arquivo SDF (.sdf)", sdf, file_name="molecula_3d.sdf", mime="chemical/x-mdl-sdfile")
    pdb = exportar_bloco_3d(smiles_input, formato="PDB")
    if pdb:
        c_pdb.download_button("⬇️ Arquivo PDB (.pdb)", pdb, file_name="molecula_3d.pdb", mime="chemical/x-pdb")
    if not (sdf or pdb):
        st.warning("Não foi possível calcular a geometria 3D desta molécula.", icon="⚠️")
