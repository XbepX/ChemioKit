"""
ChemioKit: ponto de entrada da interface (Streamlit).

Duas páginas (Molécula e Isomeria) e três modos de uso na página Molécula:
  Explorar  análise completa, com explicações ("Por quê?") e detalhes técnicos opcionais;
  Aula      para projetar: sem barra lateral, letra grande, comparação lado a lado;
  Atividade o estudante responde e o ChemioKit confere e explica.
Links com ?smiles=...&modo=...&aba=...&atividade=... abrem o app já na situação preparada.
"""

import rdkit
import streamlit as st

from ui import estado, pagina_isomeria, pagina_molecula, renderizar_secao_entradas
from ui.estilo import aplicar_css

st.set_page_config(page_title="ChemioKit", page_icon="🧪", layout="wide")

estado.inicializar()
estado.ler_link()
modo = st.session_state.modo

pag_molecula = st.Page(pagina_molecula, title="Molécula", icon="🧪", url_path="molecula", default=True)
pag_isomeria = st.Page(pagina_isomeria, title="Isomeria", icon="🔀", url_path="isomeria")
pagina = st.navigation([pag_molecula, pag_isomeria], position="hidden" if modo == "aula" else "sidebar")

# Botões que levam a outra página ("Abrir no ChemioKit" na Isomeria; "Ver os isômeros" na busca)
if st.session_state.pop("ir_para_molecula", False) and pagina.title != pag_molecula.title:
    st.switch_page(pag_molecula)
if st.session_state.pop("ir_para_isomeria", False) and pagina.title != pag_isomeria.title:
    st.switch_page(pag_isomeria)

aplicar_css(modo)

if modo != "aula":
    with st.sidebar:
        if pagina.title == pag_molecula.title:
            # Os valores ficam em "modo" e "tecnico"; os widgets usam chaves próprias porque o Streamlit
            # apaga o valor de um widget que não é desenhado (a barra lateral some no Modo Aula).
            estado.espelhar_widget("w_modo", "modo")
            st.radio("Modo de uso", list(estado.MODOS), format_func=estado.MODOS.get, key="w_modo",
                     captions=["análise completa, com explicações", "para projetar em sala", "o estudante responde e confere"],
                     on_change=estado.copiar_widget, args=("w_modo", "modo"))
            if st.session_state.modo == "explorar":
                estado.espelhar_widget("w_tecnico", "tecnico")
                st.toggle("Detalhes técnicos", key="w_tecnico", on_change=estado.copiar_widget, args=("w_tecnico", "tecnico"),
                          help="Tabela completa, métodos, versões e exportação de dados.")
            st.divider()
            renderizar_secao_entradas()  # histórico e exemplos; a busca fica na página
        st.divider()
        st.caption(f"ChemioKit · RDKit {rdkit.__version__} · Streamlit {st.__version__}")

pagina.run()
