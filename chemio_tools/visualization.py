import base64
import io
import math

import py3Dmol
from PIL import Image
from rdkit import Chem
from rdkit.Chem import AllChem, Draw
from rdkit.Chem.Draw import rdMolDraw2D
from .cores import esquema_cpk
from .utils import validar_smiles, obter_mapa_carbonos

# Faixa de carga parcial (Gasteiger) usada no gradiente do Mapa Eletrostático
LIMITE_CARGA_MEP = (-0.4, 0.4)


# Cores de destaque por hibridização (RGB 0-1). O rótulo sp3/sp2/sp também é escrito
# ao lado do átomo, para a informação não depender só da cor. O expoente usa a marcação
# <sup> do RDKit: os caracteres ³ e ² não existem na fonte de desenho e viravam "sp".
CORES_HIBRIDIZACAO = {
    "sp3": (0.55, 0.75, 1.0),   # azul
    "sp2": (1.0, 0.70, 0.35),   # laranja
    "sp": (0.85, 0.55, 0.95),   # lilás
}
ROTULOS_HIBRIDIZACAO = {"sp3": "sp<sup>3</sup>", "sp2": "sp<sup>2</sup>", "sp": "sp"}
_HIBRIDIZACAO_RDKIT = {
    Chem.HybridizationType.SP3: "sp3",
    Chem.HybridizationType.SP2: "sp2",
    Chem.HybridizationType.SP: "sp",
}


def _preparar_desenho_2d(
    smiles: str,
    mostrar_h: bool = False,
    destacar_quirais: bool = False,
    mostrar_indices: bool = False,
    mostrar_metilas: bool = False,
    espessura_linha: int = 2,
    tamanho_fonte: int = 12,
    fundo_escuro: bool = False,
    indices_destaque_extra: list[int] = None,
    colorir_hibridizacao: bool = False,
    escala_rotulos: float | None = None,
):
    """
    Monta a molécula, os destaques e as opções de desenho usadas tanto na imagem da tela
    (gerar_imagem_2d) quanto na exportação em PNG/SVG (exportar_imagem_2d).
    Devolve (mol, atomos_destacados, cores_dos_destaques, opcoes) ou None se o SMILES for inválido.
    """
    if not validar_smiles(smiles):
        return None

    mol = Chem.MolFromSmiles(smiles.strip())

    if mostrar_h:
        mol = Chem.AddHs(mol)

    mapa_c = obter_mapa_carbonos(mol)

    if mostrar_indices:
        for atom in mol.GetAtoms():
            idx = atom.GetIdx()
            if idx in mapa_c:
                atom.SetProp("atomNote", mapa_c[idx])

    highlight_atoms = set()
    cores_destaque = {}

    if destacar_quirais:
        # Força a verificação de estereocentros mesmo sem estereoquímica explícita
        mol_estereo = Chem.Mol(mol)
        Chem.AssignStereochemistry(mol_estereo, cleanIt=True, force=True, flagPossibleStereoCenters=True)
        centros = Chem.FindMolChiralCenters(mol_estereo, includeUnassigned=True)

        for idx, config in centros:
            highlight_atoms.add(idx)
            atomo = mol.GetAtomWithIdx(idx)
            note_existente = atomo.GetProp("atomNote") if atomo.HasProp("atomNote") else ""

            simbolo_config = f"({config})" if config != "?" else ""
            if note_existente:
                rotulo = f"{note_existente} {simbolo_config}*".strip()
            else:
                rotulo = f"{simbolo_config}*".strip()

            atomo.SetProp("atomNote", rotulo)

    if indices_destaque_extra:
        for idx in indices_destaque_extra:
            highlight_atoms.add(idx)

    if colorir_hibridizacao:
        for atomo in mol.GetAtoms():
            if atomo.GetSymbol() != "C":
                continue
            hib = _HIBRIDIZACAO_RDKIT.get(atomo.GetHybridization())
            if hib is None:
                continue
            idx = atomo.GetIdx()
            highlight_atoms.add(idx)
            cores_destaque[idx] = CORES_HIBRIDIZACAO[hib]
            note_existente = atomo.GetProp("atomNote") if atomo.HasProp("atomNote") else ""
            atomo.SetProp("atomNote", f"{note_existente} {ROTULOS_HIBRIDIZACAO[hib]}".strip())

    opts = Draw.MolDrawOptions()
    opts.bondLineWidth = espessura_linha
    opts.minFontSize = tamanho_fonte
    opts.maxFontSize = tamanho_fonte + 6
    opts.explicitMethyl = mostrar_metilas
    if escala_rotulos is not None:
        # Tamanho dos rótulos (C1, C2..., R/S, sp³) em relação ao dos átomos; o padrão do RDKit é 0,5
        opts.annotationFontScale = escala_rotulos

    if fundo_escuro:
        # Correção: o nome do método no RDKit é setBackgroundColour (com "u"); a versão
        # anterior chamava setBackgroundColor e o app parava com AttributeError.
        # SetDarkMode também troca as cores das ligações e dos átomos para tons claros.
        rdMolDraw2D.SetDarkMode(opts)
        opts.setBackgroundColour((0.15, 0.17, 0.22, 1.0))

    return mol, sorted(highlight_atoms), (cores_destaque or None), opts


def gerar_imagem_2d(
    smiles: str,
    mostrar_h: bool = False,
    destacar_quirais: bool = False,
    mostrar_indices: bool = False,
    mostrar_metilas: bool = False,
    espessura_linha: int = 2,
    tamanho_fonte: int = 12,
    fundo_escuro: bool = False,
    indices_destaque_extra: list[int] = None,
    colorir_hibridizacao: bool = False,
    escala_rotulos: float | None = None,
):
    """Gera a imagem 2D customizada alinhada às opções e destaque de centros quirais."""
    preparo = _preparar_desenho_2d(
        smiles, mostrar_h, destacar_quirais, mostrar_indices, mostrar_metilas,
        espessura_linha, tamanho_fonte, fundo_escuro, indices_destaque_extra, colorir_hibridizacao, escala_rotulos,
    )
    if preparo is None:
        return None
    mol, highlight_atoms, cores_destaque, opts = preparo

    if cores_destaque:
        # Draw.MolToImage ignora highlightAtomColors; com cores próprias desenha-se pelo Cairo.
        desenho = rdMolDraw2D.MolDraw2DCairo(500, 420)
        desenho.SetDrawOptions(opts)
        rdMolDraw2D.PrepareAndDrawMolecule(
            desenho, mol, highlightAtoms=highlight_atoms, highlightAtomColors=cores_destaque
        )
        desenho.FinishDrawing()
        return Image.open(io.BytesIO(desenho.GetDrawingText()))

    return Draw.MolToImage(
        mol,
        size=(500, 420),
        options=opts,
        highlightAtoms=highlight_atoms if highlight_atoms else None
    )


def exportar_imagem_2d(
    smiles: str,
    formato: str = "png",
    largura: int = 1200,
    altura: int = 1000,
    mostrar_h: bool = False,
    destacar_quirais: bool = False,
    mostrar_indices: bool = False,
    mostrar_metilas: bool = False,
    espessura_linha: int = 2,
    tamanho_fonte: int = 12,
    fundo_escuro: bool = False,
    indices_destaque_extra: list[int] = None,
    colorir_hibridizacao: bool = False,
    escala_rotulos: float | None = None,
) -> dict | None:
    """
    Exporta o desenho 2D em alta resolução, com as mesmas opções da tela.
      formato "png" -> MolDraw2DCairo; "conteudo" é o PNG em base64 (texto, para virar JSON)
      formato "svg" -> MolDraw2DSVG;   "conteudo" é o próprio texto SVG
    Espessura das linhas e fontes crescem na proporção do tamanho (a tela tem 500 px de largura).
    """
    formato = (formato or "").lower()
    if formato not in ("png", "svg"):
        return None
    preparo = _preparar_desenho_2d(
        smiles, mostrar_h, destacar_quirais, mostrar_indices, mostrar_metilas,
        espessura_linha, tamanho_fonte, fundo_escuro, indices_destaque_extra, colorir_hibridizacao, escala_rotulos,
    )
    if preparo is None:
        return None
    mol, highlight_atoms, cores_destaque, opts = preparo

    escala = largura / 500
    opts.bondLineWidth = max(1, round(espessura_linha * escala))
    opts.minFontSize = round(tamanho_fonte * escala)
    opts.maxFontSize = round((tamanho_fonte + 6) * escala)

    if formato == "png":
        desenho = rdMolDraw2D.MolDraw2DCairo(largura, altura)
    else:
        desenho = rdMolDraw2D.MolDraw2DSVG(largura, altura)
    desenho.SetDrawOptions(opts)
    rdMolDraw2D.PrepareAndDrawMolecule(
        desenho,
        mol,
        highlightAtoms=highlight_atoms or None,
        highlightAtomColors=cores_destaque,
    )
    desenho.FinishDrawing()
    texto = desenho.GetDrawingText()

    if formato == "png":
        return {
            "formato": "png",
            "mime": "image/png",
            "largura": largura,
            "altura": altura,
            "conteudo": base64.b64encode(texto).decode("ascii"),
        }
    return {"formato": "svg", "mime": "image/svg+xml", "largura": largura, "altura": altura, "conteudo": texto}


def gerar_html_3d(
    smiles: str,
    estilo: str = "Ball & Stick",
    mostrar_h: bool = True,
    fundo_escuro: bool = False,
    superficie: str = "Nenhuma",
    coloracao_superficie: str = "Mapa Eletrostático (MEP)",
    opacidade_superficie: float = 0.5,
    auto_spin: bool = False,
    destacar_quirais: bool = False,
    espessura_3d: int = 4,
    raio_malha_quiral: float = 1.2,
    largura: int = 520,
    altura: int = 420
) -> str | None:
    """
    Gera a visualização 3D interativa sincronizando os centros quirais com o modelo final.
    Os átomos usam um único esquema de cores, o CPK com as cores do Jmol (chemio_tools/cores.py),
    com o carbono preto no fundo claro e cinza-escuro no fundo escuro.
    """
    if not validar_smiles(smiles):
        return None

    mol = Chem.MolFromSmiles(smiles.strip())
    mol_3d = Chem.AddHs(mol) if mostrar_h else mol

    if AllChem.EmbedMolecule(mol_3d, randomSeed=42) != 0:
        return None

    AllChem.MMFFOptimizeMolecule(mol_3d)

    # Cargas parciais de Gasteiger (usadas pelo Mapa Eletrostático).
    # Ficam em "_GasteigerCharge" no RDKit e NÃO são escritas no MolBlock,
    # por isso são enviadas ao viewer abaixo via mapAtomProperties.
    cargas_parciais = None
    try:
        AllChem.ComputeGasteigerCharges(mol_3d)
        cargas_parciais = []
        for atomo in mol_3d.GetAtoms():
            carga = atomo.GetDoubleProp("_GasteigerCharge")
            cargas_parciais.append(carga if math.isfinite(carga) else 0.0)
    except Exception:
        cargas_parciais = None

    mol_block = Chem.MolToMolBlock(mol_3d)

    view = py3Dmol.view(width=largura, height=altura)
    view.addModel(mol_block, "sdf")

    usar_mep = (
        superficie != "Nenhuma"
        and coloracao_superficie == "Mapa Eletrostático (MEP)"
        and cargas_parciais is not None
    )
    if usar_mep:
        # O índice do átomo no 3Dmol segue a ordem do MolBlock, que é a mesma do RDKit.
        view.mapAtomProperties([
            {"index": idx, "props": {"partialCharge": round(carga, 4)}}
            for idx, carga in enumerate(cargas_parciais)
        ])

    bg_color = "#1e1e1e" if fundo_escuro else "white"
    view.setBackgroundColor(bg_color)

    spec_cor = {"colorscheme": esquema_cpk(fundo_escuro)}

    if estilo == "Wireframe / Line":
        raio_wireframe = 0.02 * espessura_3d
        dict_stick = {"radius": raio_wireframe}
        dict_stick.update(spec_cor)
        view.setStyle({"stick": dict_stick})

    elif estilo == "Stick (Bastonetes)":
        dict_stick = {"radius": espessura_3d * 0.04}
        dict_stick.update(spec_cor)
        view.setStyle({"stick": dict_stick})

    elif estilo == "CPK / Esferas":
        dict_sphere = {"scale": 0.8}
        dict_sphere.update(spec_cor)
        view.setStyle({"sphere": dict_sphere})

    else:  # Ball & Stick
        dict_stick = {"radius": espessura_3d * 0.03}
        dict_stick.update(spec_cor)
        dict_sphere = {"scale": 0.25}
        dict_sphere.update(spec_cor)
        view.setStyle({"stick": dict_stick, "sphere": dict_sphere})

    # Destaque dos Centros Quirais no modelo 3D
    if destacar_quirais:
        Chem.AssignStereochemistry(mol_3d, cleanIt=True, force=True, flagPossibleStereoCenters=True)
        centros = Chem.FindMolChiralCenters(mol_3d, includeUnassigned=True)
        conf = mol_3d.GetConformer()

        for idx, _ in centros:
            pos = conf.GetAtomPosition(idx)
            view.addSphere({
                "center": {"x": pos.x, "y": pos.y, "z": pos.z},
                "radius": raio_malha_quiral,
                "color": "#00aaff",
                "wireframe": True,
                "opacity": 0.45
            })

    # Superfície Eletrônica
    if superficie != "Nenhuma":
        surf_type = py3Dmol.VDW
        if superficie == "Superfície Acessível ao Solvente (SAS)":
            surf_type = py3Dmol.SAS

        if usar_mep:
            # Gradiente vermelho-branco-azul: vermelho = carga parcial negativa, azul = positiva
            surf_spec = {
                "opacity": opacidade_superficie,
                "colorscheme": {
                    "prop": "partialCharge",
                    "gradient": "rwb",
                    "min": LIMITE_CARGA_MEP[0],
                    "max": LIMITE_CARGA_MEP[1]
                }
            }
        else:
            surf_spec = {"opacity": opacidade_superficie, "color": "lightblue"}

        view.addSurface(surf_type, surf_spec)

    if auto_spin:
        view.spin(True)

    view.zoomTo()
    return view._make_html()
