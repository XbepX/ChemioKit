# Resumo técnico — ChemioChat (`chemio_tools` + `ui`)

> Levantado a partir do código-fonte em `ChemioChat/` (29/10/2026). Fontes: `app.py`, `chemio_tools/*.py`, `ui/*.py`, `pyproject.toml`, `requirements.txt`, `uv.lock`, `.venv/pyvenv.cfg`, `testes/testes_core.ipynb`, `README.md` e `arquitetura_projeto_chemiochat.md`.
> Quando um comportamento não ficava claro só pela leitura, executei as funções de `chemio_tools` com RDKit 2026.3.5 (mesma versão do `uv.lock`) em um ambiente separado. Os resultados dessas execuções aparecem como **"Teste:"**.

**Sobre o `arquitetura_projeto_chemiochat.md`:** é uma cópia antiga e incompleta do código, gerada por `documenta_projeto.py`. O script corta cada arquivo em 3000 caracteres, ignora notebooks e grava a saída como `arquitetura_projeto.md`, nome que ainda aparece na árvore do documento. Por isso `core.py`, `visualization.py`, `tab_visualization.py`, `README.md` e `requirements.txt` aparecem cortados nele. Neste resumo, a referência é sempre o código atual.

**Três nomes no repositório:** a interface usa "ChemioChat" (`app.py`, `README.md`), o `pyproject.toml` usa `name = "quimiolab"`, e o ambiente virtual e o kernel do notebook também se chamam `quimiolab`.

---

## 1. Estrutura de pastas e papel de cada módulo

```text
ChemioChat/
├── app.py                    # Ponto de entrada Streamlit: entrada → validação → 3 abas
├── chemio_tools/             # Motor químico (RDKit + py3Dmol), sem dependência de Streamlit
│   ├── __init__.py           # Expõe a API pública (10 funções em __all__)
│   ├── utils.py              # Validação de SMILES e numeração C1, C2...
│   ├── properties.py         # Descritores físico-químicos + grupos funcionais (SMARTS)
│   ├── stereochemistry.py    # Centros quirais (R/S), atividade óptica, enumeração de estereoisômeros
│   ├── visualization.py      # Imagem 2D (RDKit Draw) e HTML 3D (py3Dmol)
│   ├── io_handlers.py        # Importação .mol/.sdf/.pdb → SMILES; exportação 3D .sdf/.pdb
│   ├── core.py               # Versão monolítica anterior — NÃO é importada por nenhum arquivo
│   └── formatters.py         # Arquivo vazio (0 linhas)
├── ui/                       # Camada de interface (Streamlit)
│   ├── __init__.py           # Expõe as 4 funções de renderização
│   ├── inputs.py             # Campo SMILES, histórico/exemplos, upload de arquivo
│   ├── tab_visualization.py  # Aba 1: 2D/3D, grupos funcionais, estereoquímica, galeria de isômeros
│   ├── tab_properties.py     # Aba 2: métricas e contagem de átomos
│   └── tab_exportes.py       # Aba 3: download .sdf/.pdb
├── testes/testes_core.ipynb  # Notebook exploratório (ver seção 5)
├── documenta_projeto.py      # Gera o relatório de arquitetura em Markdown
├── pyproject.toml / uv.lock / requirements.txt / packages.txt
└── README.md
```

### Fluxo do `app.py`

1. `renderizar_secao_entradas()` devolve uma string SMILES, digitada ou extraída de um arquivo enviado.
2. `validar_smiles()` testa a string. Se for inválida, o app mostra um erro e para (`st.stop()`).
3. Quando o SMILES muda, o app volta ao estado inicial: painéis de estereoquímica e de isômeros fechados, nenhum grupo funcional destacado.
4. Três abas: "Visualização & Análise Interativa", "Propriedades & Composição" e "Exportar Estrutura".

A UI só fala com o motor pelas funções de `chemio_tools` e passa sempre uma string SMILES. É essa separação que permite reaproveitar o motor como toolkit.

### `core.py`

- Reúne em um único arquivo 8 das 10 funções públicas (`validar_smiles`, `obter_mapa_carbonos`, `obter_propriedades_basicas`, `identificar_centros_quirais`, `identificar_grupos_funcionais`, `gerar_estereoisomeros`, `gerar_imagem_2d`, `gerar_html_3d`). Não tem as funções de I/O.
- A data de modificação é anterior à dos módulos separados, e nenhum `.py` ou notebook importa `core`. Tudo indica que é a versão anterior à divisão em módulos, deixada no repositório.
- Diferenças em relação aos módulos atuais:
  - `GRUPOS_SMARTS` não tem **Fenol** (8 grupos em vez de 9). Teste: o fenol não é detectado pela versão do `core`.
  - `gerar_html_3d` não tem o parâmetro `raio_malha_quiral`; o raio fica fixo em 1.2 Å.
  - O destaque de centros quirais (2D e 3D) não usa `flagPossibleStereoCenters=True`.
  - `import math` não é usado.

### `formatters.py`

Arquivo vazio. Não tem funções e não é importado.

---

## 2. Funções públicas de `chemio_tools`

Todas as funções exportadas em `chemio_tools/__init__.py` recebem SMILES como `str`, com exceção de `obter_mapa_carbonos` e `carregar_mol_de_texto`.

| Função (módulo) | Entrada | Saída | O que faz |
|---|---|---|---|
| `validar_smiles` (utils) | `smiles: str` | `bool` | `Chem.MolFromSmiles` ≠ `None` |
| `obter_mapa_carbonos` (utils) | `mol: Chem.Mol` | `dict[int, str]` | Associa o índice RDKit de cada carbono a "C1", "C2"… **na ordem de leitura do SMILES** (não é numeração IUPAC). Teste: no 2-butanol (`CCC(C)O`), o centro quiral recebe o rótulo **C3**. |
| `obter_propriedades_basicas` (properties) | `smiles` | `dict \| None`: `formula`, `massa_molecular`, `logp`, `tpsa` (2 casas decimais), `contagem_elementos` (com H explícitos) | `CalcMolFormula`, `Descriptors.MolWt`, `Descriptors.MolLogP`, `Descriptors.TPSA` e contagem de átomos após `AddHs` |
| `identificar_grupos_funcionais` (properties) | `smiles` | `list[{"grupo": str, "indices": list[int]}]` | Busca os 9 padrões de `GRUPOS_SMARTS` com `GetSubstructMatches` e devolve os índices dos átomos encontrados |
| `identificar_centros_quirais` (stereochemistry) | `smiles` | `dict \| None`: `centros` (`indice_rdkit`, `rotulo_carbono`, `elemento`, `configuracao`), `total_centros`, `opticamente_ativo`, `tem_centros` | `AssignStereochemistry(force=True)` + `FindMolChiralCenters(includeUnassigned=True)`. Configuração `?` vira "Não especificada (?)". |
| `gerar_estereoisomeros` (stereochemistry) | `smiles` | `list[str]` (SMILES isoméricos) | `EnumerateStereoisomers` com `onlyUnassigned=False, unique=True` |
| `gerar_imagem_2d` (visualization) | `smiles` + `mostrar_h`, `destacar_quirais`, `mostrar_indices`, `mostrar_metilas`, `espessura_linha`, `tamanho_fonte`, `fundo_escuro`, `indices_destaque_extra` | Imagem PIL 500×420 px (ou `None`) | Desenho 2D com `Draw.MolToImage`; os rótulos são gravados como `atomNote` e o destaque usa `highlightAtoms` |
| `gerar_html_3d` (visualization) | `smiles` + `estilo`, `mostrar_h`, `fundo_escuro`, `superficie`, `coloracao_superficie`, `opacidade_superficie`, `auto_spin`, `destacar_quirais`, `espessura_3d`, `esquema_cor`, `raio_malha_quiral` | `str` HTML (ou `None` se a geometria 3D falhar) | Adiciona H, gera coordenadas com `EmbedMolecule(randomSeed=42)`, otimiza com `MMFFOptimizeMolecule`, calcula cargas de Gasteiger e monta um viewer py3Dmol 520×420 |
| `carregar_mol_de_texto` (io_handlers) | `conteudo_texto: str`, `formato: "MOL"\|"SDF"\|"PDB"` | `str \| None` (SMILES) | MOL/SDF → `MolFromMolBlock`; PDB → `MolFromPDBBlock`; depois converte para SMILES |
| `exportar_bloco_3d` (io_handlers) | `smiles`, `formato: "SDF"\|"PDB"` | `str \| None` | `AddHs` + `EmbedMolecule(randomSeed=42)` + `MMFFOptimizeMolecule` → `MolToMolBlock` ou `MolToPDBBlock` |

### Candidatas a tools para um agente LLM (tool calling)

| Prioridade | Função | Por quê |
|---|---|---|
| **Alta** | `obter_propriedades_basicas`, `identificar_grupos_funcionais`, `identificar_centros_quirais`, `gerar_estereoisomeros`, `validar_smiles` | Recebem um SMILES (`str`) e devolvem `dict`, `list` ou `bool`, tipos que viram JSON diretamente. É o caso típico de tool determinística: o LLM fornece o SMILES e o RDKit faz o cálculo. |
| **Alta (precisa de adaptador)** | `gerar_imagem_2d` | É a função central da tese do artigo: o LLM não desenha, ele chama o renderizador determinístico. Mas ela devolve um objeto PIL, então seria preciso serializar a imagem (PNG/base64 ou arquivo) para expô-la como tool. |
| **Média** | `exportar_bloco_3d`, `carregar_mol_de_texto` | Entrada e saída em texto. Úteis para um agente que gera arquivos para Avogadro/PyMOL ou lê arquivos enviados pelo usuário. |
| **Baixa** | `gerar_html_3d` | O HTML serve para a interface exibir, não para o modelo ler. Como tool, faria sentido só se o front-end renderizasse o retorno. |
| — | `obter_mapa_carbonos` | Recebe `Chem.Mol`, que não pode ser passado como JSON. É um auxiliar interno. |

Pontos do código que importam para essa adaptação:

- **SMILES inválido e resultado vazio dão o mesmo retorno.** As funções devolvem `None` ou `[]` sem mensagem de erro. Em `identificar_grupos_funcionais` e `gerar_estereoisomeros`, um SMILES inválido também retorna `[]`, então o agente não sabe se a molécula não tem grupos/isômeros ou se o SMILES estava errado.
- **Parâmetros de estilo usam os rótulos da UI.** Exemplos: `estilo="Wireframe / Line"`, `superficie="Superfície Acessível ao Solvente (SAS)"`, `esquema_cor="Carbono Preto (CPK)"`. Num schema de tool, isso viraria `enum` com essas strings exatas, ou exigiria desacoplar valores internos dos rótulos.
- **Índices são do RDKit (base 0, só átomos pesados).** `indices` (grupos) e `indice_rdkit` (centros quirais) seguem essa indexação. São os mesmos índices aceitos por `indices_destaque_extra` em `gerar_imagem_2d`, então as funções já podem ser encadeadas: identificar → destacar.

---

## 3. O que a interface oferece hoje (comparado com a lista)

Legenda: ✅ existe como descrito · ⚠️ existe, mas é diferente ou tem ressalva · ❌ não existe

### Visualização 2D (`tab_visualization.py` → `gerar_imagem_2d`)

| Item | Status | Como está no código |
|---|---|---|
| H explícitos | ✅ | Checkbox "Hidrogênios explícitos" (desligado por padrão) → `Chem.AddHs` |
| Índices de C | ✅ (ressalva) | Checkbox "Índices dos carbonos (C1, C2...)" (**ligado** por padrão). A numeração segue a ordem do SMILES, não a IUPAC. |
| Metilas | ✅ | Checkbox "Exibir metilas (-CH₃)" → `opts.explicitMethyl` |
| Centros quirais R/S | ✅ | Checkbox "Destacar quirais (* e R/S)": o átomo é destacado e recebe o rótulo `(R)*`/`(S)*`, ou só `*` quando a configuração não está definida |
| Traço / fonte / fundo escuro | ✅ | Sliders "Espessura da linha" (1–5, padrão 2) e "Tamanho do texto" (8–20, padrão 12); checkbox "Fundo escuro" (RGB 0.15/0.17/0.22) |
| *Extra (fora da lista)* | — | Destaque do grupo funcional selecionado (`indices_destaque_extra`); tamanho fixo de 500×420 px |

### Visualização 3D (`gerar_html_3d`)

| Item | Status | Como está no código |
|---|---|---|
| Ball & Stick | ✅ | Opção padrão: `stick` (raio = espessura×0.03) + `sphere` (scale 0.25) |
| Wireframe | ⚠️ | Opção "Wireframe / Line". Não usa o estilo `line` do py3Dmol: é `stick` com raio fino (0.02×espessura). |
| Stick | ✅ | "Stick (Bastonetes)": `stick` com raio = espessura×0.04 |
| CPK | ✅ (ressalva) | "CPK / Esferas": `sphere` com `scale 0.8`. Existe também um esquema de cor chamado "Carbono Preto (CPK)" (`blackCarbon`), que é outra coisa. |
| Superfície VDW | ✅ | `py3Dmol.VDW` |
| Superfície SAS | ✅ | `py3Dmol.SAS` |
| Superfície eletrostática | ⚠️ | **Não é um tipo de superfície.** É uma opção de *coloração* ("Mapa Eletrostático (MEP)") aplicada à VDW ou à SAS. Teste: o código passa `colorscheme: "electrostatic"`, mas essa string não existe no 3Dmol.js 2.5.5, a versão que o py3Dmol 2.5.5 carrega. Nesse caso, a função `getColorFromStyle` do 3Dmol.js usa a cor padrão do átomo. Além disso, as cargas de Gasteiger são calculadas, mas não chegam ao viewer: ficam na propriedade interna `_GasteigerCharge`, que `MolToMolBlock` não exporta. **Antes de citar "mapa eletrostático" no artigo, vale conferir visualmente.** |
| Auto-rotação | ✅ | Checkbox "Giro automático (Spin)" → `view.spin(True)` |
| Destaque quiral | ✅ | Checkbox "Destacar quirais (Malha 3D)": esfera em wireframe azul (#00aaff, opacidade 0.45) com raio ajustável de 0.8 a 2.5 Å (padrão 1.2) |
| *Extras (fora da lista)* | — | 4 esquemas de cor (o padrão da UI é "Monocromático Escuro", primeiro da lista, embora o padrão da função seja Jmol); slider de espessura (1–10, padrão 5); opção de mostrar H (ligada por padrão); slider de opacidade da superfície (0.1–1.0); fundo escuro; cor azul-clara para a superfície |

### Grupos funcionais por SMARTS (`properties.GRUPOS_SMARTS`)

| Grupo | Status | SMARTS |
|---|---|---|
| Fenol | ✅ | `[OX2H1][c]` |
| Álcool | ✅ | `[OX2H1][CX4]` |
| Ácido carboxílico | ✅ | `[CX3](=O)[OX2H1]` |
| Aldeído | ✅ | `[CX3H1](=O)` |
| Cetona | ✅ | `[#6][CX3](=O)[#6]` |
| Amina | ✅ | `[NX3;!$(NC=O)]` |
| Éster | ✅ | `[CX3](=O)[OX2H0][#6]` |
| Éter | ✅ | `[OD2]([#6])[#6]` |
| Amida | ✅ | `[CX3](=O)[NX3]` |

- **Painel interativo:** só aparece no modo 2D. Há um botão por grupo encontrado, que destaca os átomos do grupo no desenho, e um botão "Limpar Destaque".
- **Sobreposições observadas nos testes** (consequência dos padrões SMARTS, útil para uma seção de limitações):

| Molécula | Grupos retornados | Por quê |
|---|---|---|
| Acetato de etila | Éster **+ Éter** | O O do éster também casa com o padrão de éter |
| Ácido fórmico | Ácido carboxílico **+ Aldeído** | — |
| Formiato de metila | Aldeído + Éster + Éter | — |
| Nitrometano | **Amina** | O N do nitro tem X3 |
| Piridina | Nenhum grupo | — |

### Estereoisômeros 2^n com galeria

| Item | Status | Como está no código |
|---|---|---|
| Galeria | ✅ | Botão "Verificar Isômeros Possíveis": 4 imagens 2D por linha, cada uma com o SMILES abaixo |
| Contagem 2^n | ⚠️ | A UI diz "Total de combinações geradas (2^n)", mas o número exibido é o total de isômeros **únicos** gerados pelo RDKit (`unique=True`), contando também ligações duplas (E/Z). Teste: ácido tartárico → **3** (não 4: o meso não é contado duas vezes); but-2-eno → 2 (sem centro quiral); glicose aberta, exemplo padrão da UI → 16 = 2⁴. Como `onlyUnassigned=False`, a enumeração inclui centros já definidos no SMILES. |
| Atividade óptica (não estava na lista, mas faz parte do mesmo painel) | ⚠️ | O botão "Analisar Estereoquímica" lista os centros com rótulo, índice e configuração. O critério do código é: a molécula é "opticamente ativa" se tiver ao menos um centro com R ou S atribuído. Teste: o ácido meso-tartárico (R,S) aparece como "✨ Opticamente Ativa"; SMILES sem estereoquímica definida aparece como "⚪ Inativa / Indefinida". |

### Propriedades (`tab_properties.py`)

| Item | Status | Como está no código |
|---|---|---|
| Fórmula | ✅ | `CalcMolFormula` |
| Massa | ✅ | `MolWt`, em g/mol |
| LogP | ✅ | `MolLogP` |
| TPSA | ✅ | `TPSA`, em Å² |
| Estequiometria | ✅ | "Contagem de Átomos (Com H Explícitos)", um card por elemento |

### Importação e exportação

| Item | Status | Como está no código |
|---|---|---|
| Importar .mol / .sdf / .pdb | ✅ (ressalvas) | Expander com `file_uploader` (aceita mol, sdf, pdb). O conteúdo é lido em UTF-8 e **convertido para SMILES**: as coordenadas do arquivo são descartadas e o app gera outra geometria a partir do SMILES. Teste: num SDF com várias moléculas, só a primeira é lida. O SMILES importado vai para o histórico. |
| Exportar .sdf / .pdb | ✅ | Dois `download_button` (`molecula_3d.sdf`, `molecula_3d.pdb`) com geometria otimizada por MMFF (seed 42). O ".sdf" é um MolBlock único, sem o terminador `$$$$`. Teste: exportar e reimportar preserva a estrutura e a estereoquímica, por exemplo (R)-2-butanol, ácido acético e benzeno. |

### Outros itens da interface

- **Entrada:** campo de SMILES com uma lista "Histórico / Exemplos". Os exemplos iniciais são glicose de cadeia aberta (padrão), ácido acético, etanol e benzeno. Cada SMILES novo entra no início da lista.
- **Validação:** mensagem de sucesso ou erro e exibição do SMILES capturado.
- **Interface conversacional / LLM: ❌ não existe no código atual.** Não há chat nem chamada a modelo. O pacote `ollama` está nas dependências, mas nenhum arquivo o importa, e o `.gitignore` reserva `.chroma_db/` para um "RAG futuro". **No artigo, a integração com LLM deve ser descrita como proposta ou trabalho futuro, não como funcionalidade existente.**

---

## 4. Versões das bibliotecas

| Pacote | Restrição no `pyproject.toml` | Versão resolvida (`uv.lock` = `requirements.txt` = `.venv`) | Usado no código? |
|---|---|---|---|
| Python | `>=3.12,<3.13` | 3.12.13 (`.venv`, criado com uv 0.11.7) | — |
| rdkit | (sem restrição) | **2026.3.5** | Sim |
| streamlit | (sem restrição) | **1.61.1** | Sim |
| py3dmol | `>=2.5.4` | **2.5.5** (carrega o 3Dmol.js 2.5.5 via jsDelivr) | Sim |
| numpy | `<2` | 1.26.4 | Não é importado diretamente |
| pandas | `<3` | 2.3.3 | Não é importado diretamente |
| pillow | (dependência indireta) | 12.3.0 | Tipo de retorno de `gerar_imagem_2d` |
| ollama | (sem restrição) | 0.6.2 | **Não** |
| pubchempy | `>=1.0.5` | 1.0.5 | **Não** |
| ipykernel | (sem restrição) | 7.3.0 | Só no notebook |

- `packages.txt` lista bibliotecas de sistema: `libxrender1`, `libxext6`, `libcairo2`, `libgl1`.
- **O README não bate com o projeto em alguns pontos:**
  - Os badges indicam "Python 3.10+" e "Streamlit 1.30+", mas o `pyproject.toml` exige 3.12 e o lock usa Streamlit 1.61.1.
  - Há um badge de licença MIT, mas não existe arquivo `LICENSE` na raiz.
  - A árvore de arquitetura do README não mostra `core.py` nem `formatters.py`.

---

## 5. O que existe em `testes/`

Só há um arquivo, **`testes_core.ipynb`**: 36 células, kernel `quimiolab (3.12.13)`.

- **Não é uma suíte de testes.** Não usa pytest, não tem `assert` e **não importa `chemio_tools`**. O README chama a pasta de "Testes unitários do motor químico", mas o conteúdo é um notebook de prototipagem que usa RDKit e py3Dmol diretamente, com o ácido lático (`CC(O)C(=O)O`) como molécula principal.
- **Conteúdo, na ordem:**
  1. Protótipo mínimo: SMILES → `Mol` → `Draw.MolToImage`, e viewer py3Dmol em `stick` e `stick+sphere`.
  2. Fórmula molecular e contagem de elementos com `Counter`, após `AddHs`.
  3. 3D com H e geometria otimizada (`EmbedMolecule` + `MMFFOptimizeMolecule`) para o CH₄, em Ball & Stick com Jmol. O texto fala em sp³, sp² e sp, mas só o caso sp³ tem código.
  4. Superfície VDW da água colorida por carga parcial (`colorscheme` com `prop: "partialcharge"` e gradiente `rwb`), após `ComputeGasteigerCharges`. É uma abordagem diferente da usada no app (`"electrostatic"`).
  5. Descritores: massa, LogP, TPSA; doadores e aceitadores de ligação de H; ligações rotacionáveis.
  6. SMARTS de ácido carboxílico (`C(=O)[OH]`). A variável `grupo_hidroxila` recebe um padrão de amina e não é usada.
  7. Regra de Lipinski: massa ≤ 500, LogP ≤ 5, doadores ≤ 5, aceitadores ≤ 10.
  8. Centros quirais com `FindMolChiralCenters`, incluindo o L-ácido lático com estereoquímica definida.
- **Feito no notebook, mas ausente do app:** contagem de doadores/aceitadores de H, ligações rotacionáveis e regra de Lipinski.
