"""Entrada da molécula na barra lateral: nome, SMILES, histórico e exemplos (AppTest)."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "app.py")
MESO_TARTARICO = "[C@@H]([C@@H](C(=O)O)O)(C(=O)O)O"


@pytest.fixture
def app():
    at = AppTest.from_file(APP, default_timeout=120)
    at.run()
    assert not at.exception
    return at


def _botao(at, rotulo_contem):
    return next(b for b in at.button if rotulo_contem in b.label)


def _buscar(at, nome):
    at.text_input(key="campo_nome").input(nome)
    _botao(at, "Buscar").click()
    at.run()
    assert not at.exception


def test_app_abre_na_tela_de_boas_vindas(app):
    assert app.session_state.molecula is None
    assert any("Para começar" in m.value for m in app.markdown)


def test_exemplo_abre_a_molecula(app):
    _botao(app, "Ácido láctico").click()
    app.run()
    assert app.session_state.molecula["smiles"] == "CC(O)C(=O)O"
    assert [t.label for t in app.tabs] == ["Estrutura", "Propriedades", "Estereoquímica", "Comparar", "Exportar"]


def test_busca_por_nome_abre_a_molecula(app):
    _buscar(app, "etanol")
    assert app.session_state.molecula == {"smiles": "CCO", "nome": "Etanol", "origem": "glossario"}
    assert any("Etanol" in s.value for s in app.success)


def test_nome_ambiguo_mostra_opcoes_e_aplica_a_escolhida(app):
    _buscar(app, "ácido tartárico")
    assert any("mais de uma substância" in i.value for i in app.info)
    _botao(app, "meso").click()
    app.run()
    assert app.session_state.molecula["smiles"] == MESO_TARTARICO


def test_mistura_mostra_componentes(app):
    _buscar(app, "vinagre")
    assert any("mistura" in i.value for i in app.info)
    _botao(app, "Ácido etanoico").click()
    app.run()
    assert app.session_state.molecula["smiles"] == "CC(=O)O"


def test_sem_internet_avisa_sem_travar_e_sugestao_funciona(app):
    _buscar(app, "etanoll")
    assert any("PubChem" in w.value for w in app.warning)
    _botao(app, "etanol").click()
    app.run()
    assert app.session_state.molecula["smiles"] == "CCO"


def test_entrada_por_smiles_valido_e_invalido(app):
    app.segmented_control(key="forma_entrada").set_value("SMILES").run()
    app.text_input(key="campo_smiles").input("C1CC")
    _botao(app, "Abrir").click()
    app.run()
    assert any("SMILES inválido" in e.value for e in app.error)
    assert app.session_state.molecula is None
    app.text_input(key="campo_smiles").input("CCN")
    _botao(app, "Abrir").click()
    app.run()
    assert app.session_state.molecula["smiles"] == "CCN"


def test_historico_permite_voltar(app):
    _buscar(app, "etanol")
    _buscar(app, "aspirina")
    assert [h["nome"] for h in app.session_state.historico] == ["Ácido acetilsalicílico", "Etanol"]
    next(b for b in app.button if b.label == "Etanol").click()
    app.run()
    assert app.session_state.molecula["smiles"] == "CCO"


def test_cartao_mostra_nome_formula_e_smiles(app):
    _buscar(app, "aspirina")
    assert any(m.value == "### Ácido acetilsalicílico" for m in app.markdown)
    assert any("C₉H₈O₄" in m.value and "180,16 g/mol" in m.value for m in app.markdown)
    assert any(c.value == "CC(=O)Oc1ccccc1C(=O)O" for c in app.code)
