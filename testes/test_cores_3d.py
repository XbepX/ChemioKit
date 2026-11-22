"""Esquema de cores único do 3D: CPK com as cores do Jmol (3Dmol.js 2.5.5)."""

import inspect
import json
import re

import pytest

from chemio_tools import gerar_html_3d
from chemio_tools.cores import CORES_JMOL, esquema_cpk


@pytest.mark.parametrize(
    "elemento, cor",
    # valores de elementColors.Jmol no 3Dmol.js 2.5.5
    [("H", "#ffffff"), ("N", "#3050f8"), ("O", "#ff0d0d"), ("S", "#ffff30"), ("Cl", "#1ff01f"), ("Br", "#a62929"), ("F", "#90e050")],
)
def test_cores_do_jmol(elemento, cor):
    assert CORES_JMOL[elemento] == cor


def test_carbono_preto_no_fundo_claro_e_cinza_no_escuro():
    assert esquema_cpk(False)["map"]["C"] == "#000000"
    assert esquema_cpk(True)["map"]["C"] == "#606060"
    assert esquema_cpk(False)["prop"] == "elem"
    assert CORES_JMOL["C"] == "#909090"  # o mapa base não é alterado


def _esquemas_no_html(html: str) -> list[dict]:
    return [json.loads(m) for m in re.findall(r'"colorscheme": (\{"prop": "elem", "map": \{.*?\}\})', html)]


@pytest.mark.parametrize("fundo_escuro, carbono", [(False, "#000000"), (True, "#606060")])
@pytest.mark.parametrize("estilo", ["Ball & Stick", "Wireframe / Line", "Stick (Bastonetes)", "CPK / Esferas"])
def test_viewer_recebe_o_esquema_cpk(estilo, fundo_escuro, carbono):
    html = gerar_html_3d("CC(=O)Nc1ccc(Cl)cc1", estilo=estilo, fundo_escuro=fundo_escuro)
    esquemas = _esquemas_no_html(html)
    assert esquemas, "o esquema de cores não chegou ao viewer"
    assert all(e["map"]["C"] == carbono and e["map"]["N"] == "#3050f8" for e in esquemas)
    assert "blackCarbon" not in html and '"Jmol"' not in html


def test_seletor_de_esquema_foi_removido():
    assert "esquema_cor" not in inspect.signature(gerar_html_3d).parameters
