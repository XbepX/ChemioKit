"""
Aba Estrutura: desenho 2D e modelo 3D com todas as opções, destaque de grupos funcionais
e da hibridização. As opções escolhidas ficam em st.session_state.opcoes_2d para que a
aba Exportar baixe o desenho exatamente como está na tela.
"""

import streamlit as st

from chemio_tools import (
    analisar_hibridizacao_e_ligacoes,
    explicar_hibridizacao,
    explicar_ligacoes_sigma_pi,
    gerar_html_3d,
    gerar_imagem_2d,
    identificar_grupos_funcionais,
)

from .estilo import ESCALA_ROTULOS, TEXTO_CARREGANDO, aviso, fundo_escuro_padrao, por_que

ESTILOS_3D = ["Ball & Stick", "Wireframe / Line", "Stick (Bastonetes)", "CPK / Esferas"]
SUPERFICIES = ["Nenhuma", "Van der Waals (VDW)", "Superfície Acessível ao Solvente (SAS)"]
# Rótulo exibido -> valor interno esperado por gerar_html_3d (a lógica não muda)
ROTULOS_COLORACAO = {
    "Mapa Eletrostático (MEP)": "Cargas Parciais (Gasteiger)",
    "Monocromático (Azul Claro)": "Monocromático (Azul Claro)",
}
LEGENDA_CPK = "Cores dos átomos: CPK (Jmol). C preto (cinza no fundo escuro), H branco, O vermelho, N azul, S amarelo, Cl verde."


def _legenda_hibridizacao(smiles: str):
    dados = analisar_hibridizacao_e_ligacoes(smiles)
    if not dados:
        return
    c = dados["contagem_hibridizacao"]
    hib = explicar_hibridizacao(smiles)
    sp = explicar_ligacoes_sigma_pi(smiles)
    with st.container(horizontal=True, vertical_alignment="center"):
        st.markdown(
            f"🔵 **sp³**: {c['sp3']} &nbsp;&nbsp; 🟠 **sp²**: {c['sp2']} &nbsp;&nbsp; 🟣 **sp**: {c['sp']}"
            f" &nbsp;&nbsp;|&nbsp;&nbsp; ligações **σ**: {dados['sigma']} &nbsp;&nbsp; **π**: {dados['pi']}",
            width="content",
        )
        por_que([f"**Regra:** {hib['regra']}"] + [f"- {c['texto']}" for c in hib["carbonos"]]
                + [f"**Ligações σ e π:** {sp['regra']}", sp["texto"]])


def renderizar_aba_visualizacao(smiles_input: str):
    """Painel 2D/3D com opções à direita."""
    grupos_funcionais = identificar_grupos_funcionais(smiles_input)
    col_render, col_opcoes = st.columns([3, 1.3])

    with col_opcoes:
        modo_vis = st.segmented_control("Visualização", ["2D", "3D"], default="2D", key="modo_vis") or "2D"

        if modo_vis == "2D":
            with st.expander("Átomos e rótulos", expanded=True):
                opt_mostrar_h = st.checkbox("Hidrogênios explícitos", key="o2_h")
                opt_destacar_q = st.checkbox("Destacar quirais (* e R/S)", key="o2_quirais")
                opt_mostrar_idx = st.checkbox("Numerar carbonos (C1, C2...)", value=True, key="o2_indices")
                opt_metilas = st.checkbox("Exibir metilas (-CH₃)", key="o2_metilas")
                opt_hibridizacao = st.checkbox("Colorir carbonos por hibridização", key="o2_hib")
            with st.expander("Grupos funcionais", expanded=True):
                if grupos_funcionais:
                    nomes = [g["grupo"] for g in grupos_funcionais]
                    grupo = st.pills("Destacar no desenho", nomes, key="grupo_ativo",
                                     help="Clique de novo para tirar o destaque.")
                    indices_grupo = next((g["indices"] for g in grupos_funcionais if g["grupo"] == grupo), [])
                else:
                    st.caption("Nenhum dos grupos funcionais mapeados foi encontrado.")
                    indices_grupo = []
            with st.expander("Estilo e traço"):
                opt_espessura = st.slider("Espessura da linha", 1, 5, 2, key="o2_espessura")
                opt_fonte = st.slider("Tamanho do texto", 8, 20, 12, key="o2_fonte")
                opt_fundo_escuro_2d = st.checkbox("Fundo escuro", value=fundo_escuro_padrao(), key="o2_fundo")

            st.session_state.opcoes_2d = dict(
                mostrar_h=opt_mostrar_h, destacar_quirais=opt_destacar_q, mostrar_indices=opt_mostrar_idx,
                mostrar_metilas=opt_metilas, espessura_linha=opt_espessura, tamanho_fonte=opt_fonte,
                fundo_escuro=opt_fundo_escuro_2d, indices_destaque_extra=indices_grupo,
                colorir_hibridizacao=opt_hibridizacao, escala_rotulos=ESCALA_ROTULOS,
            )
        else:
            with st.expander("Geometria e estilo", expanded=True):
                opt_estilo_3d = st.selectbox("Estilo do modelo", ESTILOS_3D, key="o3_estilo")
                opt_espessura_3d = st.slider("Espessura das ligações", 1, 10, 5, key="o3_espessura")
                opt_mostrar_h_3d = st.checkbox("Mostrar hidrogênios", value=True, key="o3_h")
                opt_destacar_q_3d = st.checkbox("Destacar quirais (malha 3D)", key="o3_quirais")
                opt_raio_malha = st.slider("Raio da malha quiral (Å)", 0.8, 2.5, 1.2, step=0.1, key="o3_raio",
                                           disabled=not opt_destacar_q_3d)
            with st.expander("Superfície"):
                opt_superficie = st.selectbox("Superfície eletrônica", SUPERFICIES, key="o3_superficie")
                opt_coloracao = st.selectbox("Coloração da superfície", list(ROTULOS_COLORACAO),
                                             format_func=ROTULOS_COLORACAO.get, key="o3_coloracao",
                                             disabled=opt_superficie == "Nenhuma")
                opt_opacidade = st.slider("Opacidade", 0.1, 1.0, 0.5, step=0.1, key="o3_opacidade",
                                          disabled=opt_superficie == "Nenhuma")
            with st.expander("Efeitos"):
                opt_auto_spin = st.checkbox("Giro automático", key="o3_spin")
                opt_fundo_escuro = st.checkbox("Fundo escuro", value=fundo_escuro_padrao(), key="o3_fundo")

    with col_render:
        if modo_vis == "2D":
            img_2d = gerar_imagem_2d(smiles_input, **st.session_state.opcoes_2d)
            if img_2d:
                st.image(img_2d)
            if st.session_state.opcoes_2d["colorir_hibridizacao"]:
                _legenda_hibridizacao(smiles_input)
        else:
            with st.spinner(TEXTO_CARREGANDO):
                html_3d = gerar_html_3d(
                    smiles_input,
                    estilo=opt_estilo_3d,
                    mostrar_h=opt_mostrar_h_3d,
                    fundo_escuro=opt_fundo_escuro,
                    superficie=opt_superficie,
                    coloracao_superficie=opt_coloracao,
                    opacidade_superficie=opt_opacidade,
                    auto_spin=opt_auto_spin,
                    destacar_quirais=opt_destacar_q_3d,
                    espessura_3d=opt_espessura_3d,
                    raio_malha_quiral=opt_raio_malha,
                    largura=640,
                    altura=460,
                )
            if html_3d:
                st.iframe(html_3d, height=480)
                st.caption(LEGENDA_CPK)
                if opt_superficie != "Nenhuma" and opt_coloracao == "Mapa Eletrostático (MEP)":
                    st.caption("Superfície: vermelho = carga parcial negativa, azul = positiva (cargas de Gasteiger, de −0,4 a +0,4).")
            else:
                aviso("Não foi possível calcular a geometria 3D desta molécula.")
