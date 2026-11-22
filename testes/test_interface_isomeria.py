"""Página Isomeria (AppTest). A página é testada chamando a função dela diretamente."""

import pytest
from streamlit.testing.v1 import AppTest


def _pagina():
    from ui import estado, pagina_isomeria

    estado.inicializar()
    pagina_isomeria()


@pytest.fixture
def app():
    at = AppTest.from_function(_pagina, default_timeout=120)
    at.run()
    assert not at.exception
    return at


def _gerar(at, formula):
    at.text_input(key="iso_formula").input(formula)
    next(b for b in at.button if b.label == "Gerar").click()
    at.run()
    assert not at.exception


def test_pagina_abre_com_c4h10o(app):
    assert any("C4H10O" in s.value and "7 isômeros" in s.value for s in app.success)
    assert any("álcool (4)" in m.value and "éter (3)" in m.value for m in app.markdown)


def test_comparar_par_mostra_tipo(app):
    # padrão: isômero 1 (CCCCO) × isômero 2 (CCCOC) = função
    assert any("Isomeria plana: **função**" in s.value for s in app.success)


def test_formula_invalida_avisa(app):
    _gerar(app, "C4H11O")
    assert any("não corresponde" in w.value for w in app.warning)


def test_formula_acima_de_8_carbonos_funciona(app):
    _gerar(app, "C9H20")
    assert any("35 isômeros" in s.value for s in app.success)


def test_formula_grande_demais_avisa(app):
    _gerar(app, "C25H52")
    assert any("o limite é 20" in w.value for w in app.warning)


def test_abrir_isomero_vai_para_a_pagina_molecula(app):
    next(b for b in app.button if b.label == "Abrir no ChemioKit").click()
    app.run()
    assert not app.exception
    assert app.session_state.molecula["smiles"] == "CCCCO"
    assert app.session_state.ir_para_molecula is True  # o app.py troca de página com esse sinal


def test_buscar_nomes_sem_internet_nao_trava(app):
    next(b for b in app.button if "PubChem" in b.label).click()
    app.run()
    assert not app.exception
    assert any("PubChem" in w.value for w in app.warning)


def test_cartao_de_isomero_alterna_para_3d(app):
    chave = next(s.key for s in app.segmented_control if s.key and s.key.startswith("dim_iso_C4H10O_"))
    app.segmented_control(key=chave).set_value("3D").run()
    assert not app.exception
    assert len(app.get("iframe")) == 1
