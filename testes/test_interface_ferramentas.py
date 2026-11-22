"""Interface: hibridização no 2D, fundo escuro do 2D e downloads da aba Exportar (AppTest)."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "app.py")


@pytest.fixture
def app():
    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    assert not at.exception
    return at


def _caixa(at, rotulo):
    return next(c for c in at.checkbox if c.label == rotulo)


def test_colorir_por_hibridizacao_mostra_contagens(app):
    app.text_input(key="campo_smiles").input("C#CC=C").run()
    _caixa(app, "Colorir carbonos por hibridização").check().run()
    assert not app.exception
    texto = " ".join(m.value for m in app.markdown)
    assert "**sp³**: 0" in texto and "**sp²**: 2" in texto and "**sp**: 2" in texto
    assert "**σ**: 7" in texto and "**π**: 3" in texto  # but-1-en-3-ino: C4H4


def test_fundo_escuro_do_2d_nao_derruba_o_app(app):
    _caixa(app, "Fundo escuro").check().run()
    assert not app.exception


def test_aba_exportar_tem_png_e_svg(app):
    rotulos = [b.proto.label for b in app.get("download_button")]
    assert "⬇️ Baixar Imagem PNG (.png)" in rotulos
    assert "⬇️ Baixar Imagem SVG (.svg)" in rotulos
    assert "⬇️ Baixar Bloco SDF (.sdf)" in rotulos  # o que já existia continua


def test_3d_sem_seletor_de_esquema_de_cores(app):
    app.radio[0].set_value("3D").run()
    assert not app.exception
    assert all(s.label != "Esquema de Cores" for s in app.selectbox)
    assert any("CPK (Jmol)" in c.value for c in app.caption)
