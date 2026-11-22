"""Desenho 2D: exportação PNG/SVG, coloração por hibridização e fundo escuro."""

import base64
import io
import json

import pytest
from PIL import Image

from chemio_tools import exportar_imagem_2d, gerar_imagem_2d
from chemio_tools.visualization import CORES_HIBRIDIZACAO, _preparar_desenho_2d


def test_exportar_png_em_alta_resolucao():
    r = exportar_imagem_2d("CC(=O)Oc1ccccc1C(=O)O", "png")
    json.dumps(r)
    dados = base64.b64decode(r["conteudo"])
    assert dados[:8] == b"\x89PNG\r\n\x1a\n"
    assert Image.open(io.BytesIO(dados)).size == (1200, 1000)


def test_exportar_svg():
    r = exportar_imagem_2d("CCO", "svg", largura=800, altura=600)
    assert r["mime"] == "image/svg+xml"
    assert "<svg" in r["conteudo"] and "width='800px'" in r["conteudo"]


@pytest.mark.parametrize("formato, smiles", [("jpg", "CCO"), ("png", "C1CC"), ("svg", "")])
def test_exportar_entradas_invalidas(formato, smiles):
    assert exportar_imagem_2d(smiles, formato) is None


def test_fundo_escuro_nao_quebra():
    # Antes da correção, opts.setBackgroundColor levantava AttributeError no RDKit 2026.3.5
    img = gerar_imagem_2d("CCO", fundo_escuro=True)
    assert img.getpixel((2, 2))[:3] == (38, 43, 56)  # (0.15, 0.17, 0.22) × 255, arredondado
    assert exportar_imagem_2d("CCO", "png", fundo_escuro=True) is not None


def test_cores_e_rotulos_por_hibridizacao():
    mol, destacados, cores, _ = _preparar_desenho_2d("C#CC=CC", colorir_hibridizacao=True)
    assert destacados == [0, 1, 2, 3, 4]
    assert cores == {
        0: CORES_HIBRIDIZACAO["sp"], 1: CORES_HIBRIDIZACAO["sp"],
        2: CORES_HIBRIDIZACAO["sp2"], 3: CORES_HIBRIDIZACAO["sp2"],
        4: CORES_HIBRIDIZACAO["sp3"],
    }
    assert mol.GetAtomWithIdx(4).GetProp("atomNote") == "sp<sup>3</sup>"


def test_hibridizacao_soma_ao_rotulo_do_carbono():
    mol, *_ = _preparar_desenho_2d("CO", mostrar_indices=True, colorir_hibridizacao=True)
    assert mol.GetAtomWithIdx(0).GetProp("atomNote") == "C1 sp<sup>3</sup>"
    assert not mol.GetAtomWithIdx(1).HasProp("atomNote")  # oxigênio não é colorido


def test_imagem_colorida_usa_as_cores_escolhidas():
    img = gerar_imagem_2d("C#C", colorir_hibridizacao=True).convert("RGB")
    lilas = tuple(round(v * 255) for v in CORES_HIBRIDIZACAO["sp"])
    cores = {c for _, c in img.getcolors(maxcolors=100000)}
    # o Cairo pode arredondar cada canal em 1 unidade (ex.: 243 em vez de 242)
    assert any(all(abs(a - b) <= 2 for a, b in zip(cor, lilas)) for cor in cores)
