"""Explicações didáticas ("Por quê?") e motor de atividades."""

import json

import pytest

from chemio_tools import (
    TIPOS_ATIVIDADE,
    corrigir_atividade,
    explicar_atividade_optica,
    explicar_cadeia,
    explicar_carbonos_quirais,
    explicar_hibridizacao,
    explicar_ligacoes_sigma_pi,
    gerar_atividade,
    moleculas_para_praticar,
    obter_enantiomero,
)

# ------------------------------------------------------------------ explicações


@pytest.mark.parametrize(
    "smiles, ligantes",
    [
        ("CC(O)C(=O)O", ["H", "CH₃", "OH", "COOH"]),                        # ácido láctico
        ("C[C@H](N)C(=O)O", ["H", "CH₃", "NH₂", "COOH"]),                   # alanina
        ("N[C@@H](Cc1ccccc1)C(=O)O", ["H", "NH₂", "CH₂C₆H₅", "COOH"]),      # fenilalanina
        ("CC(Cl)C(=O)OC", ["H", "CH₃", "Cl", "COOCH₃"]),
    ],
)
def test_ligantes_do_carbono_quiral(smiles, ligantes):
    centros = explicar_carbonos_quirais(smiles)["centros"]
    assert len(centros) == 1 and sorted(centros[0]["ligantes"]) == sorted(ligantes)


def test_ligantes_condensados_no_acido_tartarico():
    centros = explicar_carbonos_quirais("OC(=O)C(O)C(O)C(=O)O")["centros"]
    assert sorted(centros[0]["ligantes"]) == sorted(["H", "OH", "COOH", "CH(OH)COOH"])


def test_ligantes_em_anel_indicam_o_sentido():
    centros = explicar_carbonos_quirais("CC1CC1C")["centros"]
    assert sum(lig.startswith("anel, sentido de") for lig in centros[0]["ligantes"]) == 2


def test_sem_carbono_quiral():
    r = explicar_carbonos_quirais("CCO")
    assert r["centros"] == [] and "não tem carbono quiral" in r["texto"]


@pytest.mark.parametrize(
    "smiles, palavra",
    [
        ("C[C@@H](O)C(=O)O", "não é igual à sua imagem especular"),
        ("O=C(O)[C@H](O)[C@H](O)C(=O)O", "simetria interna"),
        ("CCO", "aquiral"),
        ("CCC(C)O", "sem configuração definida"),
    ],
)
def test_explicacao_da_atividade_optica(smiles, palavra):
    assert palavra in explicar_atividade_optica(smiles)["texto"]


def test_enantiomero():
    assert obter_enantiomero("C[C@@H](O)C(=O)O") == "C[C@H](O)C(=O)O"
    assert obter_enantiomero("O=C(O)[C@H](O)[C@H](O)C(=O)O") is None  # meso: a imagem é a mesma
    assert obter_enantiomero("CCO") is None


def test_explicacao_da_hibridizacao_segue_a_regra():
    textos = {c["rotulo"]: c["texto"] for c in explicar_hibridizacao("C#CC=CC")["carbonos"]}
    assert textos == {
        "C1": "C1 faz uma ligação tripla: sp.",
        "C2": "C2 faz uma ligação tripla: sp.",
        "C3": "C3 faz uma ligação dupla: sp².",
        "C4": "C4 faz uma ligação dupla: sp².",
        "C5": "C5 faz só ligações simples: sp³.",
    }
    assert "duas ligações duplas" in explicar_hibridizacao("C=C=C")["carbonos"][1]["texto"]


def test_explicacao_sigma_pi_do_benzeno():
    assert explicar_ligacoes_sigma_pi("c1ccccc1")["texto"] == (
        "Simples: 9 (9 σ). Duplas: 3 (3 σ + 3 π). Triplas: 0 (0 σ + 0 π). Total: 12 σ e 3 π."
    )


@pytest.mark.parametrize(
    "smiles, classificacao",
    [
        ("CC(C)CO", ["aberta", "ramificada", "homogênea", "saturada"]),
        ("CCOCC", ["aberta", "normal", "heterogênea", "saturada"]),
        ("Cc1ccccc1", ["fechada (aromática)", "ramificada", "homogênea", "insaturada"]),
        ("C1CCCCC1", ["fechada", "não ramificada", "homogênea", "saturada"]),
        ("CCCO", ["aberta", "normal", "homogênea", "saturada"]),  # OH na ponta não torna heterogênea
    ],
)
def test_explicacao_da_cadeia(smiles, classificacao):
    assert list(explicar_cadeia(smiles)["classificacao"].values()) == classificacao


# ------------------------------------------------------------------ atividades


def test_atividade_quirais_corrige_cada_carbono():
    a = gerar_atividade("quirais", "OC(=O)C(O)C(O)C(=O)O")
    assert (a["opcoes"], a["resposta"]) == (["C1", "C2", "C3", "C4"], ["C2", "C3"])
    assert corrigir_atividade(a, ["C2", "C3"])["correto"] is True
    r = corrigir_atividade(a, ["C2", "C4"])
    assert r["correto"] is False
    assert {i["item"]: i["correto"] for i in r["itens"]} == {"C2": True, "C3": False, "C4": False}


def test_atividade_quirais_nenhum():
    assert corrigir_atividade(gerar_atividade("quirais", "CCO"), [])["correto"] is True


def test_atividade_hibridizacao():
    a = gerar_atividade("hibridizacao", "C#CC=CC")
    assert a["resposta"] == {"C1": "sp", "C2": "sp", "C3": "sp2", "C4": "sp2", "C5": "sp3"}
    r = corrigir_atividade(a, {**a["resposta"], "C5": "sp2"})
    assert r["correto"] is False and [i["item"] for i in r["itens"] if not i["correto"]] == ["C5"]


def test_atividade_hibridizacao_limita_carbonos():
    a = gerar_atividade("hibridizacao", "C" * 20)
    assert len(a["itens"]) == 12


def test_atividade_sigma_pi():
    a = gerar_atividade("sigma_pi", "C#C")
    assert a["resposta"] == {"sigma": 3, "pi": 2}
    assert corrigir_atividade(a, {"sigma": 3, "pi": 2})["correto"]
    assert not corrigir_atividade(a, {"sigma": 3, "pi": None})["correto"]


def test_atividade_cadeia():
    a = gerar_atividade("cadeia", "Cc1ccccc1")
    assert a["resposta"] == {"aberta/fechada": "fechada", "normal/ramificada": "ramificada",
                             "homogênea/heterogênea": "homogênea", "saturada/insaturada": "insaturada"}


def test_atividade_isomeria_com_par_dado_e_sorteado():
    a = gerar_atividade("isomeria", "CCCCO", "CCC(C)O")
    assert (a["resposta"], a["opcoes"]) == ("posição", ["função", "cadeia", "posição", "metameria", "tautomeria"])
    assert corrigir_atividade(a, "posição")["correto"]
    b = gerar_atividade("isomeria", "C/C=C/C", "C/C=C\\C")
    assert (b["resposta"], b["opcoes"]) == ("geométrica", ["geométrica", "óptica"])
    s1 = gerar_atividade("isomeria", "CCCCO", semente=1)
    assert s1["smiles_b"] != "CCCCO" and s1["resposta"] in s1["opcoes"]
    assert gerar_atividade("isomeria", "CCCCO", semente=1)["smiles_b"] == s1["smiles_b"]  # mesma semente, mesmo par


@pytest.mark.parametrize("tipo", list(TIPOS_ATIVIDADE))
def test_atividade_vira_json_e_tem_dica(tipo):
    a = gerar_atividade(tipo, "CC(O)C(=O)O")
    json.dumps(a, ensure_ascii=False)
    assert a["dica"] and a["explicacao"]


def test_atividade_invalida():
    assert gerar_atividade("quirais", "O") is None       # sem carbono
    assert gerar_atividade("xyz", "CCO") is None
    assert gerar_atividade("isomeria", "C" * 12) is None  # grande demais para o gerador


@pytest.mark.parametrize("tipo", list(TIPOS_ATIVIDADE))
def test_moleculas_para_praticar_servem_para_a_atividade(tipo):
    lista = moleculas_para_praticar(tipo)
    assert len(lista) >= 10
    assert all(gerar_atividade(tipo, m["smiles"], semente=0) is not None for m in lista)
