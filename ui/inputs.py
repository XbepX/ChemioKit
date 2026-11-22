import streamlit as st
from chemio_tools import resolver_nome
from chemio_tools.io_handlers import carregar_mol_de_texto

SMILES_INICIAL = "O=C[C@H](O)[C@@H](O)[C@H](O)[C@H](O)CO"

ROTULOS_FONTE = {
    "glossario": "glossário do ChemioKit",
    "cache": "PubChem (consulta guardada no computador)",
    "pubchem": "PubChem",
}


def _inicializar_estado():
    if "historico_smiles" not in st.session_state:
        st.session_state.historico_smiles = [
            SMILES_INICIAL,
            "CC(=O)O",
            "CCO",
            "c1ccccc1"
        ]
    if "campo_smiles" not in st.session_state:
        st.session_state.campo_smiles = SMILES_INICIAL
    if "nome_molecula" not in st.session_state:
        st.session_state.nome_molecula = ""
    if "resultado_busca" not in st.session_state:
        st.session_state.resultado_busca = None


# Callbacks: rodam antes de os widgets serem desenhados, por isso podem mudar o campo de SMILES.
def _aplicar_smiles(smiles: str, nome: str = ""):
    st.session_state.campo_smiles = smiles
    st.session_state.nome_molecula = nome


def _limpar_nome():
    st.session_state.nome_molecula = ""


def _ao_escolher_historico():
    _aplicar_smiles(st.session_state.hist_sel)


def _buscar_nome(nome: str | None = None):
    if nome is not None:  # sugestão clicada: vira o texto da busca
        st.session_state.campo_nome = nome
    res = resolver_nome(st.session_state.get("campo_nome", ""))
    st.session_state.resultado_busca = res
    if res["status"] == "encontrado":
        _aplicar_smiles(res["smiles"], res["nome"])


def _botoes_de_opcoes(opcoes: list[dict], prefixo: str):
    for i, opcao in enumerate(opcoes):
        marcado = "✔️ " if st.session_state.campo_smiles == opcao["smiles"] else ""
        st.button(
            f"{marcado}{opcao['nome']}",
            key=f"{prefixo}_{i}",
            on_click=_aplicar_smiles,
            args=(opcao["smiles"], opcao["nome"]),
            help=opcao.get("nota") or opcao["smiles"],
        )


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
        origem = ROTULOS_FONTE.get(res["fonte"], res["fonte"])
        st.success(f"**{res['nome']}** encontrado no {origem}: `{res['smiles']}`")
        if res.get("nota"):
            st.caption(res["nota"])

    elif status == "ambiguo":
        origem = ROTULOS_FONTE.get(res["fonte"], res["fonte"])
        st.info(f"“{res['consulta']}” corresponde a mais de uma substância ({origem}). Escolha uma:")
        _botoes_de_opcoes(res["opcoes"], "opcao")

    elif status == "mistura":
        st.info(f"**{res['nome']}** é uma mistura. Escolha o componente que deseja analisar:")
        if res.get("nota"):
            st.caption(res["nota"])
        componentes = sorted(res["componentes"], key=lambda c: c["id"] != res.get("principal"))
        _botoes_de_opcoes(componentes, "componente")

    elif status == "pubchem_indisponivel":
        st.warning(
            f"“{res['consulta']}” não está no glossário e {res['mensagem'][0].lower()}{res['mensagem'][1:]} "
            "Verifique a conexão ou digite o SMILES."
        )
        _botoes_de_sugestoes(res["sugestoes"])

    else:  # nao_encontrado
        st.warning(f"“{res['consulta']}” não foi encontrado no glossário nem no PubChem.")
        _botoes_de_sugestoes(res["sugestoes"])


def renderizar_secao_entradas() -> str:
    """Renderiza a busca por nome, a barra de entrada SMILES, o histórico e o carregador de arquivos."""
    _inicializar_estado()

    with st.form("form_busca_nome", border=False):
        col_nome, col_botao = st.columns([3, 1], vertical_alignment="bottom")
        with col_nome:
            st.text_input(
                "🔎 Buscar pelo nome:",
                key="campo_nome",
                placeholder="ex.: etanol, ácido tartárico, aspirina",
            )
        with col_botao:
            st.form_submit_button("Buscar", on_click=_buscar_nome)

    _mostrar_resultado_busca(st.session_state.resultado_busca)

    col_input, col_hist = st.columns([3, 1])

    with col_hist:
        st.selectbox(
            "📜 Histórico / Exemplos:",
            options=st.session_state.historico_smiles,
            index=0,
            key="hist_sel",
            on_change=_ao_escolher_historico,
        )

    with col_input:
        smiles_input = st.text_input(
            "Digite o SMILES da molécula:",
            key="campo_smiles",
            on_change=_limpar_nome,  # SMILES digitado à mão: o nome buscado deixa de valer
        )

    with st.expander("📂 Ou carregar arquivo de estrutura (.mol, .sdf, .pdb)"):
        arquivo_enviado = st.file_uploader(
            "Arraste o arquivo exportado (ChemSketch, Avogadro, etc.):",
            type=["mol", "sdf", "pdb"]
        )
        if arquivo_enviado is not None:
            conteudo_texto = arquivo_enviado.getvalue().decode("utf-8")
            extensao = arquivo_enviado.name.split(".")[-1].upper()

            smiles_extraido = carregar_mol_de_texto(conteudo_texto, formato=extensao)
            if smiles_extraido:
                smiles_input = smiles_extraido
                st.success(f"Estrutura importada do arquivo: `{arquivo_enviado.name}`")
            else:
                st.error("Não foi possível ler a estrutura deste arquivo.")

    if smiles_input and smiles_input not in st.session_state.historico_smiles:
        st.session_state.historico_smiles.insert(0, smiles_input)

    return smiles_input
