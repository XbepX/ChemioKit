"""
Descritores usados na química medicinal: Regra dos 5 de Lipinski, QED e alertas
estruturais (FilterCatalog do RDKit).

Os alertas estruturais marcam subestruturas que costumam dar problema em triagens de
fármacos (reatividade, interferência em ensaios). São ALERTAS para análise, não uma
previsão de toxicidade: muitos fármacos seguros têm algum desses grupos (a aspirina,
por exemplo, tem um "éster de fenol").
"""

from rdkit import Chem
from rdkit.Chem import QED, Descriptors, rdMolDescriptors
from rdkit.Chem.FilterCatalog import FilterCatalog, FilterCatalogParams

from .utils import validar_smiles

# Limites da Regra dos 5 (Lipinski et al., 1997): todos múltiplos de 5.
LIMITES_LIPINSKI = {
    "massa_molecular": 500,
    "logp": 5,
    "doadores_h": 5,
    "aceitadores_h": 10,
}

AVISO_ALERTAS = (
    "Alertas estruturais indicam subestruturas que merecem atenção em triagens de fármacos. "
    "Não são uma previsão de toxicidade."
)

CATALOGOS_ALERTAS = {
    "Brenk": "Brenk (2008): grupos indesejados em bibliotecas de triagem",
    "PAINS_A": "PAINS (família A): interferência em ensaios biológicos",
    "PAINS_B": "PAINS (família B): interferência em ensaios biológicos",
    "PAINS_C": "PAINS (família C): interferência em ensaios biológicos",
    "NIH": "NIH: grupos funcionais problemáticos em ensaios",
}

_catalogo: FilterCatalog | None = None


def _obter_catalogo() -> FilterCatalog:
    global _catalogo
    if _catalogo is None:
        params = FilterCatalogParams()
        for c in (
            FilterCatalogParams.FilterCatalogs.BRENK,
            FilterCatalogParams.FilterCatalogs.PAINS,
            FilterCatalogParams.FilterCatalogs.NIH,
        ):
            params.AddCatalog(c)
        _catalogo = FilterCatalog(params)
    return _catalogo


def avaliar_lipinski(smiles: str) -> dict | None:
    """
    Regra dos 5 de Lipinski. Doadores e aceitadores seguem a definição original da regra
    (rdMolDescriptors.CalcNumLipinskiHBD/HBA):
      doadores_h    = número de ligações N–H e O–H (um NH2 conta 2);
      aceitadores_h = número de átomos de N e O.
    Massa molecular média (g/mol) e LogP de Crippen (o mesmo da aba Propriedades).
    Ligações rotacionáveis são informadas, mas não fazem parte da Regra dos 5.
    "aprovado" é True com no máximo uma violação, como no artigo original.
    """
    if not validar_smiles(smiles):
        return None

    mol = Chem.MolFromSmiles(smiles.strip())
    valores = {
        "massa_molecular": round(Descriptors.MolWt(mol), 2),
        "logp": round(Descriptors.MolLogP(mol), 2),
        "doadores_h": rdMolDescriptors.CalcNumLipinskiHBD(mol),
        "aceitadores_h": rdMolDescriptors.CalcNumLipinskiHBA(mol),
    }
    criterios = [
        {"criterio": nome, "valor": valor, "limite": LIMITES_LIPINSKI[nome], "ok": valor <= LIMITES_LIPINSKI[nome]}
        for nome, valor in valores.items()
    ]
    violacoes = sum(not c["ok"] for c in criterios)
    return {
        **valores,
        "ligacoes_rotacionaveis": Descriptors.NumRotatableBonds(mol),
        "criterios": criterios,
        "violacoes": violacoes,
        "aprovado": violacoes <= 1,
    }


def calcular_qed(smiles: str) -> dict | None:
    """
    QED (Bickerton et al., 2012): nota de 0 a 1 de "semelhança com fármacos orais",
    que combina massa, LogP, doadores e aceitadores de H, área polar, ligações
    rotacionáveis, anéis aromáticos e alertas. Devolve a nota e as propriedades usadas.
    """
    if not validar_smiles(smiles):
        return None

    mol = Chem.MolFromSmiles(smiles.strip())
    props = QED.properties(mol)
    return {
        "qed": round(QED.qed(mol), 3),
        "propriedades": {
            "massa_molecular": round(props.MW, 2),
            "alogp": round(props.ALOGP, 2),
            "aceitadores_h": props.HBA,
            "doadores_h": props.HBD,
            "area_polar": round(props.PSA, 2),
            "ligacoes_rotacionaveis": props.ROTB,
            "aneis_aromaticos": props.AROM,
            "alertas_qed": props.ALERTS,
        },
    }


def buscar_alertas_estruturais(smiles: str) -> dict | None:
    """
    Procura subestruturas dos catálogos Brenk, PAINS (A, B e C) e NIH do RDKit.
    Devolve {"aviso", "total", "alertas": [{nome, catalogo, descricao_catalogo, indices}]}.
    "indices" são os átomos do SMILES que formam a subestrutura (para destacar no desenho).
    """
    if not validar_smiles(smiles):
        return None

    mol = Chem.MolFromSmiles(smiles.strip())
    alertas = []
    for entrada in _obter_catalogo().GetMatches(mol):
        catalogo = entrada.GetProp("FilterSet") if "FilterSet" in entrada.GetPropList() else ""
        indices = sorted({idx for m in entrada.GetFilterMatches(mol) for _, idx in m.atomPairs})
        alertas.append(
            {
                "nome": entrada.GetDescription(),
                "catalogo": catalogo,
                "descricao_catalogo": CATALOGOS_ALERTAS.get(catalogo, catalogo),
                "indices": indices,
            }
        )
    return {"aviso": AVISO_ALERTAS, "total": len(alertas), "alertas": alertas}
