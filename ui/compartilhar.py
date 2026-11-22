"""Compartilhar: link que abre o ChemioKit na molécula, no modo e na aba escolhidos, e o QR code dele."""

import io

import segno
import streamlit as st

from chemio_tools import TIPOS_ATIVIDADE

from .estado import ABAS, MODOS, molecula, montar_link


def gerar_qr_png(texto: str, escala: int = 8) -> bytes:
    qr = segno.make(texto, error="m")
    buffer = io.BytesIO()
    qr.save(buffer, kind="png", scale=escala, border=2)
    return buffer.getvalue()


@st.dialog("Compartilhar esta molécula", width="medium")
def dialogo_compartilhar():
    m = molecula()
    st.caption("Quem abrir o link verá o ChemioKit já nesta molécula, no modo escolhido. Nada é enviado a servidores externos.")
    modo = st.segmented_control("Abrir em", list(MODOS), format_func=MODOS.get, default=st.session_state.modo, key="comp_modo") or "explorar"
    aba = atividade = None
    if modo == "explorar":
        aba = st.selectbox("Na aba", ABAS, key="comp_aba")
    elif modo == "atividade":
        atividade = st.selectbox("Atividade", list(TIPOS_ATIVIDADE), format_func=TIPOS_ATIVIDADE.get,
                                 index=list(TIPOS_ATIVIDADE).index(st.session_state.atividade_tipo), key="comp_atividade")
    link = montar_link(modo, aba, atividade)
    st.code(link, language="text", wrap_lines=True)
    c_qr, c_txt = st.columns([1, 1])
    png = gerar_qr_png(link)
    c_qr.image(png, caption="Aponte a câmera do celular", width=220)
    with c_txt:
        st.markdown(f"**{m.get('nome') or m['smiles']}**")
        st.caption("Projete o QR code na aula ou cole o link numa mensagem para a turma.")
        st.download_button("⬇️ Baixar QR code (.png)", png, file_name="chemiokit_qr.png", mime="image/png")
    if link.startswith("http://localhost") or "127.0.0.1" in link:
        st.info(
            "Este endereço só funciona neste computador. Para os alunos abrirem no celular, o app precisa estar "
            "rodando num endereço da rede da escola ou na internet.",
            icon="ℹ️",
        )
