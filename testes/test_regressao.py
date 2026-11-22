"""Casos que já passavam antes da interface v2 e precisam continuar passando."""

import pytest

from chemio_tools import (
    contar_elementos_estereogenicos,
    gerar_estereoisomeros,
    gerar_html_3d,
    identificar_centros_quirais,
    identificar_grupos_funcionais,
)


@pytest.mark.parametrize(
    "smiles, esperado",
    [
        ("O=C(O)[C@H](O)[C@H](O)C(=O)O", "Inativa (composto meso)"),
        ("O=C(O)[C@@H](O)[C@H](O)C(=O)O", "Opticamente Ativa"),
        ("C[C@@H]1CCCC[C@@H]1C", "Inativa (composto meso)"),
        ("C[C@@H](O)CC", "Opticamente Ativa"),
        ("CCC(C)O", "Indefinida"),
        ("CCO", "Inativa"),
    ],
)
def test_atividade_optica(smiles, esperado):
    assert identificar_centros_quirais(smiles)["atividade_optica"] == esperado


@pytest.mark.parametrize(
    "smiles, esperado",
    [
        ("CCOC(C)=O", ["Éster"]),
        ("CCOCC", ["Éter"]),
        ("C[N+](=O)[O-]", []),
        ("CCN", ["Amina"]),
        ("CC(N)=O", ["Amida"]),
    ],
)
def test_grupos_funcionais(smiles, esperado):
    assert [g["grupo"] for g in identificar_grupos_funcionais(smiles)] == esperado


@pytest.mark.parametrize(
    "smiles, n, maximo, encontrados",
    [
        ("O=C(O)C(O)C(O)C(=O)O", 2, 4, 3),
        ("CCC(C)O", 1, 2, 2),
        ("CNC[C@H](O)c1ccc(O)c(O)c1", 1, 2, 2),
        ("C/C=C/C", 1, 2, 2),
        ("CCO", 0, 1, 1),
    ],
)
def test_estereoisomeros(smiles, n, maximo, encontrados):
    n_calc = contar_elementos_estereogenicos(smiles)
    assert (n_calc, 2**n_calc, len(gerar_estereoisomeros(smiles))) == (n, maximo, encontrados)


def test_cargas_parciais_chegam_ao_viewer():
    html = gerar_html_3d("CCO", superficie="Van der Waals (VDW)", coloracao_superficie="Mapa Eletrostático (MEP)")
    assert "mapAtomProperties" in html
    assert '"partialCharge"' in html
    assert '"rwb"' in html
