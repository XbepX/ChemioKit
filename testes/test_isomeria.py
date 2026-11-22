"""
Ambiente de isomeria. Referências das contagens:
  - alcanos CnH2n+2 (1, 1, 1, 2, 3, 5, 9, 18 isômeros de C1 a C8): sequência clássica;
  - C4H10O = 7 (4 álcoois + 3 éteres), C5H12O = 14 (8 álcoois + 6 éteres), C3H9N = 4,
    C4H9Cl = 4, C3H6Cl2 = 4, C4H8 = 5, C5H10 = 10, C4H6 = 9, C3H4 = 3: contagens dos livros;
  - C6H6 = 217 isômeros constitucionais e C8H18 = 18 constitucionais / 24 estereoisômeros:
    Kerber et al. (MOLGEN), Univ. Bayreuth.
"""

import json

import pytest

from chemio_tools import (
    analisar_isomeria_espacial,
    buscar_nomes_isomeros,
    cache_nomes,
    classificar_par_isomeros,
    gerar_isomeros,
    interpretar_formula,
    pubchem,
)

# ------------------------------------------------------------------ fórmula


@pytest.mark.parametrize(
    "texto, formula, insaturacoes",
    [("C4H10O", "C4H10O", 0), ("C2H5Cl", "C2H5Cl", 0), ("C6H6", "C6H6", 4), ("H6C2O", "C2H6O", 0), ("CH3Br", "CH3Br", 0)],
)
def test_formula_valida(texto, formula, insaturacoes):
    r = interpretar_formula(texto)
    assert (r["valida"], r["formula"], r["insaturacoes"]) == (True, formula, insaturacoes)


@pytest.mark.parametrize("texto", ["", "c4h10o", "C4H11O", "XeF2", "H2"])
def test_formula_invalida(texto):
    assert interpretar_formula(texto)["valida"] is False


# ------------------------------------------------------------------ contagens


@pytest.mark.parametrize(
    "formula, total",
    [
        ("CH4", 1), ("C2H6", 1), ("C3H8", 1), ("C4H10", 2), ("C5H12", 3), ("C6H14", 5), ("C7H16", 9), ("C8H18", 18),
        ("C2H6O", 2), ("C3H8O", 3), ("C4H10O", 7), ("C5H12O", 14),
        ("C3H9N", 4), ("C4H9Cl", 4), ("C3H6Cl2", 4),
        ("C3H6", 2), ("C4H8", 5), ("C5H10", 10), ("C3H4", 3), ("C4H6", 9),
        ("C6H6", 217),
    ],
)
def test_numero_de_isomeros_constitucionais(formula, total):
    assert gerar_isomeros(formula, mostrar_todos=True)["total"] == total


def test_c4h10o_quatro_alcoois_e_tres_eteres():
    r = gerar_isomeros("C4H10O")
    assert {g: len(i) for g, i in r["grupos"].items()} == {"álcool": 4, "éter": 3}
    assert {i["smiles"] for i in r["isomeros"]} == {
        "CCCCO", "CCC(C)O", "CC(C)CO", "CC(C)(C)O", "CCCOC", "COC(C)C", "CCOCC",
    }


def test_estruturas_improvaveis_ficam_ocultas_por_padrao():
    r = gerar_isomeros("C4H6")
    assert (r["total"], r["ocultos"]) == (9, 4)
    assert {i["smiles"] for i in r["isomeros"]} == {"C#CCC", "CC#CC", "C=CC=C", "C=C1CC1", "C1C2CC12"}
    todos = gerar_isomeros("C4H6", mostrar_todos=True)
    motivos = {i["smiles"]: i["motivos_instabilidade"] for i in todos["isomeros"]}
    assert motivos["C1=CCC1"] == ["dupla em anel de 3 ou 4 átomos"]
    assert motivos["C=C=CC"] == ["duplas acumuladas C=C=C"]


def test_peroxido_oculto():
    r = gerar_isomeros("C2H6O2", mostrar_todos=True)
    assert "ligação O–O (peróxido)" in next(i for i in r["isomeros"] if i["smiles"] == "COOC")["motivos_instabilidade"]
    assert "COOC" not in {i["smiles"] for i in gerar_isomeros("C2H6O2")["isomeros"]}


def test_enol_continua_visivel():
    assert "C=CO" in {i["smiles"] for i in gerar_isomeros("C2H4O")["isomeros"]}


def test_limites():
    assert gerar_isomeros("C9H20")["status"] == "muito_grande"   # mais de 8 átomos pesados
    assert gerar_isomeros("C7H6O")["status"] == "muito_grande"   # mais de 6.000 estruturas
    assert gerar_isomeros("abc")["status"] == "formula_invalida"


def test_nome_do_glossario_e_classificacao_da_cadeia():
    iso = {i["smiles"]: i for i in gerar_isomeros("C4H10O")["isomeros"]}
    assert iso["CCOCC"]["nome"] == "Etoxietano"
    assert iso["CCOCC"]["descricao_cadeia"] == "aberta, normal, heterogênea, saturada"
    assert iso["CC(C)(C)O"]["descricao_cadeia"] == "aberta, ramificada, homogênea, saturada"


def test_resultado_vira_json():
    json.dumps(gerar_isomeros("C4H8O"), ensure_ascii=False)


# ------------------------------------------------------------------ isomeria espacial


@pytest.mark.parametrize("formula, total", [("C8H18", 24), ("C4H8", 6), ("C5H10", 13), ("C4H10O", 8)])
def test_total_com_estereoisomeros(formula, total):
    isomeros = gerar_isomeros(formula, mostrar_todos=True)["isomeros"]
    assert sum(analisar_isomeria_espacial(i["smiles"])["total_estereoisomeros"] for i in isomeros) == total


def test_espacial_dimetilciclopropano_meso_e_par_de_enantiomeros():
    r = analisar_isomeria_espacial("CC1CC1C")
    assert (r["geometrica"], r["total_estereoisomeros"], r["opticamente_ativos"], r["meso"]) == (True, 3, 2, 1)


def test_espacial_pent_2_eno_cis_trans():
    r = analisar_isomeria_espacial("CC=CCC")
    assert (r["duplas_cis_trans"], r["possivel_optica"]) == (1, False)
    assert sorted(c for e in r["estereoisomeros"] for c in e["configuracoes_duplas"]) == ["E", "Z"]


# ------------------------------------------------------------------ classificação de pares


@pytest.mark.parametrize(
    "a, b, tipo",
    [
        ("CCCCO", "CCC(C)O", "posição"),            # butan-1-ol × butan-2-ol
        ("CCCCO", "CC(C)CO", "cadeia"),             # normal × ramificada
        ("CCO", "COC", "função"),                   # álcool × éter
        ("CCC=O", "CC(C)=O", "função"),             # aldeído × cetona
        ("CC(=O)O", "COC=O", "função"),             # ácido × éster
        ("C#CCC", "C=CC=C", "função"),              # alcino × alcadieno
        ("C=CCC", "C1CCC1", "cadeia"),              # alceno × cicloalcano (aberta × fechada)
        ("CCCN", "CCNC", "cadeia"),                 # homogênea × heterogênea
        ("CCCOC", "COC(C)C", "cadeia"),             # éter: normal × ramificada
        ("CCCCCC", "CC(C)CCC", "cadeia"),           # hexano × 2-metilpentano
        ("CC(C)CCC", "CC(C)(C)CC", "cadeia"),       # ramos diferentes
        ("CC1CC1", "C1CCC1", "cadeia"),             # anéis de tamanhos diferentes
        ("CCC1CC1", "CC1CC1C", "cadeia"),           # etil × dois metil no anel
        ("C=CCC", "CC=CC", "posição"),              # but-1-eno × but-2-eno
        ("CC(C)CCC", "CCC(C)CC", "posição"),        # 2-metilpentano × 3-metilpentano
        ("CC(C)(C)CC", "CC(C)C(C)C", "posição"),    # 2,2- × 2,3-dimetilbutano
        ("Cc1ccccc1C", "Cc1cccc(C)c1", "posição"),  # o-xileno × m-xileno
        ("CC1(C)CC1", "CC1CC1C", "posição"),        # 1,1- × 1,2-dimetilciclopropano
        ("CCCCC(C)=O", "CCCC(=O)CC", "posição"),    # hexan-2-ona × hexan-3-ona
        ("CCCOC", "CCOCC", "metameria"),            # metoxipropano × etoxietano
        ("CCC(=O)OC", "CCOC(C)=O", "metameria"),    # propanoato de metila × etanoato de etila
        ("CN(C)C", "CCNC", "metameria"),            # trimetilamina × etilmetilamina
        ("CC=O", "C=CO", "tautomeria"),             # etanal × etenol
        ("CC(C)=O", "C=C(C)O", "tautomeria"),       # propanona × propen-2-ol
    ],
)
def test_isomeria_plana(a, b, tipo):
    r = classificar_par_isomeros(a, b)
    assert (r["relacao"], r["tipo"]) == ("plana", tipo)
    assert r["explicacao"]


def test_subtipos_de_tautomeria():
    assert classificar_par_isomeros("CC=O", "C=CO")["subtipo"] == "tautomeria aldoenólica"
    assert classificar_par_isomeros("CC(C)=O", "C=C(C)O")["subtipo"] == "tautomeria cetoenólica"


@pytest.mark.parametrize(
    "a, b, tipo, subtipo",
    [
        ("C/C=C/C", "C/C=C\\C", "geométrica", "cis-trans (E/Z)"),
        ("C[C@H]1C[C@@H]1C", "C[C@H]1C[C@H]1C", "geométrica", "cis-trans em ciclo"),
        ("C[C@H](O)CC", "C[C@@H](O)CC", "óptica", "enantiômeros"),
        ("O=C(O)[C@H](O)[C@H](O)C(=O)O", "O=C(O)[C@@H](O)[C@H](O)C(=O)O", "óptica", "diastereoisômeros"),
    ],
)
def test_isomeria_espacial_entre_pares(a, b, tipo, subtipo):
    r = classificar_par_isomeros(a, b)
    assert (r["relacao"], r["tipo"], r["subtipo"]) == ("espacial", tipo, subtipo)


def test_nao_isomeros_e_mesma_substancia():
    assert classificar_par_isomeros("CCO", "CCCO")["relacao"] == "não são isômeros"
    assert classificar_par_isomeros("CCO", "OCC")["relacao"] == "mesma substância"


# ------------------------------------------------------------------ nomes pelo PubChem (simulado)


def test_nomes_pubchem_vao_para_o_cache(monkeypatch):
    chamadas = []

    def falso(formula, maximo=2000):
        chamadas.append(formula)
        return {"LFQSCWFLJHTTHZ": {"cid": 702, "nome": "Ethanol"}}

    monkeypatch.setattr(pubchem, "buscar_nomes_por_formula", falso)
    r = buscar_nomes_isomeros("C2H6O")
    assert (r["status"], r["fonte"], r["nomes"]["LFQSCWFLJHTTHZ"]["cid"]) == ("ok", "pubchem", 702)
    r2 = buscar_nomes_isomeros("H6C2O")  # mesma fórmula escrita de outro jeito
    assert r2["fonte"] == "cache" and chamadas == ["C2H6O"]
    assert cache_nomes.obter_formula("C2H6O") == r["nomes"]


def test_chave_do_pubchem_bate_com_a_do_gerador():
    etanol = next(i for i in gerar_isomeros("C2H6O")["isomeros"] if i["smiles"] == "CCO")
    assert etanol["chave_conectividade"] == "LFQSCWFLJHTTHZ"  # 1º bloco do InChIKey do etanol


def test_nomes_sem_internet():
    r = buscar_nomes_isomeros("C2H6O")  # conftest.py simula computador sem rede
    assert (r["status"], r["motivo"], r["nomes"]) == ("pubchem_indisponivel", "sem_conexao", {})
