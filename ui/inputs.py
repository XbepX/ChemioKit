"""
Entrada da molécula na barra lateral: nome, SMILES ou arquivo (.mol, .sdf, .pdb),
histórico e exemplos. A molécula só muda quando o usuário confirma (Enter ou botão).
"""

import streamlit as st

from chemio_tools import resolver_nome, validar_smiles
from chemio_tools.io_handlers import carregar_mol_de_texto

from .estado import EXEMPLOS, definir_molecula, molecula

ROTULOS_FONTE = {
    "glossario": "glossário do ChemioKit",
    "cache": "PubChem (consulta guardada no computador)",
    "pubchem": "PubChem",
}
FORMAS_DE_ENTRADA = ["Nome", "SMILES", "Arquivo"]


# Callbacks: rodam antes de a página ser desenhada
def _buscar_nome(nome: str | None = None):
    if nome is not None:  # sugestão clicada
        st.session_state.campo_nome = nome
    res = resolver_nome(st.session_state.get("campo_nome", ""))
    st.session_state.resultado_busca = res
    if res["status"] == "encontrado":
        definir_molecula(res["smiles"], res["nome"], origem=res["fonte"])


def _abrir_smiles():
    texto = st.session_state.get("campo_smiles", "").strip()
    if not texto:
        st.session_state.erro_smiles = None
    elif definir_molecula(texto, origem="smiles"):
        st.session_state.erro_smiles = None
    else:
        st.session_state.erro_smiles = texto


def _escolher(smiles: str, nome: str, origem: str = ""):
    definir_molecula(smiles, nome, origem)


def _botoes_de_opcoes(opcoes: list[dict], prefixo: str):
    atual = (molecula() or {}).get("smiles")
    for i, opcao in enumerate(opcoes):
        marcado = "✔️ " if atual == opcao["smiles"] else ""
        st.button(f"{marcado}{opcao['nome']}", key=f"{prefixo}_{i}", on_click=_escolher,
                  args=(opcao["smiles"], opcao["nome"], "glossario"), help=opcao.get("nota") or opcao["smiles"],
                  width="stretch")


def _botoes_de_sugestoes(sugestoes: list[str]):
    if sugestoes:
        st.caption("Você quis dizer:")
        for i, sugestao in enumerate(sugestoes):
            st.button(sugestao, key=f"sugestao_{i}", on_click=_buscar_nome, args=(sugestao,))


def _mostrar_resultado_busca(res: dict | None):
    if not res or res["status"] == "vazio":
        return
    status = res["status"]
    if status == "encontrado":
        st.success(f"**{res['nome']}**: {ROTULOS_FONTE.get(res['fonte'], res['fonte'])}", icon="✅")
    elif status == "ambiguo":
        st.info(f"“{res['consulta']}” corresponde a mais de uma substância. Escolha uma:", icon="❔")
        _botoes_de_opcoes(res["opcoes"], "opcao")
    elif status == "mistura":
        st.info(f"**{res['nome']}** é uma mistura. Escolha um componente:", icon="🧴")
        componentes = sorted(res["componentes"], key=lambda c: c["id"] != res.get("principal"))
        _botoes_de_opcoes(componentes, "componente")
    elif status == "pubchem_indisponivel":
        st.warning(f"“{res['consulta']}” não está no glossário e {res['mensagem'][0].lower()}{res['mensagem'][1:]} "
                   "Verifique a conexão ou use o SMILES.", icon="📡")
        _botoes_de_sugestoes(res["sugestoes"])
    else:
        st.warning(f"“{res['consulta']}” não foi encontrado no glossário nem no PubChem.", icon="🔍")
        _botoes_de_sugestoes(res["sugestoes"])


def renderizar_secao_entradas():
    """Barra lateral: forma de entrada, campo, resultado da busca, histórico e exemplos."""
    st.markdown("**Molécula**")
    forma = st.segmented_control("Entrada", FORMAS_DE_ENTRADA, default="Nome", key="forma_entrada",
                                 label_visibility="collapsed") or "Nome"

    if forma == "Nome":
        with st.form("form_nome", border=False, enter_to_submit=True):
            st.text_input("Nome da substância", key="campo_nome", placeholder="ex.: ácido láctico, aspirina")
            st.form_submit_button("Buscar", on_click=_buscar_nome, type="primary", width="stretch")
        _mostrar_resultado_busca(st.session_state.resultado_busca)

    elif forma == "SMILES":
        with st.form("form_smiles", border=False, enter_to_submit=True):
            st.text_input("SMILES", key="campo_smiles", placeholder="ex.: CC(O)C(=O)O")
            st.form_submit_button("Abrir", on_click=_abrir_smiles, type="primary", width="stretch")
        if st.session_state.get("erro_smiles"):
            st.error("SMILES inválido: o RDKit não reconheceu a estrutura. Confira parênteses, números de anel e letras.", icon="🚫")

    else:
        arquivo = st.file_uploader("Arquivo de estrutura", type=["mol", "sdf", "pdb"],
                                   help="Exportado do ChemSketch, Avogadro, PubChem etc.")
        if arquivo is not None:
            conteudo = arquivo.getvalue().decode("utf-8", errors="replace")
            smiles = carregar_mol_de_texto(conteudo, formato=arquivo.name.split(".")[-1].upper())
            if smiles and validar_smiles(smiles):
                nome = arquivo.name.rsplit(".", 1)[0]
                if (molecula() or {}).get("smiles") != smiles:
                    definir_molecula(smiles, nome, origem="arquivo")
                st.success(f"Estrutura lida de **{arquivo.name}**", icon="✅")
            else:
                st.error("Não foi possível ler a estrutura deste arquivo.", icon="🚫")

    historico = st.session_state.historico
    if historico:
        st.markdown("**Histórico**")
        atual = (molecula() or {}).get("smiles")
        for i, h in enumerate(historico):
            rotulo = h["nome"] or h["smiles"]
            if len(rotulo) > 34:
                rotulo = rotulo[:32] + "…"
            st.button(("● " if h["smiles"] == atual else "") + rotulo, key=f"hist_{i}", on_click=_escolher,
                      args=(h["smiles"], h["nome"]), type="tertiary", help=h["smiles"])

    with st.expander("Exemplos", expanded=not historico):
        for i, (nome, smiles) in enumerate(EXEMPLOS):
            st.button(nome, key=f"exemplo_{i}", on_click=_escolher, args=(smiles, nome, "exemplo"), type="tertiary")
