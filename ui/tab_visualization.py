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

from .estilo import ESCALA_ROTULOS, TEXTO_CARREGANDO, aviso, por_que

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


@st.cache_data(show_spinner=False, max_entries=200)
def _html_3d(smiles: str, opcoes: tuple) -> str | None:
    """3D da aba Estrutura em cache (as opções vêm como tupla para servir de chave)."""
    kw = dict(opcoes)
    kw["indices_destaque"] = list(kw["indices_destaque"])
    return gerar_html_3d(smiles, **kw)


def renderizar_aba_visualizacao(smiles_input: str):
    """Barra de exibição (vale para 2D e 3D) acima da estrutura; ajustes finos à direita."""
    grupos_funcionais = identificar_grupos_funcionais(smiles_input)

    with st.container(horizontal=True, vertical_alignment="center", gap="medium"):
        modo_vis = st.segmented_control("Visualização", ["2D", "3D"], default="2D", key="modo_vis", required=True,
                                        label_visibility="collapsed") or "2D"
        opt_indices = st.toggle("Numerar carbonos", value=True, key="est_indices", help="C1, C2... (mesma numeração no 2D e no 3D)")
        opt_h = st.toggle("Hidrogênios", key="est_h")
        opt_quirais = st.toggle("Quirais", key="est_quirais", help="Marca os carbonos quirais (* e R/S no 2D; malha no 3D)")
        opt_hib = st.toggle("Hibridização", key="est_hib", help="sp³, sp² e sp em cada carbono, com a contagem de ligações σ e π")

    col_render, col_opcoes = st.columns([3, 1.3])

    with col_opcoes:
        with st.expander("Grupos funcionais", expanded=True):
            if grupos_funcionais:
                nomes = [g["grupo"] for g in grupos_funcionais]
                grupo = st.pills("Destacar na estrutura", nomes, key="grupo_ativo",
                                 help="Clique de novo para tirar o destaque.")
                indices_grupo = next((g["indices"] for g in grupos_funcionais if g["grupo"] == grupo), [])
            else:
                st.caption("Nenhum dos grupos funcionais mapeados foi encontrado.")
                indices_grupo = []

        if modo_vis == "2D":
            with st.expander("Desenho 2D"):
                opt_metilas = st.checkbox("Exibir metilas (-CH₃)", key="o2_metilas")
                opt_espessura = st.slider("Espessura da linha", 1, 5, 2, key="o2_espessura")
                opt_fonte = st.slider("Tamanho do texto", 8, 20, 12, key="o2_fonte")
                opt_fundo_escuro_2d = st.checkbox("Fundo escuro", key="o2_fundo")
            st.session_state.opcoes_2d = dict(
                mostrar_h=opt_h, destacar_quirais=opt_quirais, mostrar_indices=opt_indices,
                mostrar_metilas=opt_metilas, espessura_linha=opt_espessura, tamanho_fonte=opt_fonte,
                fundo_escuro=opt_fundo_escuro_2d, indices_destaque_extra=indices_grupo,
                colorir_hibridizacao=opt_hib, escala_rotulos=ESCALA_ROTULOS,
            )
        else:
            with st.expander("Modelo 3D", expanded=True):
                opt_estilo_3d = st.selectbox("Estilo do modelo", ESTILOS_3D, key="o3_estilo")
                opt_espessura_3d = st.slider("Espessura das ligações", 1, 10, 5, key="o3_espessura")
                opt_raio_malha = st.slider("Raio da malha quiral (Å)", 0.8, 2.5, 1.2, step=0.1, key="o3_raio",
                                           disabled=not opt_quirais)
            with st.expander("Superfície"):
                opt_superficie = st.selectbox("Superfície eletrônica", SUPERFICIES, key="o3_superficie")
                opt_coloracao = st.selectbox("Coloração da superfície", list(ROTULOS_COLORACAO),
                                             format_func=ROTULOS_COLORACAO.get, key="o3_coloracao",
                                             disabled=opt_superficie == "Nenhuma")
                opt_opacidade = st.slider("Opacidade", 0.1, 1.0, 0.5, step=0.1, key="o3_opacidade",
                                          disabled=opt_superficie == "Nenhuma")
            with st.expander("Efeitos"):
                opt_auto_spin = st.checkbox("Giro automático", key="o3_spin")
                opt_fundo_escuro = st.checkbox("Fundo escuro", key="o3_fundo")

    with col_render:
        if modo_vis == "2D":
            img_2d = gerar_imagem_2d(smiles_input, **st.session_state.opcoes_2d)
            if img_2d:
                st.image(img_2d)
        else:
            opcoes_3d = dict(
                estilo=opt_estilo_3d, mostrar_h=opt_h, fundo_escuro=opt_fundo_escuro, superficie=opt_superficie,
                coloracao_superficie=opt_coloracao, opacidade_superficie=opt_opacidade, auto_spin=opt_auto_spin,
                destacar_quirais=opt_quirais, espessura_3d=opt_espessura_3d, raio_malha_quiral=opt_raio_malha,
                largura="100%", altura=460, indices_destaque=tuple(indices_grupo),
                rotulos_carbonos=opt_indices, rotulos_hibridizacao=opt_hib,
            )
            with st.spinner(TEXTO_CARREGANDO):
                html_3d = _html_3d(smiles_input, tuple(sorted(opcoes_3d.items())))
            if html_3d:
                st.iframe(html_3d, height=480)
                st.caption(LEGENDA_CPK)
                if opt_superficie != "Nenhuma" and opt_coloracao == "Mapa Eletrostático (MEP)":
                    st.caption("Superfície: vermelho = carga parcial negativa, azul = positiva (cargas de Gasteiger, de −0,4 a +0,4).")
            else:
                aviso("Não foi possível calcular a geometria 3D desta molécula.")
        if opt_hib:
            _legenda_hibridizacao(smiles_input)
