# Glossário de nomes

`glossario.toml` liga os nomes que estudantes e professores usam a uma estrutura (SMILES).
Foi copiado do ChemioChat_app (68 entradas conferidas com o PubChem e a IUPAC).

O ChemioKit procura um nome nesta ordem (`chemio_tools/busca_nome.py`):

1. **Glossário** (este arquivo);
2. **PubChem**: primeiro as consultas já guardadas no computador (`dados/cache_nomes.sqlite`),
   depois a consulta pela internet, com tempo limite de 8 segundos;
3. **Sugestões** de nomes parecidos do glossário, para perguntar "você quis dizer...?".

O SMILES vem sempre do glossário ou do PubChem, nunca de um modelo de linguagem.
O PubChem conhece sobretudo nomes em inglês ("aspirin", "lactic acid"); os nomes em
português devem estar no glossário.

## Acrescentar uma substância

```toml
[[substancia]]
id = "acido_piruvico"            # único, sem acento nem espaço
nome = "Ácido pirúvico"          # como aparece para o usuário
smiles = "CC(=O)C(=O)O"
iupac = ["ácido 2-oxopropanoico"]
comuns = ["ácido pirúvico"]
comerciais = []
informais = []
ingles = ["pyruvic acid"]
nota = "Produto final da glicólise."   # opcional
```

Maiúsculas, acentos, hífens e parênteses são ignorados na busca: "Ácido Pirúvico",
"acido piruvico" e "ácido-pirúvico" encontram a mesma entrada.

## Acrescentar uma mistura

```toml
[[mistura]]
id = "soro_caseiro"
nome = "Soro caseiro"
informais = ["soro caseiro"]
componentes = ["cloreto_de_sodio", "agua"]   # ids de substâncias do glossário
principal = "cloreto_de_sodio"               # opcional (aparece primeiro)
nota = "Solução de sal e açúcar em água."
```

Misturas não têm SMILES: o ChemioKit mostra os componentes para o usuário escolher.

## Nomes ambíguos

Se o mesmo nome aparecer em mais de uma entrada (como "ácido tartárico"), o ChemioKit
mostra as opções e pergunta qual é. Use isso de propósito quando um nome tiver mais de um
significado em sala.

## Depois de editar

- Reinicie o app para recarregar o glossário.
- `uv run pytest` confere se o arquivo carrega sem problemas e se todos os SMILES são válidos.
