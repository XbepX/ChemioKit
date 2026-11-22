"""
Aba Propriedades: composição, ligações, cadeia, anéis, semelhança com fármacos e tautômeros.
Com "Detalhes técnicos" ligado, mostra a tabela completa, os métodos e o JSON para baixar.
"""

import json

import pandas as pd
import rdkit
import streamlit as st

from chemio_tools import (
    analisar_aneis,
    analisar_hibridizacao_e_ligacoes,
    avaliar_lipinski,
    calcular_qed,
    explicar_cadeia,
    explicar_hibridizacao,
    explicar_ligacoes_sigma_pi,
    gerar_imagem_2d,
    gerar_tautomeros,
    obter_esqueleto_murcko,
    obter_identificadores,
    obter_propriedades_basicas,
)

from .estilo import cabecalho, formula_bonita, num

NOMES_CRITERIOS = {
    "massa_molecular": ("Massa molecular", "g/mol", "≤ 500"),
    "logp": ("LogP (lipofilicidade)", "", "≤ 5"),
    "doadores_h": ("Doadores de ligação de H (N–H, O–H)", "", "≤ 5"),
    "aceitadores_h": ("Aceitadores de ligação de H (N, O)", "", "≤ 10"),
}

METODOS = """
| Grandeza | Método (RDKit {versao}) |
|---|---|
| Massa molecular | `Descriptors.MolWt` (massas atômicas médias) |
| LogP | `Descriptors.MolLogP` (Crippen, 1999) |
| TPSA | `Descriptors.TPSA` (Ertl, 2000) |
| Doadores/aceitadores de H (Lipinski) | `CalcNumLipinskiHBD/HBA`: ligações N–H e O–H; átomos de N e O (Lipinski, 1997) |
| Ligações rotacionáveis | `Descriptors.NumRotatableBonds` |
| QED | `QED.qed` (Bickerton et al., 2012) |
| Hibridização | `Atom.GetHybridization` |
| σ e π | contagem após `Kekulize` com H explícitos |
| Anéis | `RingInfo` (menor conjunto de anéis) e aromaticidade do RDKit |
| Esqueleto | `MurckoScaffold` (Bemis e Murcko, 1996) |
| Tautômeros | `rdMolStandardize.TautomerEnumerator` |
| Alertas | `FilterCatalog`: Brenk (2008), PAINS (Baell e Holloway, 2010), NIH (Jadhav et al., J. Med. Chem. 53) |
"""


def _secao(titulo: str):
    st.markdown(f"#### {titulo}")


def renderizar_aba_propriedades(smiles_input: str):
    dados = obter_propriedades_basicas(smiles_input)
    if not dados:
        return

    # Métricas principais
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Fórmula molecular", formula_bonita(dados["formula"]))
    c2.metric("Massa molecular", f"{num(dados['massa_molecular'])} g/mol")
    c3.metric("LogP", num(dados["logp"]), help="Lipofilicidade: quanto maior, mais a substância prefere gordura a água (Crippen).")
    c4.metric("TPSA", f"{num(dados['tpsa'])} Å²", help="Área de superfície polar topológica (Ertl).")

    _secao("Composição (com H explícitos)")
    elementos = dados["contagem_elementos"]
    cols = st.columns(max(len(elementos), 1))
    for col, (simbolo, n) in zip(cols, elementos.items()):
        col.metric(f"Átomos de {simbolo}", n)

    st.divider()
    esquerda, direita = st.columns(2, gap="large")

    with esquerda:
        hib = analisar_hibridizacao_e_ligacoes(smiles_input)
        c = hib["contagem_hibridizacao"]
        exp_h = explicar_hibridizacao(smiles_input)
        exp_s = explicar_ligacoes_sigma_pi(smiles_input)
        cabecalho("Ligações e hibridização", [f"**Regra:** {exp_h['regra']}"] + [f"- {x['texto']}" for x in exp_h["carbonos"]]
                  + [f"**σ e π:** {exp_s['regra']}", exp_s["texto"]])
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("C sp³", c["sp3"])
        m2.metric("C sp²", c["sp2"])
        m3.metric("C sp", c["sp"])
        m4.metric("σ", hib["sigma"])
        m5.metric("π", hib["pi"])

        cadeia = explicar_cadeia(smiles_input)
        cabecalho("Cadeia carbônica", [f"- **{i['valor'].capitalize()}**: {i['motivo']}" for i in cadeia["itens"]])
        st.markdown(" · ".join(f"**{i['valor']}**" for i in cadeia["itens"]))

        aneis = analisar_aneis(smiles_input)
        _secao("Anéis e aromaticidade")
        if aneis["total"]:
            st.markdown(f"**{aneis['total']}** anel(éis), **{aneis['aromaticos']}** aromático(s).")
            for k, a in enumerate(aneis["aneis"], 1):
                hetero = f", com {', '.join(a['heteroatomos'])}" if a["heteroatomos"] else ""
                st.markdown(f"- Anel {k}: {a['tamanho']} átomos{hetero} — {'aromático' if a['aromatico'] else 'não aromático'}")
            murcko = obter_esqueleto_murcko(smiles_input)
            if murcko["tem_anel"]:
                st.caption("Esqueleto de Murcko (anéis e as cadeias que os ligam, sem cadeias laterais):")
                st.image(gerar_imagem_2d(murcko["esqueleto"], espessura_linha=2, tamanho_fonte=14), width=200)
        else:
            st.caption("A molécula não tem anéis.")

    with direita:
        lip = avaliar_lipinski(smiles_input)
        cabecalho("Semelhança com fármacos", [
                "**Regra dos 5 de Lipinski (1997):** substâncias tomadas por via oral costumam ter massa ≤ 500, "
                "LogP ≤ 5, até 5 doadores e até 10 aceitadores de ligação de hidrogênio. Mais de uma violação "
                "indica que a absorção pelo intestino tende a ser baixa.",
                "**QED** (0 a 1) resume o quanto as propriedades se parecem com as de fármacos orais conhecidos.",
                "São regras práticas da química medicinal, não avaliam se a substância funciona ou é segura.",
        ])
        tabela = pd.DataFrame([
            {"Critério": NOMES_CRITERIOS[c["criterio"]][0], "Valor": num(c["valor"]),
             "Limite": NOMES_CRITERIOS[c["criterio"]][2], "": "✅" if c["ok"] else "❌"}
            for c in lip["criterios"]
        ])
        st.dataframe(tabela, hide_index=True, width="stretch")
        veredito = "atende" if lip["aprovado"] else "não atende"
        st.markdown(f"**{lip['violacoes']} violação(ões)**: {veredito} à Regra dos 5. "
                    f"Ligações rotacionáveis: {lip['ligacoes_rotacionaveis']}.")
        q = calcular_qed(smiles_input)
        st.metric("QED", num(q["qed"]), help="0 = nada parecido com fármacos orais; 1 = muito parecido.")
        st.progress(q["qed"])

        taut = gerar_tautomeros(smiles_input)
        _secao("Tautômeros")
        if taut["total"] > 1:
            st.caption(f"{taut['total']} formas encontradas pelo RDKit (a primeira é a forma padronizada, não necessariamente a predominante)."
                       + (" A lista foi cortada no limite." if taut["limite_atingido"] else ""))
            cols = st.columns(3)
            for k, s in enumerate(taut["tautomeros"][:9]):
                with cols[k % 3]:
                    st.image(gerar_imagem_2d(s, espessura_linha=2, tamanho_fonte=14))
                    st.code(s, language="text", wrap_lines=True)
        else:
            st.caption("Nenhum outro tautômero encontrado.")

    if st.session_state.get("tecnico"):
        st.divider()
        _secao("Detalhes técnicos")
        completo = {
            "smiles": smiles_input,
            "identificadores": obter_identificadores(smiles_input),
            "propriedades": dados,
            "lipinski": lip,
            "qed": q,
            "hibridizacao_e_ligacoes": hib,
            "cadeia": cadeia["classificacao"],
            "aneis": aneis,
            "esqueleto_murcko": obter_esqueleto_murcko(smiles_input),
            "tautomeros": taut,
        }
        linhas = [
            ("Massa molecular (g/mol)", dados["massa_molecular"]), ("LogP (Crippen)", dados["logp"]),
            ("TPSA (Å²)", dados["tpsa"]), ("Doadores de H (Lipinski)", lip["doadores_h"]),
            ("Aceitadores de H (Lipinski)", lip["aceitadores_h"]), ("Ligações rotacionáveis", lip["ligacoes_rotacionaveis"]),
            ("Violações da Regra dos 5", lip["violacoes"]), ("QED", q["qed"]), ("Área polar (QED)", q["propriedades"]["area_polar"]),
            ("Anéis", aneis["total"]), ("Anéis aromáticos", aneis["aromaticos"]), ("C sp³", c["sp3"]),
            ("C sp²", c["sp2"]), ("C sp", c["sp"]), ("Ligações σ", hib["sigma"]), ("Ligações π", hib["pi"]),
            ("Tautômeros", taut["total"]),
        ]
        tabela = pd.DataFrame(linhas, columns=["Descritor", "Valor"])
        st.dataframe(tabela, hide_index=True, width="stretch")
        c_json, c_csv = st.columns(2)
        c_json.download_button("⬇️ Todos os resultados (.json)", json.dumps(completo, ensure_ascii=False, indent=2),
                               file_name="chemiokit_propriedades.json", mime="application/json")
        c_csv.download_button("⬇️ Tabela de descritores (.csv)", tabela.to_csv(index=False).encode("utf-8-sig"),
                              file_name="chemiokit_descritores.csv", mime="text/csv")
        with st.expander("Métodos e versões"):
            st.markdown(METODOS.format(versao=rdkit.__version__))
