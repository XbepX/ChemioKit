"""
Modo Atividade: o estudante responde, o ChemioKit confere e explica.

Fluxo: escolher o tipo → responder → Verificar → ver o que acertou e errou →
tentar de novo ou ver a resposta com a explicação → próxima molécula.
Nada é gravado: respostas e acertos ficam só na sessão do navegador.
"""

import random

import streamlit as st

from chemio_tools import TIPOS_ATIVIDADE, corrigir_atividade, gerar_atividade, gerar_imagem_2d, moleculas_para_praticar

from .estado import definir_modo, definir_molecula, molecula
from .estilo import ESCALA_ROTULOS

ROTULO_HIB = {"sp3": "sp³", "sp2": "sp²", "sp": "sp"}


def _sair():
    definir_modo("explorar")


def _limpar_correcao():
    st.session_state.pop("correcao", None)
    st.session_state.pop("revelar", None)


def _sortear_molecula():
    tipo = st.session_state.atividade_tipo
    atual = (molecula() or {}).get("smiles")
    opcoes = [m for m in moleculas_para_praticar(tipo) if m["smiles"] != atual]
    if opcoes:
        escolha = random.choice(opcoes)
        definir_molecula(escolha["smiles"], escolha["nome"], origem="glossario")
    st.session_state.atividade_semente = random.randint(0, 10_000)
    _limpar_correcao()


def _nova_pergunta():
    st.session_state.atividade_semente = st.session_state.get("atividade_semente", 0) + 1
    _limpar_correcao()


def _ao_trocar_tipo():
    escolhido = st.session_state.get("w_atividade_tipo")
    if escolhido:
        st.session_state.atividade_tipo = escolhido
    _limpar_correcao()


def _obter_atividade(smiles: str) -> dict | None:
    tipo = st.session_state.atividade_tipo
    semente = st.session_state.get("atividade_semente", 0)
    chave = (tipo, smiles, semente)
    guardada = st.session_state.get("atividade")
    if not guardada or guardada.get("_chave") != chave:
        nova = gerar_atividade(tipo, smiles, semente=semente)
        st.session_state.atividade = {**nova, "_chave": chave} if nova else {"_chave": chave, "vazia": True}
        _limpar_correcao()
    a = st.session_state.atividade
    return None if a.get("vazia") else a


def _formulario(a: dict, prefixo: str):
    """Campos de resposta de cada tipo. Devolve a resposta no formato de corrigir_atividade."""
    tipo = a["tipo"]
    if tipo == "quirais":
        marcados = st.pills("Carbonos quirais", a["opcoes"] + ["Nenhum"], selection_mode="multi", key=f"{prefixo}_quirais")
        return [] if "Nenhum" in marcados else marcados
    if tipo == "hibridizacao":
        resposta = {}
        cols = st.columns(3)
        for k, item in enumerate(a["itens"]):
            with cols[k % 3]:
                escolha = st.segmented_control(item, ["sp3", "sp2", "sp"], format_func=ROTULO_HIB.get, key=f"{prefixo}_{item}")
                resposta[item] = escolha
        return resposta
    if tipo == "sigma_pi":
        c1, c2 = st.columns(2)
        sigma = c1.number_input("Ligações σ", min_value=0, step=1, value=None, key=f"{prefixo}_sigma")
        pi = c2.number_input("Ligações π", min_value=0, step=1, value=None, key=f"{prefixo}_pi")
        return {"sigma": sigma, "pi": pi}
    if tipo == "cadeia":
        resposta = {}
        for p in a["perguntas"]:
            resposta[p["atributo"]] = st.segmented_control(p["pergunta"], p["opcoes"], key=f"{prefixo}_{p['atributo']}")
        return resposta
    return st.radio("Tipo de isomeria", a["opcoes"], index=None, horizontal=True, key=f"{prefixo}_iso")


def _texto_item(a: dict, item: dict, revelar: bool) -> str:
    sinal = "✅" if item["correto"] else "❌"
    tipo = a["tipo"]
    if tipo == "quirais":
        if item["correto"]:
            return f"{sinal} {item['item']}: {'é quiral' if item['esperado'] else 'não é quiral'}"
        return f"{sinal} {item['item']}: " + ("faltou marcar" if item["esperado"] else "não é quiral")
    nome = {"sigma": "σ", "pi": "π"}.get(item["item"], item["item"])
    dado = ROTULO_HIB.get(item["resposta"], item["resposta"])
    texto = f"{sinal} {nome}: sua resposta: {dado if dado is not None else '—'}"
    if revelar and not item["correto"]:
        texto += f" · correto: {ROTULO_HIB.get(item['esperado'], item['esperado'])}"
    return texto


def renderizar_modo_atividade(smiles: str):
    m = molecula()
    c_titulo, c_sair = st.columns([6, 1], vertical_alignment="center")
    c_titulo.markdown("## ✏️ Atividade")
    c_sair.button("Sair da atividade", on_click=_sair, width="stretch")

    st.session_state.w_atividade_tipo = st.session_state.atividade_tipo
    st.pills("Tipo de atividade", list(TIPOS_ATIVIDADE), format_func=TIPOS_ATIVIDADE.get, key="w_atividade_tipo",
             on_change=_ao_trocar_tipo)

    a = _obter_atividade(smiles)
    c_mol, c_botao = st.columns([4, 1], vertical_alignment="center")
    c_mol.markdown(f"Molécula: **{m['nome'] or smiles}**")
    c_botao.button("🎲 Outra molécula", on_click=_sortear_molecula, width="stretch")

    if a is None:
        st.info("Esta molécula não serve para este tipo de atividade (por exemplo: sem carbono, ou grande demais "
                "para gerar isômeros). Clique em **Outra molécula**.", icon="ℹ️")
        return

    prefixo = f"at_{abs(hash(a['_chave']))}"
    col_img, col_resp = st.columns([1, 1.2], gap="large")
    with col_img:
        if a["tipo"] == "isomeria":
            ia, ib = st.columns(2)
            ia.image(gerar_imagem_2d(a["smiles"], espessura_linha=2, tamanho_fonte=14), caption="Estrutura A")
            ib.image(gerar_imagem_2d(a["smiles_b"], espessura_linha=2, tamanho_fonte=14), caption="Estrutura B")
        else:
            mostrar_h = st.toggle("Mostrar hidrogênios", value=a["tipo"] == "sigma_pi", key=f"{prefixo}_hs")
            st.image(gerar_imagem_2d(a["smiles"], mostrar_indices=True, mostrar_h=mostrar_h, espessura_linha=2, tamanho_fonte=14, escala_rotulos=ESCALA_ROTULOS))

    with col_resp:
        st.markdown(f"**{a['enunciado']}**")
        with st.form(f"{prefixo}_form", border=False):
            resposta = _formulario(a, prefixo)
            verificar = st.form_submit_button("Verificar", type="primary")
        with st.popover("Dica", icon="💡"):
            st.markdown(a["dica"])

        if verificar:
            st.session_state.correcao = corrigir_atividade(a, resposta)
            st.session_state.revelar = False

        correcao = st.session_state.get("correcao")
        if correcao:
            revelar = st.session_state.get("revelar") or correcao["correto"]
            if correcao["correto"]:
                st.success("Correto! 🎉", icon="✅")
            else:
                st.error("Ainda não. Veja o que precisa revisar:", icon="🔁")
            if a["tipo"] != "isomeria":
                for item in correcao["itens"]:
                    st.markdown(_texto_item(a, item, revelar))
            if not revelar:
                c1, c2 = st.columns(2)
                c1.button("Tentar de novo", on_click=_limpar_correcao, width="stretch")
                if c2.button("Ver resposta e explicação", width="stretch"):
                    st.session_state.revelar = True
                    st.rerun()
            else:
                with st.container(border=True):
                    st.markdown("**Explicação**")
                    if a["tipo"] == "isomeria" and not correcao["correto"]:
                        st.markdown(f"Resposta: **{a['resposta']}**")
                    for linha in correcao["explicacao"]:
                        st.markdown(f"- {linha}")
                c1, c2 = st.columns(2)
                if a["tipo"] == "isomeria":
                    c1.button("Outro par de isômeros", on_click=_nova_pergunta, width="stretch")
                c2.button("Próxima molécula", on_click=_sortear_molecula, type="primary", width="stretch")
