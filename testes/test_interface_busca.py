"""Busca da molécula (campo único: nome, SMILES ou fórmula), histórico e exemplos (AppTest)."""

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
    at.text_input(key="campo_busca").input(nome)
    _botao(at, "Buscar").click()
    at.run()
    assert not at.exception


def test_app_abre_na_tela_de_boas_vindas_com_a_busca_no_centro(app):
    assert app.session_state.molecula is None
    assert any("Para começar" in m.value for m in app.markdown)
    campo = app.text_input(key="campo_busca")
    assert campo.label == "Nome, SMILES ou fórmula da molécula"


def test_busca_fica_no_topo_com_molecula_aberta(app):
    _buscar(app, "etanol")
    assert app.text_input[0].key == "campo_busca"  # o primeiro campo da página é a busca
    assert any("glossário" in t.value for t in app.toast)


def test_exemplo_abre_a_molecula(app):
    _botao(app, "Ácido láctico").click()
    app.run()
    assert app.session_state.molecula["smiles"] == "CC(O)C(=O)O"
    assert [t.label for t in app.tabs] == ["Estrutura", "Propriedades", "Estereoquímica", "Comparar", "Exportar"]


def test_busca_por_nome_abre_a_molecula(app):
    _buscar(app, "etanol")
    assert app.session_state.molecula == {"smiles": "CCO", "nome": "Etanol", "origem": "glossario"}
    assert any("Etanol" in t.value for t in app.toast)


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


def test_mesmo_campo_aceita_smiles_valido_e_invalido(app):
    _buscar(app, "CC(O")
    assert any("parece um SMILES, mas não é válido" in e.value for e in app.error)
    assert app.session_state.molecula is None
    _buscar(app, "CCN")
    assert app.session_state.molecula["smiles"] == "CCN"


def test_formula_com_um_isomero_abre_direto(app):
    _buscar(app, "CH4")
    assert app.session_state.molecula["smiles"] == "C"


def test_formula_com_poucos_isomeros_mostra_opcoes(app):
    _buscar(app, "C2H6O")
    assert any("fórmula molecular com 2 isômeros" in i.value for i in app.info)
    _botao(app, "COC (éter)").click()
    app.run()
    assert app.session_state.molecula == {"smiles": "COC", "nome": "", "origem": "formula"}


def test_formula_com_muitos_isomeros_leva_a_isomeria(app):
    _buscar(app, "C6H6")
    _botao(app, "Ver os isômeros de C6H6").click()
    app.run()
    assert app.session_state.iso_formula == "C6H6"


def test_co_avisa_que_foi_lido_como_smiles(app):
    _buscar(app, "CO")
    assert any("lido como SMILES" in i.value for i in app.info)


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
