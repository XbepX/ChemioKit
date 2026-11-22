"""Busca por nome na interface (streamlit.testing.v1.AppTest)."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "app.py")
MESO_TARTARICO = "[C@@H]([C@@H](C(=O)O)O)(C(=O)O)O"


@pytest.fixture
def app():
    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    assert not at.exception
    return at


def _buscar(at, nome):
    at.text_input(key="campo_nome").input(nome)
    next(b for b in at.button if b.label == "Buscar").click()
    at.run()
    assert not at.exception


def _botao(at, rotulo_contem):
    return next(b for b in at.button if rotulo_contem in b.label)


def test_app_abre_com_smiles_inicial(app):
    assert app.text_input(key="campo_smiles").value == "O=C[C@H](O)[C@@H](O)[C@H](O)[C@H](O)CO"


def test_busca_por_nome_preenche_o_smiles(app):
    _buscar(app, "etanol")
    assert app.text_input(key="campo_smiles").value == "CCO"
    assert any("Etanol" in s.value for s in app.success)


def test_nome_ambiguo_mostra_opcoes_e_aplica_a_escolhida(app):
    _buscar(app, "ácido tartárico")
    assert any("mais de uma substância" in i.value for i in app.info)
    _botao(app, "meso").click()
    app.run()
    assert app.text_input(key="campo_smiles").value == MESO_TARTARICO


def test_mistura_mostra_componentes(app):
    _buscar(app, "vinagre")
    assert any("mistura" in i.value for i in app.info)
    _botao(app, "Ácido etanoico").click()
    app.run()
    assert app.text_input(key="campo_smiles").value == "CC(=O)O"


def test_sem_internet_avisa_sem_travar_e_sugestao_funciona(app):
    _buscar(app, "etanoll")
    assert any("PubChem" in w.value for w in app.warning)
    _botao(app, "etanol").click()
    app.run()
    assert app.text_input(key="campo_smiles").value == "CCO"
