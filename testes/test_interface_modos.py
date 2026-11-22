"""Modos Aula e Atividade, link compartilhável e QR code (AppTest)."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from ui.compartilhar import gerar_qr_png

APP = str(Path(__file__).resolve().parent.parent / "app.py")


def _abrir(**params):
    at = AppTest.from_file(APP, default_timeout=120)
    for k, v in params.items():
        at.query_params[k] = v
    at.run()
    assert not at.exception
    return at


# ------------------------------------------------------------------ link e QR code


def test_link_abre_molecula_modo_e_atividade():
    at = _abrir(smiles="CC(O)C(=O)O", nome="Ácido láctico", modo="atividade", atividade="sigma_pi")
    assert at.session_state.molecula["nome"] == "Ácido láctico"
    assert (at.session_state.modo, at.session_state.atividade_tipo) == ("atividade", "sigma_pi")


def test_link_com_smiles_invalido_e_ignorado():
    at = _abrir(smiles="C1CC", modo="xyz")
    assert at.session_state.molecula is None and at.session_state.modo == "explorar"


def test_compartilhar_monta_o_link():
    at = _abrir(smiles="CCO", nome="Etanol")
    next(b for b in at.button if b.label == "Compartilhar").click()
    at.run()
    links = [c.value for c in at.code if "smiles=" in c.value]
    assert links and "smiles=CCO" in links[0] and "nome=Etanol" in links[0] and "modo=explorar" in links[0]


def test_qr_code_e_um_png():
    assert gerar_qr_png("http://localhost:8501/?smiles=CCO")[:8] == b"\x89PNG\r\n\x1a\n"


# ------------------------------------------------------------------ Modo Aula


def test_modo_aula_mantem_o_modo_nas_interacoes():
    at = _abrir(smiles="CC(O)C(=O)O", nome="Ácido láctico", modo="aula")
    at.segmented_control(key="aula_vista").set_value("Lado a lado").run()
    assert at.session_state.modo == "aula"
    assert any("Isomeria espacial: óptica (enantiômeros)" in m.value for m in at.markdown)


def test_modo_aula_meso_e_igual_a_imagem_especular():
    at = _abrir(smiles="O=C(O)[C@H](O)[C@H](O)C(=O)O", modo="aula")  # meso (caso da regressão)
    at.segmented_control(key="aula_vista").set_value("Lado a lado").run()
    assert any("mesma substância" in m.value for m in at.markdown)


def test_modo_aula_usa_a_configuracao_escrita():
    # SMILES com configuração definida, escrito diferente do canônico: não pode ser trocado
    at = _abrir(smiles="OC(=O)[C@@H](C)O", modo="aula")
    at.segmented_control(key="aula_vista").set_value("Lado a lado").run()
    assert not any("primeiro estereoisômero" in c.value for c in at.caption)
    assert any("Isomeria espacial: óptica (enantiômeros)" in m.value for m in at.markdown)


def test_modo_aula_3d_lado_a_lado():
    at = _abrir(smiles="CC=CC", modo="aula")
    at.segmented_control(key="aula_vista").set_value("Lado a lado").run()
    at.segmented_control(key="aula_fonte").set_value("Estereoisômeros").run()
    at.segmented_control(key="aula_dim").set_value("3D").run()
    assert not at.exception
    assert len(at.get("iframe")) == 2
    assert any("geométrica" in m.value for m in at.markdown)


def test_sair_do_modo_aula():
    at = _abrir(smiles="CCO", modo="aula")
    next(b for b in at.button if b.label == "Sair").click()
    at.run()
    assert at.session_state.modo == "explorar"


# ------------------------------------------------------------------ Modo Atividade


def _verificar(at):
    next(b for b in at.button if b.label == "Verificar").click()
    at.run()
    assert not at.exception


def test_atividade_quirais_resposta_certa():
    at = _abrir(smiles="CC(O)C(=O)O", modo="atividade", atividade="quirais")
    pills = next(p for p in at.pills if p.label == "Carbonos quirais")
    pills.set_value(["C2"])
    _verificar(at)
    assert any("Correto" in s.value for s in at.success)
    assert any("quatro ligantes diferentes" in m.value for m in at.markdown)  # explicação aparece


def test_atividade_quirais_resposta_errada_e_revelar():
    at = _abrir(smiles="CC(O)C(=O)O", modo="atividade", atividade="quirais")
    next(p for p in at.pills if p.label == "Carbonos quirais").set_value(["C1"])
    _verificar(at)
    assert any("Ainda não" in e.value for e in at.error)
    assert any("C2: faltou marcar" in m.value for m in at.markdown)
    assert not any("**Explicação**" == m.value for m in at.markdown)  # só depois de pedir
    next(b for b in at.button if b.label == "Ver resposta e explicação").click()
    at.run()
    assert any("**Explicação**" == m.value for m in at.markdown)


def test_atividade_sigma_pi():
    at = _abrir(smiles="c1ccccc1", modo="atividade", atividade="sigma_pi")
    at.number_input[0].set_value(12)
    at.number_input[1].set_value(3)
    _verificar(at)
    assert any("Correto" in s.value for s in at.success)


def test_atividade_isomeria_tem_duas_estruturas():
    at = _abrir(smiles="CCCCO", modo="atividade", atividade="isomeria")
    radio = next(r for r in at.radio if r.label == "Tipo de isomeria")
    assert set(radio.options) == {"função", "cadeia", "posição", "metameria", "tautomeria"}
    assert len(at.image) >= 2  # estruturas A e B


def test_outra_molecula_sorteia_do_glossario():
    at = _abrir(smiles="CCO", modo="atividade")
    next(b for b in at.button if "Outra molécula" in b.label).click()
    at.run()
    assert not at.exception
    assert at.session_state.molecula["smiles"] != "CCO" and at.session_state.molecula["origem"] == "glossario"


def test_verificar_sem_responder_avisa_e_nao_corrige():
    at = _abrir(smiles="CC(O)C(=O)O", modo="atividade", atividade="quirais")
    _verificar(at)
    assert any("Responda antes de verificar" in w.value for w in at.warning)
    assert not at.success and not any("Ainda não" in e.value for e in at.error)


def test_nenhum_junto_com_carbono_avisa():
    at = _abrir(smiles="CC(O)C(=O)O", modo="atividade", atividade="quirais")
    next(p for p in at.pills if p.label == "Carbonos quirais").set_value(["C2", "Nenhum"])
    _verificar(at)
    assert any("não combinam" in w.value for w in at.warning)


def test_hibridizacao_incompleta_lista_o_que_falta():
    at = _abrir(smiles="C#CC", modo="atividade", atividade="hibridizacao")
    at.segmented_control(key=next(s.key for s in at.segmented_control if s.label == "C1")).set_value("sp")
    _verificar(at)
    assert any("C2" in w.value and "C3" in w.value for w in at.warning)


def test_atividade_em_3d_mostra_rotulos():
    at = _abrir(smiles="CC(O)C(=O)O", modo="atividade", atividade="quirais")
    chave = next(s.key for s in at.segmented_control if s.key and s.key.endswith("_dim"))
    at.segmented_control(key=chave).set_value("3D").run()
    html = at.get("iframe")[0].proto.srcdoc
    assert 'addLabel("C1"' in html and 'addLabel("C2"' in html


def test_aula_hibridizacao_no_3d():
    at = _abrir(smiles="C#CC", modo="aula")
    at.segmented_control(key="aula_dim").set_value("3D").run()
    at.toggle(key="aula_hib").set_value(True).run()
    assert not at.exception
    assert "sp\\u00b3" in at.get("iframe")[0].proto.srcdoc
