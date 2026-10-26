"""Leitura das instancias do MKP no formato da OR-Library."""
from pathlib import Path

import numpy as np

PASTA_INSTANCIAS = Path(__file__).resolve().parent / "All-MKP-Instances"


class Instancia:
    """Guarda os dados de uma instancia do MKP 0-1.

    lucros:      vetor p de tamanho n
    consumos:    matriz r de dimensao m x n (linha i = consumo de cada item no recurso i)
    capacidades: vetor b de tamanho m
    referencia:  valor otimo ou melhor conhecido (None quando o arquivo traz 0)
    """

    def __init__(self, nome, lucros, consumos, capacidades, referencia):
        self.nome = nome
        self.lucros = lucros
        self.consumos = consumos
        self.capacidades = capacidades
        self.referencia = referencia
        self.m, self.n = consumos.shape


def lerInstancia(caminho_arquivo):
    """Le um arquivo .dat: n m otimo, depois n lucros, m*n consumos e m capacidades."""
    caminho_arquivo = Path(caminho_arquivo)
    with open(caminho_arquivo, "r") as arquivo:
        valores = [int(float(v)) for v in arquivo.read().split()]

    n, m, otimo = valores[0], valores[1], valores[2]
    esperado = 3 + n + m * n + m
    if len(valores) < esperado:
        raise ValueError(f"{caminho_arquivo.name}: esperados {esperado} valores, encontrados {len(valores)}")

    inicio = 3
    lucros = np.array(valores[inicio:inicio + n], dtype=np.int64)
    inicio += n
    consumos = np.array(valores[inicio:inicio + m * n], dtype=np.int64).reshape(m, n)
    inicio += m * n
    capacidades = np.array(valores[inicio:inicio + m], dtype=np.int64)

    referencia = otimo if otimo > 0 else None
    return Instancia(caminho_arquivo.stem, lucros, consumos, capacidades, referencia)


def localizarInstancia(nome, pasta_base=PASTA_INSTANCIAS):
    """Aceita um caminho para o arquivo ou apenas o nome (com ou sem .dat) e procura em All-MKP-Instances."""
    caminho = Path(nome)
    if caminho.is_file():
        return caminho

    alvo = caminho.name if caminho.suffix == ".dat" else caminho.name + ".dat"
    encontrados = [c for c in Path(pasta_base).rglob("*.dat") if c.name.lower() == alvo.lower()]

    if not encontrados:
        raise FileNotFoundError(f"Instancia '{nome}' nao encontrada em {pasta_base}")
    if len(encontrados) > 1:
        opcoes = "\n  ".join(str(c) for c in encontrados)
        raise FileNotFoundError(f"Mais de uma instancia com o nome '{nome}':\n  {opcoes}")
    return encontrados[0]
