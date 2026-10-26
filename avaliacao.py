"""Avaliacao de solucoes do MKP, independente do algoritmo que as gerou."""
import numpy as np


def calcularLucro(solucao, instancia):
    """Lucro total dos itens selecionados: soma de p_j * x_j."""
    return int(instancia.lucros @ solucao)


def calcularConsumo(solucao, instancia):
    """Consumo de cada recurso: R[i] = soma de r_ij * x_j."""
    return instancia.consumos @ solucao


def ehViavel(solucao, instancia):
    """Uma solucao e viavel se nenhum recurso ultrapassa sua capacidade."""
    solucao = np.asarray(solucao)
    if solucao.shape != (instancia.n,) or not np.isin(solucao, (0, 1)).all():
        return False
    return bool((calcularConsumo(solucao, instancia) <= instancia.capacidades).all())


def calcularGap(valor, limite):
    """Gap percentual de um problema de maximizacao: 100 * (limite - valor) / limite."""
    if limite is None or limite == 0:
        return None
    return 100.0 * (limite - valor) / limite
