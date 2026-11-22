"""Abas da página Molécula no modo Explorar (AppTest)."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "app.py")


def _abrir(smiles, nome="", **params):
    at = AppTest.from_file(APP, default_timeout=120)
    at.query_params["smiles"] = smiles
    if nome:
        at.query_params["nome"] = nome
    for k, v in params.items():
        at.query_params[k] = v
    at.run()
    assert not at.exception
    return at


def _caixa(at, rotulo):
    return next(c for c in at.checkbox if c.label == rotulo)


# ------------------------------------------------------------------ Estrutura


def test_botao_hibridizacao_mostra_contagens():
    at = _abrir("C#CC=C")
    at.toggle(key="est_hib").set_value(True).run()
    assert not at.exception
    texto = " ".join(m.value for m in at.markdown)
    assert "**sp³**: 0" in texto and "**sp²**: 2" in texto and "**sp**: 2" in texto
    assert "**σ**: 7" in texto and "**π**: 3" in texto  # but-1-en-3-ino: C4H4


def test_fundo_escuro_do_2d_nao_derruba_o_app():
    at = _abrir("CCO")
    _caixa(at, "Fundo escuro").check().run()
    assert not at.exception


def test_3d_usa_st_iframe_e_esquema_cpk_unico():
    at = _abrir("CCO")
    at.segmented_control(key="modo_vis").set_value("3D").run()
    assert not at.exception
    assert len(at.get("iframe")) == 1
    assert all(s.label != "Esquema de Cores" for s in at.selectbox)
    assert any("CPK (Jmol)" in c.value for c in at.caption)
    assert "Cargas Parciais (Gasteiger)" in at.selectbox(key="o3_coloracao").options


def test_grupo_funcional_pode_ser_destacado():
    at = _abrir("CCOC(C)=O")
    assert at.pills(key="grupo_ativo").options == ["Éster"]
    at.pills(key="grupo_ativo").set_value("Éster").run()
    assert not at.exception
    assert at.session_state.opcoes_2d["indices_destaque_extra"]


# ------------------------------------------------------------------ Propriedades e detalhes técnicos


def test_propriedades_mostram_lipinski_e_qed():
    at = _abrir("CC(=O)Oc1ccccc1C(=O)O", "Ácido acetilsalicílico", aba="Propriedades")
    assert any(m.label == "QED" for m in at.metric)
    assert any("0 violação(ões)" in m.value for m in at.markdown)


def test_detalhes_tecnicos_mostram_tabela_e_downloads():
    at = _abrir("CCO", tecnico="1")
    rotulos = [b.proto.label for b in at.get("download_button")]
    assert "⬇️ Todos os resultados (.json)" in rotulos and "⬇️ Tabela de descritores (.csv)" in rotulos


# ------------------------------------------------------------------ Estereoquímica


def test_estereoquimica_do_acido_tartarico():
    at = _abrir("O=C(O)C(O)C(O)C(=O)O")
    assert any("Estereoisômeros únicos encontrados: **3**" in s.value for s in at.success)
    assert any("$2^n$ = 4" in i.value and "compostos meso" in i.value for i in at.info)


def test_estereoquimica_explica_os_ligantes():
    at = _abrir("C[C@@H](O)C(=O)O")
    assert any("**C2**: H, CH₃, OH, COOH — configuração **R**" in m.value for m in at.markdown)


# ------------------------------------------------------------------ Alertas


def test_aba_alertas_so_aparece_com_alertas():
    assert "⚠️ Alertas" not in [t.label for t in _abrir("CCO").tabs]
    at = _abrir("CC=O")
    assert "⚠️ Alertas" in [t.label for t in at.tabs]
    assert any("Não são uma previsão de toxicidade" in w.value for w in at.warning)


# ------------------------------------------------------------------ Comparar


def test_comparar_com_isomero():
    at = _abrir("CCCCO")
    at.text_input(key="comparar_texto").input("CCC(C)O")
    next(b for b in at.button if b.label == "Comparar").click()
    at.run()
    assert not at.exception
    assert any("Isomeria plana: **posição**" in s.value for s in at.success)
    assert any(m.label == "Similaridade (Tanimoto)" for m in at.metric)


def test_comparar_entrada_invalida():
    at = _abrir("CCO")
    at.text_input(key="comparar_texto").input("xyzabc")
    next(b for b in at.button if b.label == "Comparar").click()
    at.run()
    assert not at.exception and at.error


# ------------------------------------------------------------------ Exportar


def test_aba_exportar_tem_identificadores_e_downloads():
    at = _abrir("CCO")
    assert any(c.value == "LFQSCWFLJHTTHZ-UHFFFAOYSA-N" for c in at.code)
    rotulos = [b.proto.label for b in at.get("download_button")]
    for r in ["⬇️ Imagem PNG (.png)", "⬇️ Imagem SVG (.svg)", "⬇️ Arquivo SDF (.sdf)", "⬇️ Arquivo PDB (.pdb)"]:
        assert r in rotulos


def test_janelas_de_estrutura_tem_fundo_branco_por_padrao():
    at = _abrir("CCO")
    assert at.session_state.opcoes_2d["fundo_escuro"] is False
    assert next(c for c in at.checkbox if c.label == "Fundo escuro").value is False
    at.segmented_control(key="modo_vis").set_value("3D").run()
    assert next(c for c in at.checkbox if c.label == "Fundo escuro").value is False
    assert 'setBackgroundColor("white")' in at.get("iframe")[0].proto.srcdoc


def test_hibridizacao_tambem_no_3d():
    at = _abrir("C#CC=C")
    at.toggle(key="est_hib").set_value(True).run()
    at.segmented_control(key="modo_vis").set_value("3D").run()
    assert not at.exception
    html = at.get("iframe")[0].proto.srcdoc
    assert 'addLabel("C1 sp"' in html and 'addLabel("C3 sp\\u00b2"' in html
    assert any("**sp³**: 0" in m.value for m in at.markdown)  # a contagem continua no 3D


def test_grupo_funcional_destacado_no_3d():
    at = _abrir("CCOC(C)=O")
    at.pills(key="grupo_ativo").set_value("Éster").run()
    at.segmented_control(key="modo_vis").set_value("3D").run()
    assert "#ff9900" in at.get("iframe")[0].proto.srcdoc  # esferas de destaque


@pytest.mark.parametrize("aba, chave", [
    ("Estereoquímica", "dim_estereo_principal"),
    ("Propriedades", "dim_murcko"),
])
def test_outras_janelas_alternam_para_3d(aba, chave):
    at = _abrir("C[C@@H](O)c1ccccc1", aba=aba)
    at.segmented_control(key=chave).set_value("3D").run()
    assert not at.exception
    assert len(at.get("iframe")) == 1


def test_comparar_alterna_as_duas_estruturas_para_3d():
    at = _abrir("CCCCO")
    at.text_input(key="comparar_texto").input("CCC(C)O")
    next(b for b in at.button if b.label == "Comparar").click()
    at.run()
    at.segmented_control(key="dim_comparar").set_value("3D").run()
    assert len(at.get("iframe")) == 2 and all("#ff9900" in f.proto.srcdoc for f in at.get("iframe"))


def test_alertas_alternam_para_3d():
    at = _abrir("CC=O")
    chave = next(s.key for s in at.segmented_control if s.key and s.key.startswith("dim_alerta_"))
    at.segmented_control(key=chave).set_value("3D").run()
    assert len(at.get("iframe")) == 1
