"""
Entrada da molécula: um campo único que aceita nome, SMILES ou fórmula molecular, no centro
da tela inicial e no topo da página quando já há uma molécula aberta. O app descobre sozinho
o que foi digitado (chemio_tools.resolver_entrada). Arquivos .mol/.sdf/.pdb entram pelo botão
"Abrir arquivo". A barra lateral fica com o histórico e os exemplos.
"""

import streamlit as st

from chemio_tools import resolver_entrada, validar_smiles
from chemio_tools.io_handlers import carregar_mol_de_texto

from .estado import EXEMPLOS, definir_molecula, molecula

ROTULOS_FONTE = {
    "glossario": "glossário do ChemioKit",
    "cache": "PubChem (consulta guardada no computador)",
    "pubchem": "PubChem",
    "smiles": "SMILES",
    "formula": "fórmula molecular",
}
PLACEHOLDER = "ex.: ácido láctico, aspirina, CC(O)C(=O)O ou C2H6O"


# ------------------------------------------------------------------ callbacks (rodam antes de desenhar a página)


def _buscar(texto: str | None = None):
    if texto is not None:  # sugestão clicada vira o texto da busca
        st.session_state.campo_busca = texto
    res = resolver_entrada(st.session_state.get("campo_busca", ""))
    if res["status"] == "encontrado":
        definir_molecula(res["smiles"], res.get("nome", ""), origem=res["fonte"])
        st.session_state.campo_busca = ""  # a molécula abriu: o campo fica livre para a próxima busca
        st.session_state.aviso_busca = f"{res.get('nome') or res['smiles']}: {ROTULOS_FONTE.get(res['fonte'], res['fonte'])}"
        st.session_state.resultado_busca = res if res.get("aviso") else None
    else:
        st.session_state.resultado_busca = res


def _escolher(smiles: str, nome: str, origem: str = ""):
    definir_molecula(smiles, nome, origem)
    st.session_state.resultado_busca = None
    st.session_state.campo_busca = ""


def _ir_para_isomeria(formula: str):
    st.session_state.iso_formula = formula
    st.session_state.ir_para_isomeria = True
    st.session_state.resultado_busca = None


def _carregar_arquivo():
    arquivo = st.session_state.get("arquivo_estrutura")
    if arquivo is None:
        return
    conteudo = arquivo.getvalue().decode("utf-8", errors="replace")
    smiles = carregar_mol_de_texto(conteudo, formato=arquivo.name.split(".")[-1].upper())
    if smiles and validar_smiles(smiles):
        definir_molecula(smiles, arquivo.name.rsplit(".", 1)[0], origem="arquivo")
        st.session_state.aviso_busca = f"Estrutura lida de {arquivo.name}"
        st.session_state.resultado_busca = None
    else:
        st.session_state.resultado_busca = {"status": "arquivo_invalido", "consulta": arquivo.name}


# ------------------------------------------------------------------ resultado da busca


def _botoes_de_opcoes(opcoes: list[dict], prefixo: str, origem: str):
    atual = (molecula() or {}).get("smiles")
    cols = st.columns(2)
    for i, opcao in enumerate(opcoes):
        marcado = "✔️ " if atual == opcao["smiles"] else ""
        cols[i % 2].button(f"{marcado}{opcao['nome']}", key=f"{prefixo}_{i}", on_click=_escolher,
                           args=(opcao["smiles"], opcao.get("nome_molecula", opcao["nome"]), origem),
                           help=opcao.get("nota") or opcao["smiles"], width="stretch")


def _botoes_de_sugestoes(sugestoes: list[str]):
    if sugestoes:
        with st.container(horizontal=True, vertical_alignment="center"):
            st.caption("Você quis dizer:")
            for i, sugestao in enumerate(sugestoes):
                st.button(sugestao, key=f"sugestao_{i}", on_click=_buscar, args=(sugestao,))


def _mostrar_resultado(res: dict | None):
    if not res or res["status"] == "vazio":
        return
    status = res["status"]
    if status == "encontrado" and res.get("aviso"):
        st.info(res["aviso"], icon="ℹ️")
    elif status == "ambiguo":
        if res.get("fonte") == "formula":
            st.info(f"**{res['formula']}** é uma fórmula molecular com {len(res['opcoes'])} isômeros. Escolha um:", icon="🔀")
        else:
            st.info(f"“{res['consulta']}” corresponde a mais de uma substância. Escolha uma:", icon="❔")
        _botoes_de_opcoes(res["opcoes"], "opcao", res.get("fonte", ""))
    elif status == "mistura":
        st.info(f"**{res['nome']}** é uma mistura. Escolha um componente:", icon="🧴")
        componentes = sorted(res["componentes"], key=lambda c: c["id"] != res.get("principal"))
        _botoes_de_opcoes(componentes, "componente", "glossario")
    elif status == "formula":
        st.info(res["mensagem"] + " Uma fórmula não identifica uma única molécula: digite o nome da substância "
                "ou veja todos os isômeros.", icon="🔀")
        if res.get("total"):
            st.button(f"Ver os isômeros de {res['formula']}", on_click=_ir_para_isomeria, args=(res["formula"],), icon="🔀")
    elif status == "smiles_invalido":
        st.error(res["mensagem"], icon="🚫")
    elif status == "arquivo_invalido":
        st.error(f"Não foi possível ler a estrutura de {res['consulta']}.", icon="🚫")
    elif status == "pubchem_indisponivel":
        st.warning(f"“{res['consulta']}” não está no glossário e {res['mensagem'][0].lower()}{res['mensagem'][1:]} "
                   "Verifique a conexão ou digite o SMILES.", icon="📡")
        _botoes_de_sugestoes(res["sugestoes"])
    else:  # nao_encontrado
        st.warning(f"“{res['consulta']}” não foi encontrado no glossário nem no PubChem.", icon="🔍")
        _botoes_de_sugestoes(res["sugestoes"])


# ------------------------------------------------------------------ campo de busca


def _formulario_busca(destaque: bool):
    # O arquivo fica fora do formulário: o Streamlit não aceita callbacks de widgets dentro de formulários
    with st.form("form_busca", border=False, enter_to_submit=True):
        c_campo, c_botao = st.columns([5, 1], vertical_alignment="bottom")
        c_campo.text_input(
            "Nome, SMILES ou fórmula da molécula",
            key="campo_busca",
            placeholder=PLACEHOLDER,
            label_visibility="visible" if destaque else "collapsed",
            help="Nomes em português (ácido láctico), nomes comerciais (aspirina), nomes em inglês (lidocaine), "
                 "SMILES (CCO) ou fórmulas moleculares (C2H6O).",
        )
        c_botao.form_submit_button("Buscar", on_click=_buscar, type="primary", icon="🔎", width="stretch")


def _botao_arquivo(largura: str = "content"):
    with st.popover("Abrir arquivo", icon="📂", width=largura):
        st.file_uploader("Arquivo .mol, .sdf ou .pdb (ChemSketch, Avogadro, PubChem...)", type=["mol", "sdf", "pdb"],
                         key="arquivo_estrutura", on_change=_carregar_arquivo)


def renderizar_busca(destaque: bool = False):
    """
    Campo único de busca. destaque=True: versão grande, com título e explicação (tela inicial);
    destaque=False: barra compacta no topo da página.
    """
    if aviso := st.session_state.pop("aviso_busca", None):
        st.toast(aviso, icon="✅")

    if destaque:
        _formulario_busca(destaque=True)
        with st.container(horizontal=True, vertical_alignment="center"):
            _botao_arquivo()
            st.caption("O ChemioKit reconhece sozinho se você digitou um nome, um SMILES ou uma fórmula.")
    else:
        c_busca, c_arquivo = st.columns([6, 1.3], vertical_alignment="bottom")
        with c_busca:
            _formulario_busca(destaque=False)
        with c_arquivo:
            _botao_arquivo("stretch")

    _mostrar_resultado(st.session_state.get("resultado_busca"))


# ------------------------------------------------------------------ barra lateral


def renderizar_secao_entradas():
    """Barra lateral: histórico e exemplos (a busca fica na página)."""
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

    with st.expander("Exemplos"):
        for i, (nome, smiles) in enumerate(EXEMPLOS):
            st.button(nome, key=f"exemplo_{i}", on_click=_escolher, args=(smiles, nome, "exemplo"), type="tertiary")
