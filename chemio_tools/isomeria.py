"""
Isomeria a partir da fórmula molecular.

1. gerar_isomeros(formula): todos os isômeros constitucionais (planos) da fórmula.
   O RDKit não gera isômeros, por isso o gerador foi escrito aqui:
     a) monta todas as árvores com os átomos pesados (C, N, O, S, halogênios), juntando
        um átomo por vez a um átomo que ainda tenha valência livre;
     b) acrescenta as insaturações uma a uma: cada passo fecha um anel (liga dois átomos
        ainda não ligados) ou aumenta a ordem de uma ligação (simples -> dupla -> tripla);
     c) em cada passo, estruturas repetidas são descartadas pelo SMILES canônico.
   Toda estrutura final pode ser desmontada de volta até uma árvore tirando insaturações,
   e toda árvore pode ser desmontada tirando folhas; por isso o caminho inverso encontra
   todas. Valências fixas: C 4, N 3, O 2, S 2, halogênios 1; sem cargas (grupos como o
   nitro, que só existem com cargas formais, não são gerados).

2. Estruturas improváveis ficam ocultas por padrão (podem ser mostradas):
   tripla em anel com menos de 8 átomos, dupla em anel de 3 ou 4 átomos, ligação O–O
   (peróxido) e duplas acumuladas C=C=C. Enóis continuam visíveis (tautomeria).

3. classificar_par_isomeros(a, b): tipo de isomeria entre duas estruturas, com o critério
   usado escrito por extenso (função, cadeia, posição, metameria, tautomeria; geométrica
   ou óptica quando a diferença é só espacial).

4. analisar_isomeria_espacial(smiles): isomeria geométrica e óptica de uma estrutura,
   usando as funções de estereoquímica que já existiam no ChemioKit.

Todas as funções devolvem tipos que viram JSON.
"""

from __future__ import annotations

import re
from concurrent.futures import TimeoutError as TempoEsgotado

from rdkit import Chem, RDLogger
from rdkit.Chem.MolStandardize import rdMolStandardize

from . import cache_nomes, glossario, pubchem
from .stereochemistry import (
    _gerar_imagem_especular,
    contar_elementos_estereogenicos,
    gerar_estereoisomeros,
    identificar_centros_quirais,
)
from .utils import validar_smiles

VALENCIAS = {"C": 4, "N": 3, "O": 2, "S": 2, "F": 1, "Cl": 1, "Br": 1, "I": 1}
LIMITE_ATOMOS_PESADOS = 8
LIMITE_ESTRUTURAS = 6000  # interrompe a geração se um passo intermediário passar disso

_ORDEM = {1: Chem.BondType.SINGLE, 2: Chem.BondType.DOUBLE, 3: Chem.BondType.TRIPLE}

# ------------------------------------------------------------------ fórmula


def interpretar_formula(formula: str) -> dict:
    """
    Lê fórmulas como "C4H10O" ou "C2H5Cl" e calcula o número de insaturações
    (anéis + ligações pi) pela fórmula IDH = (2C + 2 + N - H - X) / 2.
    Devolve {"valida", "elementos", "hidrogenios", "atomos_pesados", "insaturacoes", "formula", "erro"}.
    """
    texto = (formula or "").replace(" ", "")
    if not texto or not re.fullmatch(r"([A-Z][a-z]?\d*)+", texto):
        return {"valida": False, "erro": "Escreva a fórmula com os símbolos dos elementos, ex.: C4H10O."}

    contagem: dict[str, int] = {}
    for simbolo, numero in re.findall(r"([A-Z][a-z]?)(\d*)", texto):
        contagem[simbolo] = contagem.get(simbolo, 0) + (int(numero) if numero else 1)

    desconhecidos = sorted(set(contagem) - set(VALENCIAS) - {"H"})
    if desconhecidos:
        return {"valida": False, "erro": f"Elemento(s) não suportado(s): {', '.join(desconhecidos)}. Use C, H, N, O, S, F, Cl, Br, I."}

    hidrogenios = contagem.pop("H", 0)
    if not contagem:
        return {"valida": False, "erro": "A fórmula precisa ter pelo menos um átomo além do hidrogênio."}

    dobro = 2 + sum(n * (VALENCIAS[e] - 2) for e, n in contagem.items()) - hidrogenios
    if dobro < 0 or dobro % 2:
        return {"valida": False, "erro": "Essa fórmula não corresponde a nenhuma molécula neutra com as valências usuais."}

    # Ordem de Hill: C, depois H, depois os demais em ordem alfabética
    def termo(simbolo: str, n: int) -> str:
        return f"{simbolo}{n if n > 1 else ''}" if n else ""

    outros = sorted(e for e in contagem if e != "C")
    formula_hill = termo("C", contagem.get("C", 0)) + termo("H", hidrogenios) + "".join(termo(e, contagem[e]) for e in outros)

    return {
        "valida": True,
        "formula": formula_hill,
        "elementos": contagem,
        "hidrogenios": hidrogenios,
        "atomos_pesados": sum(contagem.values()),
        "insaturacoes": dobro // 2,
        "erro": None,
    }


# ------------------------------------------------------------------ gerador


class _LimiteExcedido(Exception):
    pass


def _montar_mol(elementos: tuple, ligacoes: dict, sanitizar: bool = False) -> Chem.Mol:
    rw = Chem.RWMol()
    for e in elementos:
        atomo = Chem.Atom(e)
        atomo.SetNoImplicit(True)
        rw.AddAtom(atomo)
    usada = [0] * len(elementos)
    for (i, j), ordem in ligacoes.items():
        rw.AddBond(i, j, _ORDEM[ordem])
        usada[i] += ordem
        usada[j] += ordem
    for i, e in enumerate(elementos):
        rw.GetAtomWithIdx(i).SetNumExplicitHs(VALENCIAS[e] - usada[i])
    mol = rw.GetMol()
    if sanitizar:
        Chem.SanitizeMol(mol)
    else:
        mol.UpdatePropertyCache(strict=False)
        Chem.FastFindRings(mol)
    return mol


def _valencia_livre(elementos: tuple, ligacoes: dict) -> list[int]:
    usada = [0] * len(elementos)
    for (i, j), ordem in ligacoes.items():
        usada[i] += ordem
        usada[j] += ordem
    return [VALENCIAS[e] - usada[k] for k, e in enumerate(elementos)]


def _guardar(destino: dict, elementos: tuple, ligacoes: dict):
    chave = Chem.MolToSmiles(_montar_mol(elementos, ligacoes))
    if chave not in destino:
        destino[chave] = (elementos, ligacoes)
        if len(destino) > LIMITE_ESTRUTURAS:
            raise _LimiteExcedido


def _enumerar_constitucionais(elementos: dict[str, int], insaturacoes: int) -> set[str]:
    """SMILES canônicos (RDKit, com aromaticidade) de todos os isômeros constitucionais."""
    nivel: dict = {}
    for e in elementos:
        _guardar(nivel, (e,), {})

    # a) árvores: um átomo novo por vez, ligado a um átomo com valência livre
    for _ in range(sum(elementos.values()) - 1):
        proximo: dict = {}
        for atomos, ligacoes in nivel.values():
            livre = _valencia_livre(atomos, ligacoes)
            restantes = dict(elementos)
            for e in atomos:
                restantes[e] -= 1
            for e, n in restantes.items():
                if n == 0:
                    continue
                for i, li in enumerate(livre):
                    if li >= 1:
                        novas = dict(ligacoes)
                        novas[(i, len(atomos))] = 1
                        _guardar(proximo, atomos + (e,), novas)
        nivel = proximo

    # b) insaturações: fecha um anel ou aumenta a ordem de uma ligação
    for _ in range(insaturacoes):
        proximo = {}
        for atomos, ligacoes in nivel.values():
            livre = _valencia_livre(atomos, ligacoes)
            for i in range(len(atomos)):
                if livre[i] < 1:
                    continue
                for j in range(i + 1, len(atomos)):
                    if livre[j] < 1:
                        continue
                    ordem = ligacoes.get((i, j), 0)
                    if ordem < 3:
                        novas = dict(ligacoes)
                        novas[(i, j)] = ordem + 1
                        _guardar(proximo, atomos, novas)
        nivel = proximo

    finais = set()
    for atomos, ligacoes in nivel.values():
        try:
            finais.add(Chem.MolToSmiles(_montar_mol(atomos, ligacoes, sanitizar=True)))
        except Exception:  # estrutura que o RDKit não consegue sanitizar (rara)
            continue
    return finais


# ------------------------------------------------------------------ funções orgânicas

# Ordem = prioridade de exibição. SMARTS próprios para a isomeria: os de properties.py
# continuam como estão (a aba Propriedades não muda).
FUNCOES_SMARTS = {
    "ácido carboxílico": "[CX3](=O)[OX2H1]",
    "éster": "[CX3](=O)[OX2H0][#6]",
    "amida": "[CX3](=O)[NX3]",
    "aldeído": "[$([CX3H1](=O)[#6]),$([CX3H2]=O)]",
    "cetona": "[#6][CX3](=O)[#6]",
    "nitrila": "[CX2]#[NX1]",
    "álcool": "[OX2H1][CX4]",
    "enol": "[OX2H1][#6X3]=[#6X3]",
    "fenol": "[OX2H1]c",
    "éter": "[OX2;!$(O[#6]=[O,S,N])]([#6])[#6]",
    "amina": "[NX3;!$(N[#6]=[O,S,N]);!$(N[#6]#*)]([#6])",
    "imina": "[CX3]=[NX2]",
    "tiol": "[SX2H1][#6]",
    "sulfeto": "[SX2]([#6])[#6]",
    "haleto orgânico": "[#6][F,Cl,Br,I]",
}
_PADROES = {nome: Chem.MolFromSmarts(s) for nome, s in FUNCOES_SMARTS.items()}


def _subclasse_hidrocarboneto(mol: Chem.Mol) -> str:
    duplas = sum(1 for b in mol.GetBonds() if b.GetBondType() == Chem.BondType.DOUBLE)
    triplas = sum(1 for b in mol.GetBonds() if b.GetBondType() == Chem.BondType.TRIPLE)
    if mol.GetRingInfo().NumRings():
        if any(a.GetIsAromatic() for a in mol.GetAtoms()):
            return "hidrocarboneto aromático"
        if triplas:
            return "cicloalcino"
        if duplas:
            return "cicloalceno"
        return "cicloalcano"
    if duplas and triplas:
        return "alcenino"
    if triplas:
        return {1: "alcino"}.get(triplas, "alcadiino")
    if duplas:
        return {1: "alceno", 2: "alcadieno"}.get(duplas, "alcatrieno")
    return "alcano"


def identificar_funcoes(mol: Chem.Mol) -> list[str]:
    if all(a.GetSymbol() in ("C", "H") for a in mol.GetAtoms()):
        return [_subclasse_hidrocarboneto(mol)]
    funcoes = [nome for nome, p in _PADROES.items() if mol.HasSubstructMatch(p)]
    if not funcoes and any(a.GetIsAromatic() and a.GetSymbol() != "C" for a in mol.GetAtoms()):
        funcoes = ["heterocíclico aromático"]
    return funcoes or ["outra"]


# ------------------------------------------------------------------ classificação da cadeia


def _atomos_da_cadeia(mol: Chem.Mol) -> set[int]:
    """Carbonos + heteroátomos entre carbonos (O, N, S ligados a 2 ou mais carbonos)."""
    cadeia = {a.GetIdx() for a in mol.GetAtoms() if a.GetSymbol() == "C"}
    for a in mol.GetAtoms():
        if a.GetSymbol() in ("O", "N", "S") and sum(v.GetSymbol() == "C" for v in a.GetNeighbors()) >= 2:
            cadeia.add(a.GetIdx())
    return cadeia


def classificar_cadeia(mol: Chem.Mol) -> dict:
    """Classificação escolar da cadeia carbônica."""
    cadeia = _atomos_da_cadeia(mol)
    fechada = mol.GetRingInfo().NumRings() > 0
    heterogenea = any(mol.GetAtomWithIdx(i).GetSymbol() != "C" for i in cadeia)
    insaturada = any(
        b.GetBondType() in (Chem.BondType.DOUBLE, Chem.BondType.TRIPLE, Chem.BondType.AROMATIC)
        and b.GetBeginAtom().GetSymbol() == "C" and b.GetEndAtom().GetSymbol() == "C"
        for b in mol.GetBonds()
    )
    vizinhos_na_cadeia = {
        i: [v.GetIdx() for v in mol.GetAtomWithIdx(i).GetNeighbors() if v.GetIdx() in cadeia] for i in cadeia
    }
    if fechada:
        info = mol.GetRingInfo()
        ramificada = any(
            info.NumAtomRings(i) and any(not info.NumAtomRings(v) for v in vizinhos)
            for i, vizinhos in vizinhos_na_cadeia.items()
        )
    else:
        ramificada = any(len(v) >= 3 for v in vizinhos_na_cadeia.values())
    return {
        "aberta": not fechada,
        "ramificada": ramificada,
        "heterogenea": heterogenea,
        "insaturada": insaturada,
        "aromatica": any(a.GetIsAromatic() for a in mol.GetAtoms()),
    }


def descrever_cadeia(c: dict) -> str:
    partes = [
        "aberta" if c["aberta"] else ("fechada aromática" if c["aromatica"] else "fechada"),
        "ramificada" if c["ramificada"] else ("normal" if c["aberta"] else "não ramificada"),
        "heterogênea" if c["heterogenea"] else "homogênea",
        "insaturada" if c["insaturada"] else "saturada",
    ]
    return ", ".join(partes)


# ------------------------------------------------------------------ estruturas improváveis


def motivos_instabilidade(mol: Chem.Mol) -> list[str]:
    motivos = []
    for b in mol.GetBonds():
        tipo = b.GetBondType()
        if tipo == Chem.BondType.TRIPLE and any(b.IsInRingSize(k) for k in range(3, 8)):
            motivos.append("tripla em anel pequeno")
        if tipo == Chem.BondType.DOUBLE and (b.IsInRingSize(3) or b.IsInRingSize(4)):
            motivos.append("dupla em anel de 3 ou 4 átomos")
        if b.GetBeginAtom().GetSymbol() == "O" and b.GetEndAtom().GetSymbol() == "O":
            motivos.append("ligação O–O (peróxido)")
    for a in mol.GetAtoms():
        duplas_com_c = [
            b for b in a.GetBonds()
            if b.GetBondType() == Chem.BondType.DOUBLE and b.GetOtherAtom(a).GetSymbol() == "C"
        ]
        if a.GetSymbol() == "C" and len(duplas_com_c) >= 2:
            motivos.append("duplas acumuladas C=C=C")
    return sorted(set(motivos))


# ------------------------------------------------------------------ nomes do glossário

_nomes_glossario: dict[str, str] | None = None


def chave_conectividade(mol: Chem.Mol) -> str:
    """Primeiro bloco do InChIKey: igual para estruturas com a mesma constituição."""
    RDLogger.DisableLog("rdApp.*")
    try:
        return Chem.MolToInchiKey(mol)[:14]
    finally:
        RDLogger.EnableLog("rdApp.*")


def _indice_glossario() -> dict[str, str]:
    """Bloco de conectividade -> nome em português (só entradas sem estereoquímica escolhida)."""
    global _nomes_glossario
    if _nomes_glossario is None:
        _nomes_glossario = {}
        for e in glossario.obter().entradas.values():
            if e.tipo != "substancia":
                continue
            mol = Chem.MolFromSmiles(e.smiles)
            if mol is None or any(a.GetChiralTag() != Chem.ChiralType.CHI_UNSPECIFIED for a in mol.GetAtoms()):
                continue
            _nomes_glossario.setdefault(chave_conectividade(mol), e.nome)
    return _nomes_glossario


# ------------------------------------------------------------------ API: gerar


def _resumo_estereo(mol: Chem.Mol) -> dict:
    info = Chem.FindPotentialStereo(mol)
    tetra = [s.centeredOn for s in info if s.type == Chem.StereoType.Atom_Tetrahedral]
    duplas = [s.centeredOn for s in info if s.type == Chem.StereoType.Bond_Double]
    aneis = mol.GetRingInfo().AtomRings()
    cis_trans_anel = any(sum(i in anel for i in tetra) >= 2 for anel in aneis)
    return {
        "centros_estereogenicos": len(tetra),
        "duplas_cis_trans": len(duplas),
        "geometrica": bool(duplas) or cis_trans_anel,
        "possivel_optica": bool(tetra),
    }


def gerar_isomeros(formula: str, mostrar_todos: bool = False, limite_atomos: int = LIMITE_ATOMOS_PESADOS) -> dict:
    """
    Gera os isômeros constitucionais da fórmula. Resultado:
      status: "ok" | "formula_invalida" | "muito_grande"
      formula, insaturacoes, total (todas as estruturas), ocultos (improváveis não mostrados),
      isomeros: [{smiles, funcoes, grupo, cadeia, descricao_cadeia, motivos_instabilidade,
                  estereo (resumo), nome (glossário, se houver), chave_conectividade}]
      grupos: {grupo: [posições na lista isomeros]}
    """
    f = interpretar_formula(formula)
    if not f["valida"]:
        return {"status": "formula_invalida", "mensagem": f["erro"]}
    if f["atomos_pesados"] > limite_atomos:
        return {
            "status": "muito_grande",
            "formula": f["formula"],
            "mensagem": f"{f['formula']} tem {f['atomos_pesados']} átomos além do H. O limite é {limite_atomos}: "
            "acima disso o número de estruturas cresce demais para mostrar na tela.",
        }

    try:
        todos = _enumerar_constitucionais(f["elementos"], f["insaturacoes"])
    except _LimiteExcedido:
        return {
            "status": "muito_grande",
            "formula": f["formula"],
            "mensagem": f"{f['formula']} tem mais de {LIMITE_ESTRUTURAS:,} estruturas possíveis".replace(",", ".")
            + ". Tente uma fórmula com menos átomos ou menos insaturações.",
        }

    nomes = _indice_glossario()
    isomeros = []
    ocultos = 0
    for smiles in sorted(todos, key=lambda s: (len(s), s)):
        mol = Chem.MolFromSmiles(smiles)
        motivos = motivos_instabilidade(mol)
        if motivos and not mostrar_todos:
            ocultos += 1
            continue
        funcoes = identificar_funcoes(mol)
        cadeia = classificar_cadeia(mol)
        chave = chave_conectividade(mol)
        isomeros.append(
            {
                "smiles": smiles,
                "funcoes": funcoes,
                "grupo": " + ".join(funcoes),
                "cadeia": cadeia,
                "descricao_cadeia": descrever_cadeia(cadeia),
                "motivos_instabilidade": motivos,
                "estereo": _resumo_estereo(mol),
                "nome": nomes.get(chave),
                "chave_conectividade": chave,
            }
        )

    grupos: dict[str, list[int]] = {}
    for i, iso in enumerate(isomeros):
        grupos.setdefault(iso["grupo"], []).append(i)

    return {
        "status": "ok",
        "formula": f["formula"],
        "insaturacoes": f["insaturacoes"],
        "total": len(todos),
        "ocultos": ocultos,
        "isomeros": isomeros,
        "grupos": grupos,
    }


# ------------------------------------------------------------------ API: isomeria espacial


def analisar_isomeria_espacial(smiles: str) -> dict | None:
    """
    Isomeria geométrica e óptica de uma estrutura:
      geometrica: True se há dupla C=C com cis/trans ou dois centros num mesmo anel (cis/trans em ciclo);
      centros_estereogenicos, duplas_cis_trans, n (elementos estereogênicos, máximo 2^n);
      estereoisomeros: [{smiles, atividade_optica, configuracoes_duplas (E/Z)}];
      opticamente_ativos, meso: quantos estereoisômeros são ativos e quantos são meso.
    """
    if not validar_smiles(smiles):
        return None
    mol = Chem.MolFromSmiles(smiles.strip())
    resumo = _resumo_estereo(mol)
    lista = []
    for s in gerar_estereoisomeros(smiles):
        m = Chem.MolFromSmiles(s)
        duplas = [
            {"Z": "Z", "E": "E"}.get(str(b.GetStereo()).replace("STEREO", ""), None)
            for b in m.GetBonds()
            if b.GetStereo() in (Chem.BondStereo.STEREOE, Chem.BondStereo.STEREOZ)
        ]
        lista.append(
            {
                "smiles": s,
                "atividade_optica": identificar_centros_quirais(s)["atividade_optica"],
                "configuracoes_duplas": duplas,
            }
        )
    return {
        **resumo,
        "n": contar_elementos_estereogenicos(smiles),
        "estereoisomeros": lista,
        "total_estereoisomeros": len(lista),
        "opticamente_ativos": sum(e["atividade_optica"] == "Opticamente Ativa" for e in lista),
        "meso": sum(e["atividade_optica"] == "Inativa (composto meso)" for e in lista),
    }


# ------------------------------------------------------------------ API: classificar um par


def _descritor_ramo(mol: Chem.Mol, atomos: set[int], ponto: int) -> str:
    """SMILES canônico de um ramo (só ligações simples), marcando o átomo que se liga à cadeia."""
    rw = Chem.RWMol()
    mapa = {}
    for i in sorted(atomos):
        a = Chem.Atom(mol.GetAtomWithIdx(i).GetAtomicNum())
        a.SetNoImplicit(True)
        if i == ponto:
            a.SetIsotope(1)  # marca o ponto de ligação
        mapa[i] = rw.AddAtom(a)
    for b in mol.GetBonds():
        i, j = b.GetBeginAtomIdx(), b.GetEndAtomIdx()
        if i in atomos and j in atomos:
            rw.AddBond(mapa[i], mapa[j], Chem.BondType.SINGLE)
    return Chem.MolToSmiles(rw.GetMol())


def _componentes(vizinhos: dict[int, list[int]], atomos: set[int]) -> list[set[int]]:
    vistos, comps = set(), []
    for inicio in atomos:
        if inicio in vistos:
            continue
        pilha, comp = [inicio], set()
        while pilha:
            x = pilha.pop()
            if x in comp:
                continue
            comp.add(x)
            pilha.extend(v for v in vizinhos[x] if v in atomos and v not in comp)
        vistos |= comp
        comps.append(comp)
    return comps


def _caminhos_mais_longos(vizinhos: dict[int, list[int]], atomos: set[int]) -> list[list[int]]:
    melhores: list[list[int]] = []

    def andar(caminho):
        nonlocal melhores
        estendeu = False
        for v in vizinhos[caminho[-1]]:
            if v in atomos and v not in caminho:
                estendeu = True
                andar(caminho + [v])
        if not estendeu:
            if not melhores or len(caminho) > len(melhores[0]):
                melhores = [caminho]
            elif len(caminho) == len(melhores[0]):
                melhores.append(caminho)

    for a in atomos:
        andar([a])
    return melhores


def _assinatura_esqueleto(mol: Chem.Mol) -> tuple:
    """
    Assinatura da cadeia (carbonos + heteroátomos entre carbonos) sem as posições: para
    cada parte, o tamanho da cadeia principal (ou os anéis) e quais ramos ela tem.
    Mesma assinatura = mesma cadeia principal e mesmos ramos (diferença só de posição).
    """
    cadeia = _atomos_da_cadeia(mol)
    vizinhos = {i: [v.GetIdx() for v in mol.GetAtomWithIdx(i).GetNeighbors() if v.GetIdx() in cadeia] for i in cadeia}
    info = mol.GetRingInfo()
    partes = []
    for comp in _componentes(vizinhos, cadeia):
        em_anel = {i for i in comp if any(i in r and all(x in cadeia for x in r) for r in info.AtomRings())}
        if em_anel:
            nucleo = em_anel
            rotulo_nucleo = ("anel", _descritor_ramo(mol, nucleo, -1))
        else:
            candidatos = []
            for caminho in _caminhos_mais_longos(vizinhos, comp):
                ramos = []
                for resto in _componentes(vizinhos, comp - set(caminho)):
                    ponto = next(i for i in resto if any(v in caminho for v in vizinhos[i]))
                    ramos.append(_descritor_ramo(mol, resto, ponto))
                candidatos.append((-len(ramos), tuple(sorted(ramos))))
            n_ramos, ramos = min(candidatos)
            partes.append(("cadeia", len(_caminhos_mais_longos(vizinhos, comp)[0]), ramos))
            continue
        ramos = []
        for resto in _componentes(vizinhos, comp - nucleo):
            ponto = next(i for i in resto if any(v in nucleo for v in vizinhos[i]))
            ramos.append(_descritor_ramo(mol, resto, ponto))
        partes.append((*rotulo_nucleo, tuple(sorted(ramos))))
    return tuple(sorted(partes, key=str))


def _particao_heteroatomos(mol: Chem.Mol) -> tuple:
    """Para cada heteroátomo da cadeia: quantos carbonos há de cada lado (metameria)."""
    cadeia = _atomos_da_cadeia(mol)
    pesados = {a.GetIdx() for a in mol.GetAtoms()}
    vizinhos = {i: [v.GetIdx() for v in mol.GetAtomWithIdx(i).GetNeighbors()] for i in pesados}
    resultado = []
    for h in sorted(i for i in cadeia if mol.GetAtomWithIdx(i).GetSymbol() != "C"):
        lados = []
        for comp in _componentes(vizinhos, pesados - {h}):
            if any(v in comp for v in vizinhos[h]):
                lados.append(sum(mol.GetAtomWithIdx(i).GetSymbol() == "C" for i in comp))
        resultado.append((mol.GetAtomWithIdx(h).GetSymbol(), tuple(sorted(lados))))
    return tuple(sorted(resultado))


def _sem_estereo(mol: Chem.Mol) -> str:
    m = Chem.Mol(mol)
    Chem.RemoveStereochemistry(m)
    return Chem.MolToSmiles(m)


def _tipo_tautomeria(fa: set, fb: set) -> str:
    juntas = fa | fb
    if "enol" in juntas and "aldeído" in juntas:
        return "tautomeria aldoenólica"
    if "enol" in juntas and "cetona" in juntas:
        return "tautomeria cetoenólica"
    if "imina" in juntas and "amina" in juntas:
        return "tautomeria imina-enamina"
    return "tautomeria"


def _classificar_espacial(ma: Chem.Mol, mb: Chem.Mol) -> dict:
    sa, sb = Chem.MolToSmiles(ma), Chem.MolToSmiles(mb)
    if Chem.MolToSmiles(_gerar_imagem_especular(ma)) == sb:
        return {"tipo": "óptica", "subtipo": "enantiômeros",
                "explicacao": "Mesma constituição; uma é a imagem especular não sobreponível da outra."}

    def sem_duplas(m):
        m = Chem.Mol(m)
        for b in m.GetBonds():
            b.SetStereo(Chem.BondStereo.STEREONONE)
        return Chem.MolToSmiles(m)

    if sem_duplas(ma) == sem_duplas(mb):
        return {"tipo": "geométrica", "subtipo": "cis-trans (E/Z)",
                "explicacao": "Mesma constituição; diferem só na disposição dos grupos em torno de uma ligação dupla."}

    # Centros com configuração diferente num mesmo anel = cis/trans em ciclo
    centros_a = dict(Chem.FindMolChiralCenters(ma, includeUnassigned=True, useLegacyImplementation=False))
    centros_b = dict(Chem.FindMolChiralCenters(mb, includeUnassigned=True, useLegacyImplementation=False))
    if centros_a.keys() == centros_b.keys() and sa != sb:
        aneis = ma.GetRingInfo().AtomRings()
        tetra = list(centros_a)
        if any(sum(i in anel for i in tetra) >= 2 for anel in aneis):
            return {"tipo": "geométrica", "subtipo": "cis-trans em ciclo",
                    "explicacao": "Mesma constituição; os substituintes estão do mesmo lado (cis) ou em lados opostos (trans) do anel. "
                    "Também são diastereoisômeros."}
    return {"tipo": "óptica", "subtipo": "diastereoisômeros",
            "explicacao": "Mesma constituição e estereoisômeros que não são imagens especulares um do outro."}


def classificar_par_isomeros(smiles_a: str, smiles_b: str) -> dict | None:
    """
    Tipo de isomeria entre duas estruturas. Resultado:
      {"relacao": "mesma substância" | "não são isômeros" | "plana" | "espacial",
       "tipo", "subtipo", "explicacao", "funcoes_a", "funcoes_b"}
    Critérios (isomeria plana), na ordem:
      1. tautomeria: uma se converte na outra por migração de H (enumerador de tautômeros do RDKit);
      2. função: funções diferentes (para hidrocarbonetos: alcano, alceno, alcino, alcadieno...;
         cadeia aberta × fechada conta como cadeia, ex.: alceno × cicloalcano);
      3. cadeia: mesma função, mas cadeia aberta × fechada ou homogênea × heterogênea;
      4. metameria: mesma função, cadeias heterogêneas e heteroátomo em outra posição
         (muda o número de carbonos de cada lado dele);
      5. cadeia: normal × ramificada, ou cadeia principal ou ramos diferentes;
      6. posição: mesma cadeia principal e mesmos ramos; muda só a posição do grupo
         funcional, da insaturação ou do ramo.
    """
    if not (validar_smiles(smiles_a) and validar_smiles(smiles_b)):
        return None
    ma = Chem.MolFromSmiles(smiles_a.strip())
    mb = Chem.MolFromSmiles(smiles_b.strip())
    fa, fb = identificar_funcoes(ma), identificar_funcoes(mb)
    base = {"funcoes_a": fa, "funcoes_b": fb}

    from rdkit.Chem.rdMolDescriptors import CalcMolFormula

    if CalcMolFormula(ma) != CalcMolFormula(mb):
        return {**base, "relacao": "não são isômeros", "tipo": None, "subtipo": None,
                "explicacao": f"As fórmulas moleculares são diferentes ({CalcMolFormula(ma)} e {CalcMolFormula(mb)})."}

    if Chem.MolToSmiles(ma) == Chem.MolToSmiles(mb):
        return {**base, "relacao": "mesma substância", "tipo": None, "subtipo": None,
                "explicacao": "As duas estruturas representam a mesma substância."}

    if _sem_estereo(ma) == _sem_estereo(mb):
        return {**base, "relacao": "espacial", **_classificar_espacial(ma, mb)}

    plana = {**base, "relacao": "plana"}
    ca, cb = classificar_cadeia(ma), classificar_cadeia(mb)

    # 1. tautomeria
    enumerador = rdMolStandardize.TautomerEnumerator()
    RDLogger.DisableLog("rdApp.*")
    try:
        tautomeros_a = {_sem_estereo(t) for t in enumerador.Enumerate(ma)}
    finally:
        RDLogger.EnableLog("rdApp.*")
    if _sem_estereo(mb) in tautomeros_a and set(fa) != set(fb):
        return {**plana, "tipo": "tautomeria", "subtipo": _tipo_tautomeria(set(fa), set(fb)),
                "explicacao": f"Funções diferentes ({', '.join(fa)} × {', '.join(fb)}) que se interconvertem "
                "pela migração de um hidrogênio, em equilíbrio dinâmico."}

    hidrocarbonetos = all(a.GetSymbol() == "C" for a in ma.GetAtoms()) and all(a.GetSymbol() == "C" for a in mb.GetAtoms())

    # 2. função
    if set(fa) != set(fb):
        if hidrocarbonetos and ca["aberta"] != cb["aberta"]:
            return {**plana, "tipo": "cadeia", "subtipo": "aberta × fechada",
                    "explicacao": f"Hidrocarbonetos de cadeia aberta e fechada ({fa[0]} × {fb[0]})."}
        if hidrocarbonetos and not ca["aberta"] and not cb["aberta"]:
            return {**plana, "tipo": "cadeia", "subtipo": "cadeias fechadas diferentes",
                    "explicacao": f"Hidrocarbonetos cíclicos com cadeias diferentes ({fa[0]} × {fb[0]})."}
        return {**plana, "tipo": "função", "subtipo": None,
                "explicacao": f"Funções diferentes: {', '.join(fa)} × {', '.join(fb)}."}

    funcao = ", ".join(fa)

    # 3. cadeia: aberta × fechada ou homogênea × heterogênea
    if ca["aberta"] != cb["aberta"]:
        return {**plana, "tipo": "cadeia", "subtipo": "aberta × fechada",
                "explicacao": f"Mesma função ({funcao}); uma cadeia é aberta e a outra fechada."}
    if ca["heterogenea"] != cb["heterogenea"]:
        return {**plana, "tipo": "cadeia", "subtipo": "homogênea × heterogênea",
                "explicacao": f"Mesma função ({funcao}); uma cadeia é homogênea e a outra heterogênea."}

    # 4. metameria
    if ca["heterogenea"] and _particao_heteroatomos(ma) != _particao_heteroatomos(mb):
        return {**plana, "tipo": "metameria", "subtipo": "compensação",
                "explicacao": f"Mesma função ({funcao}) e cadeias heterogêneas; o heteroátomo está em outra posição "
                "(muda o número de carbonos de cada lado dele)."}

    # 5. cadeia normal × ramificada
    if ca["ramificada"] != cb["ramificada"]:
        return {**plana, "tipo": "cadeia", "subtipo": "normal × ramificada",
                "explicacao": f"Mesma função ({funcao}); uma cadeia é ramificada e a outra não."}

    # 6 e 7. cadeia principal/ramos × posição
    if _assinatura_esqueleto(ma) != _assinatura_esqueleto(mb):
        return {**plana, "tipo": "cadeia", "subtipo": "cadeias diferentes",
                "explicacao": f"Mesma função ({funcao}); a cadeia principal ou os ramos são diferentes "
                f"({descrever_cadeia(ca)} × {descrever_cadeia(cb)})."}
    return {**plana, "tipo": "posição", "subtipo": None,
            "explicacao": f"Mesma função ({funcao}), mesma cadeia principal e mesmos ramos; muda a posição "
            "do grupo funcional, da insaturação ou do ramo."}


# ------------------------------------------------------------------ API: nomes pelo PubChem


def buscar_nomes_isomeros(formula: str, tempo_limite: float = pubchem.TEMPO_LIMITE_FORMULA) -> dict:
    """
    Nomes (em inglês) dos compostos já cadastrados no PubChem com essa fórmula, para
    identificar os isômeros gerados que são substâncias conhecidas. Ordem: cache local,
    depois PubChem com tempo limite. Resultado:
      {"status": "ok" | "pubchem_indisponivel" | "formula_invalida", "fonte": "cache" | "pubchem",
       "nomes": {chave_conectividade: {"cid", "nome"}}, "mensagem"}
    Cruze com "chave_conectividade" de cada isômero de gerar_isomeros().
    """
    f = interpretar_formula(formula)
    if not f["valida"]:
        return {"status": "formula_invalida", "nomes": {}, "mensagem": f["erro"]}
    chave = f["formula"]

    guardado = cache_nomes.obter_formula(chave)
    if guardado is not None:
        return {"status": "ok", "fonte": "cache", "nomes": guardado}

    try:
        nomes = pubchem.consultar_formula_com_tempo_limite(chave, tempo_limite)
    except TempoEsgotado:
        return {"status": "pubchem_indisponivel", "motivo": "tempo_esgotado", "nomes": {},
                "mensagem": f"O PubChem não respondeu em {tempo_limite:g} s."}
    except Exception as e:  # sem rede, erro HTTP, resposta inesperada
        return {"status": "pubchem_indisponivel", "motivo": "sem_conexao", "nomes": {},
                "mensagem": f"Não foi possível consultar o PubChem ({type(e).__name__})."}

    cache_nomes.salvar_formula(chave, nomes)
    return {"status": "ok", "fonte": "pubchem", "nomes": nomes}
