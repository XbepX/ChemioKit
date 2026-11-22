"""
Ferramentas novas do motor (tarefa 2). Os valores esperados foram conferidos à mão
(contagem de átomos e ligações) sempre que possível; os que dependem de um modelo
numérico do RDKit (Tanimoto, QED) estão indicados como valores de referência.
"""

import json

import pytest

import chemio_tools as ct

# ------------------------------------------------------------------ hibridização e σ/π


@pytest.mark.parametrize(
    "smiles, sp3, sp2, sp, sigma, pi",
    [
        ("c1ccccc1", 0, 6, 0, 12, 3),   # benzeno: 6 C–C + 6 C–H; 3 duplas na forma de Kekulé
        ("C#C", 0, 0, 2, 3, 2),         # etino: C≡C (1σ + 2π) + 2 C–H
        ("C=C", 0, 2, 0, 5, 1),         # eteno
        ("CC", 2, 0, 0, 7, 0),          # etano: C–C + 6 C–H
        ("O=C=O", 0, 0, 1, 2, 2),       # CO2: carbono sp com duas duplas
        ("CC#N", 1, 0, 1, 5, 2),        # acetonitrila
        ("C=C=C", 0, 2, 1, 6, 2),       # propadieno (aleno): carbono central sp
        ("CC(=O)O", 1, 1, 0, 7, 1),     # ácido acético
    ],
)
def test_hibridizacao_e_ligacoes(smiles, sp3, sp2, sp, sigma, pi):
    r = ct.analisar_hibridizacao_e_ligacoes(smiles)
    assert r["contagem_hibridizacao"] == {"sp3": sp3, "sp2": sp2, "sp": sp}
    assert (r["sigma"], r["pi"]) == (sigma, pi)


def test_hibridizacao_por_carbono_segue_a_numeracao():
    r = ct.analisar_hibridizacao_e_ligacoes("C=C=C")
    assert [(c["rotulo_carbono"], c["hibridizacao"]) for c in r["carbonos"]] == [("C1", "sp2"), ("C2", "sp"), ("C3", "sp2")]


def test_benzeno_kekulizado_tem_3_simples_e_3_duplas_no_anel():
    r = ct.analisar_hibridizacao_e_ligacoes("c1ccccc1")
    assert r["ligacoes"] == {"simples": 9, "duplas": 3, "triplas": 0}  # 3 C–C + 6 C–H simples


# ------------------------------------------------------------------ identificadores


def test_identificadores_do_etanol():
    r = ct.obter_identificadores("OCC")
    assert r == {
        "smiles_canonico": "CCO",
        "inchi": "InChI=1S/C2H6O/c1-2-3/h3H,2H2,1H3",
        "inchikey": "LFQSCWFLJHTTHZ-UHFFFAOYSA-N",
    }


def test_inchikey_distingue_enantiomeros():
    r = ct.obter_identificadores("C[C@@H](O)CC")["inchikey"]
    s = ct.obter_identificadores("C[C@H](O)CC")["inchikey"]
    assert r != s and r[:14] == s[:14]  # mesmo esqueleto (1º bloco), estereoquímica diferente


# ------------------------------------------------------------------ Lipinski e QED


def test_lipinski_aspirina():
    r = ct.avaliar_lipinski("CC(=O)Oc1ccccc1C(=O)O")
    assert r["doadores_h"] == 1       # um O–H
    assert r["aceitadores_h"] == 4    # quatro átomos de O
    assert r["massa_molecular"] == pytest.approx(180.16, abs=0.01)
    assert (r["violacoes"], r["aprovado"]) == (0, True)


def test_lipinski_doadores_contam_ligacoes_nh():
    assert ct.avaliar_lipinski("NCCN")["doadores_h"] == 4  # dois NH2 = quatro N–H


def test_lipinski_duas_violacoes_reprova():
    r = ct.avaliar_lipinski("C" * 40)  # C40H82: 563,1 g/mol e muito lipofílico
    assert r["massa_molecular"] == pytest.approx(563.1, abs=0.1)
    assert [c["criterio"] for c in r["criterios"] if not c["ok"]] == ["massa_molecular", "logp"]
    assert (r["violacoes"], r["aprovado"]) == (2, False)


@pytest.mark.parametrize("smiles, rotacionaveis", [("CCCC", 1), ("CCCCC", 2), ("CCO", 0)])
def test_ligacoes_rotacionaveis(smiles, rotacionaveis):
    assert ct.avaliar_lipinski(smiles)["ligacoes_rotacionaveis"] == rotacionaveis


def test_qed_aspirina():
    r = ct.calcular_qed("CC(=O)Oc1ccccc1C(=O)O")
    assert r["qed"] == 0.55  # valor de referência do RDKit 2026.3.5
    assert r["propriedades"]["aneis_aromaticos"] == 1


# ------------------------------------------------------------------ alertas estruturais


def test_alertas_sao_apresentados_como_alertas():
    r = ct.buscar_alertas_estruturais("CCO")
    assert r["total"] == 0
    assert "não são uma previsão de toxicidade" in r["aviso"].lower()


def test_alerta_de_aldeido_nos_catalogos_brenk_e_nih():
    r = ct.buscar_alertas_estruturais("CC=O")
    assert {(a["nome"], a["catalogo"]) for a in r["alertas"]} == {("aldehyde", "Brenk"), ("aldehyde", "NIH")}


def test_alerta_pains_rodanina_com_indices():
    r = ct.buscar_alertas_estruturais("O=C1C(=Cc2ccccc2)SC(=S)N1")
    pains = [a for a in r["alertas"] if a["catalogo"].startswith("PAINS")]
    assert pains and pains[0]["indices"]


# ------------------------------------------------------------------ anéis, Murcko, tautômeros


@pytest.mark.parametrize(
    "smiles, total, aromaticos, hetero",
    [
        ("c1ccc2ccccc2c1", 2, 2, []),        # naftaleno
        ("c1ccncc1", 1, 1, ["N"]),           # piridina
        ("C1CCCCC1", 1, 0, []),              # ciclo-hexano
        ("c1ccc2c(c1)CCC2", 2, 1, []),       # indano: benzeno + anel de 5 saturado
        ("CCO", 0, 0, []),
    ],
)
def test_aneis(smiles, total, aromaticos, hetero):
    r = ct.analisar_aneis(smiles)
    assert (r["total"], r["aromaticos"]) == (total, aromaticos)
    assert sorted(h for a in r["aneis"] for h in a["heteroatomos"]) == hetero


@pytest.mark.parametrize(
    "smiles, esqueleto",
    [
        ("CC(C)Cc1ccc(cc1)C(C)C(=O)O", "c1ccccc1"),     # ibuprofeno
        ("c1ccc(cc1)Cc1ccncc1", "c1ccc(Cc2ccncc2)cc1"),  # a ponte CH2 entre os anéis fica
        ("CCO", ""),
    ],
)
def test_esqueleto_murcko(smiles, esqueleto):
    assert ct.obter_esqueleto_murcko(smiles)["esqueleto"] == esqueleto


def test_tautomeros_ceto_enol_da_acetona():
    r = ct.gerar_tautomeros("CC(C)=O")
    assert set(r["tautomeros"]) == {"CC(C)=O", "C=C(C)O"}
    assert r["tautomeros"][0] == r["canonico"]


def test_tautomeros_hidroxipiridina_inclui_piridona():
    assert "O=c1cccc[nH]1" in ct.gerar_tautomeros("Oc1ccccn1")["tautomeros"]


def test_sem_tautomeros():
    assert ct.gerar_tautomeros("CCO")["total"] == 1


# ------------------------------------------------------------------ comparação


def test_comparar_mesma_molecula_escrita_diferente():
    r = ct.comparar_moleculas("CCO", "OCC")
    assert (r["tanimoto"], r["identicas"]) == (1.0, True)


def test_mcs_etanol_propanol():
    r = ct.comparar_moleculas("CCO", "CCCO")
    assert 0 < r["tanimoto"] < 1
    assert (r["mcs"]["num_atomos"], r["mcs"]["indices_b"]) == (3, [1, 2, 3])  # C–C–O do propan-1-ol


def test_mcs_benzeno_tolueno_e_o_anel():
    r = ct.comparar_moleculas("c1ccccc1", "Cc1ccccc1")
    assert (r["mcs"]["num_atomos"], r["mcs"]["completa"]) == (6, True)
    assert 0 not in r["mcs"]["indices_b"]  # a metila (átomo 0) não faz parte


# ------------------------------------------------------------------ JSON e entradas inválidas

FUNCOES_DE_UM_SMILES = [
    ct.analisar_hibridizacao_e_ligacoes,
    ct.obter_identificadores,
    ct.avaliar_lipinski,
    ct.calcular_qed,
    ct.buscar_alertas_estruturais,
    ct.analisar_aneis,
    ct.obter_esqueleto_murcko,
    ct.gerar_tautomeros,
]


@pytest.mark.parametrize("funcao", FUNCOES_DE_UM_SMILES, ids=lambda f: f.__name__)
def test_resultado_vira_json(funcao):
    json.dumps(funcao("CC(=O)Oc1ccccc1C(=O)O"), ensure_ascii=False)


@pytest.mark.parametrize("funcao", FUNCOES_DE_UM_SMILES, ids=lambda f: f.__name__)
def test_smiles_invalido_devolve_none(funcao):
    assert funcao("C1CC") is None


def test_comparar_com_smiles_invalido():
    assert ct.comparar_moleculas("CCO", "") is None
    json.dumps(ct.comparar_moleculas("CCO", "CCCO"))
