"""
Configuração comum dos testes (pytest).

- Nenhum teste acessa a internet: a conexão do PubChemPy (urlopen, usada por todas as
  consultas: nome, fórmula, propriedades) é trocada por uma função que simula "sem
  conexão". Testes que precisam de respostas do PubChem trocam as funções de consulta
  por respostas simuladas (monkeypatch).
- O cache de nomes é gravado numa pasta temporária, nunca em dados/.
"""

import urllib.error

import pytest

from chemio_tools import cache_nomes, pubchem


def _sem_rede(*args, **kwargs):
    raise urllib.error.URLError("rede desativada nos testes")


@pytest.fixture(autouse=True)
def isolar(tmp_path, monkeypatch):
    monkeypatch.setattr(cache_nomes, "caminho_cache", tmp_path / "cache_nomes.sqlite")
    monkeypatch.setattr(pubchem.pcp, "urlopen", _sem_rede)
