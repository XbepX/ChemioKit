"""Aba Isomeria (AppTest)."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "app.py")


@pytest.fixture
def app():
    at = AppTest.from_file(APP, default_timeout=120)
    at.run()
    assert not at.exception
    return at


def _gerar(at, formula):
    at.text_input(key="iso_formula").input(formula)
    next(b for b in at.button if b.label == "Gerar").click()
    at.run()
    assert not at.exception


def test_aba_isomeria_abre_com_c4h10o(app):
    assert any("C4H10O" in s.value and "7 isômeros" in s.value for s in app.success)
    assert any("álcool (4)" in m.value and "éter (3)" in m.value for m in app.markdown)


def test_comparar_par_mostra_tipo(app):
    # padrão: isômero 1 (CCCCO) × isômero 2 (CCCOC) = função
    assert any("Isomeria plana: **função**" in s.value for s in app.success)


def test_formula_invalida_avisa(app):
    _gerar(app, "C4H11O")
    assert any("não corresponde" in w.value for w in app.warning)


def test_formula_grande_avisa(app):
    _gerar(app, "C9H20")
    assert any("O limite é 8" in w.value for w in app.warning)


def test_abrir_isomero_no_chemiokit(app):
    next(b for b in app.button if b.label == "Abrir no ChemioKit").click()
    app.run()
    assert not app.exception
    assert app.text_input(key="campo_smiles").value == "CCCCO"


def test_buscar_nomes_sem_internet_nao_trava(app):
    next(b for b in app.button if "PubChem" in b.label).click()
    app.run()
    assert not app.exception
    assert any("PubChem" in w.value for w in app.warning)
