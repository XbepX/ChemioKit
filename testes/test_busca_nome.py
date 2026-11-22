"""Busca por nome: glossário -> cache -> PubChem (simulado) -> sugestões."""

import json
import time

import pytest

from chemio_tools import cache_nomes, glossario, identificar_centros_quirais, pubchem, resolver_nome, validar_smiles

L_TARTARICO = "[C@@H]([C@H](C(=O)O)O)(C(=O)O)O"
D_TARTARICO = "[C@H]([C@@H](C(=O)O)O)(C(=O)O)O"
MESO_TARTARICO = "[C@@H]([C@@H](C(=O)O)O)(C(=O)O)O"
TARTARICO_SEM_ESTEREO = "C(C(C(=O)O)O)(C(=O)O)O"


def _pubchem_simulado(monkeypatch, respostas: dict[str, list[dict]]):
    """Troca a consulta ao PubChem por um dicionário nome -> candidatos e conta as chamadas."""
    chamadas = []

    def falso(nome, maximo=5):
        chamadas.append(nome)
        return respostas.get(nome, [])

    monkeypatch.setattr(pubchem, "buscar_candidatos_por_nome", falso)
    return chamadas


def _registro(nome, smiles, cid, iupac):
    return {"nome_consultado": nome, "smiles": smiles, "cid": cid, "nome_iupac": iupac}


# ------------------------------------------------------------------ glossário


def test_glossario_carrega_sem_problemas():
    g = glossario.recarregar()
    assert g.problemas == []
    assert len(g.entradas) >= 68
    assert all(validar_smiles(e.smiles) for e in g.entradas.values() if e.tipo == "substancia")


@pytest.mark.parametrize(
    "nome, smiles, tipo_nome",
    [
        ("Etanol", "CCO", "nome IUPAC"),
        ("  ÁCIDO-etanoico  ", "CC(=O)O", "nome IUPAC"),  # maiúsculas, acento, hífen e espaços
        ("ácido acético", "CC(=O)O", "nome comum"),
        ("aspirina", "CC(=O)Oc1ccccc1C(=O)O", "nome comercial"),
        ("AAS", "CC(=O)Oc1ccccc1C(=O)O", "nome comum"),
    ],
)
def test_nome_do_glossario(nome, smiles, tipo_nome):
    r = resolver_nome(nome)
    assert (r["status"], r["fonte"], r["smiles"], r["tipo_nome"]) == ("encontrado", "glossario", smiles, tipo_nome)


def test_glossario_vem_antes_do_pubchem(monkeypatch):
    chamadas = _pubchem_simulado(monkeypatch, {"Etanol": [_registro("Etanol", "C", 1, "x")]})
    assert resolver_nome("Etanol")["smiles"] == "CCO"
    assert chamadas == []


def test_nome_ambiguo_mostra_as_quatro_formas_do_acido_tartarico():
    r = resolver_nome("ácido tartárico")
    assert r["status"] == "ambiguo"
    smiles = {o["smiles"] for o in r["opcoes"]}
    assert smiles == {L_TARTARICO, D_TARTARICO, MESO_TARTARICO, TARTARICO_SEM_ESTEREO}
    # Conferência cruzada com o motor de estereoquímica
    atividade = {s: identificar_centros_quirais(s)["atividade_optica"] for s in smiles}
    assert atividade == {
        L_TARTARICO: "Opticamente Ativa",
        D_TARTARICO: "Opticamente Ativa",
        MESO_TARTARICO: "Inativa (composto meso)",
        TARTARICO_SEM_ESTEREO: "Indefinida",
    }


def test_mistura_lista_componentes():
    r = resolver_nome("vinagre")
    assert r["status"] == "mistura"
    assert r["principal"] == "acido_etanoico"
    assert {c["smiles"] for c in r["componentes"]} == {"CC(=O)O", "O"}


# ------------------------------------------------------------------ PubChem (simulado)


def test_pubchem_um_registro_vai_para_o_cache_e_funciona_sem_internet(monkeypatch):
    _pubchem_simulado(monkeypatch, {"lidocaine": [_registro("lidocaine", "CCN(CC)CC(=O)Nc1c(C)cccc1C", 3676, "2-(diethylamino)-N-(2,6-dimethylphenyl)acetamide")]})
    r = resolver_nome("lidocaine")
    assert (r["status"], r["fonte"], r["cid"]) == ("encontrado", "pubchem", 3676)
    assert cache_nomes.obter("Lidocaine ")["cid"] == 3676

    def sem_rede(*a, **k):
        raise OSError("sem rede")

    monkeypatch.setattr(pubchem, "buscar_candidatos_por_nome", sem_rede)
    r2 = resolver_nome("LIDOCAINE")
    assert (r2["status"], r2["fonte"], r2["smiles"]) == ("encontrado", "cache", r["smiles"])


def test_pubchem_varios_registros_vira_escolha_e_nao_vai_para_o_cache(monkeypatch):
    _pubchem_simulado(monkeypatch, {"x": [_registro("x", "CCO", 1, "a"), _registro("x", "CCCO", 2, "b")]})
    r = resolver_nome("x")
    assert r["status"] == "ambiguo" and r["fonte"] == "pubchem"
    assert [o["smiles"] for o in r["opcoes"]] == ["CCO", "CCCO"]
    assert cache_nomes.obter("x") is None


def test_nome_inexistente_sem_sugestoes(monkeypatch):
    _pubchem_simulado(monkeypatch, {})
    r = resolver_nome("xyzabc")
    assert r == {"status": "nao_encontrado", "consulta": "xyzabc", "sugestoes": []}


def test_erro_de_digitacao_gera_sugestao(monkeypatch):
    _pubchem_simulado(monkeypatch, {})
    r = resolver_nome("etanoll")
    assert r["status"] == "nao_encontrado"
    assert r["sugestoes"] == ["etanol"]


def test_sem_internet_avisa_e_sugere():
    # conftest.py faz o PubChemPy levantar URLError, como num computador sem rede
    r = resolver_nome("etanoll")
    assert (r["status"], r["motivo"], r["sugestoes"]) == ("pubchem_indisponivel", "sem_conexao", ["etanol"])


def test_pubchem_lento_respeita_o_tempo_limite(monkeypatch):
    def lento(nome, maximo=5):
        time.sleep(3)
        return []

    monkeypatch.setattr(pubchem, "buscar_candidatos_por_nome", lento)
    inicio = time.perf_counter()
    r = resolver_nome("qualquer coisa", tempo_limite=0.3)
    assert time.perf_counter() - inicio < 1.5
    assert (r["status"], r["motivo"]) == ("pubchem_indisponivel", "tempo_esgotado")


def test_sem_pubchem_nao_consulta(monkeypatch):
    chamadas = _pubchem_simulado(monkeypatch, {})
    r = resolver_nome("lidocaine", usar_pubchem=False)
    assert r["status"] == "nao_encontrado" and chamadas == []


@pytest.mark.parametrize("nome", ["", "   ", None])
def test_nome_vazio(nome):
    assert resolver_nome(nome)["status"] == "vazio"


@pytest.mark.parametrize("nome", ["Etanol", "ácido tartárico", "vinagre", "etanoll", ""])
def test_resultado_vira_json(nome):
    json.dumps(resolver_nome(nome), ensure_ascii=False)


@pytest.mark.parametrize(
    "consulta",
    [
        lambda: pubchem.pcp.get_compounds("ethanol", "name"),
        lambda: pubchem.pcp.get_properties(["Title"], "C2H6O", "formula"),
    ],
    ids=["por_nome", "por_formula"],
)
def test_nenhum_teste_acessa_a_internet(consulta):
    # Garante que o conftest.py bloqueia todas as consultas, mesmo num computador com internet
    import urllib.error

    with pytest.raises(urllib.error.URLError, match="rede desativada nos testes"):
        consulta()
