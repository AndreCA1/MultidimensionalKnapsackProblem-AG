"""Algoritmo genetico com operador de reparo para o MKP 0-1.

Baseado em: Chu, P. C. & Beasley, J. E. (1998). A Genetic Algorithm for the
Multidimensional Knapsack Problem. Journal of Heuristics, 4(1), 63-86.
"""
import time

import numpy as np

try:
    from scipy.optimize import linprog
except ImportError:
    linprog = None


def resolverRelaxacaoLinear(instancia):
    """Resolve o MKP com 0 <= x_j <= 1 e devolve (valor_lp, duais).

    As variaveis duais medem a escassez de cada recurso e servem de pesos na
    pseudo-utilidade. Sem o scipy, usa os pesos 1/b_i (consumo relativo a
    capacidade) e devolve valor_lp = None.
    """
    if linprog is None:
        return None, 1.0 / instancia.capacidades

    resultado = linprog(
        c=-instancia.lucros,
        A_ub=instancia.consumos,
        b_ub=instancia.capacidades,
        bounds=(0, 1),
        method="highs",
    )
    if not resultado.success:
        return None, 1.0 / instancia.capacidades

    # O linprog minimiza -p.x, entao as duais de <= vem com sinal negativo
    duais = -resultado.ineqlin.marginals
    return -resultado.fun, duais


def calcularPseudoUtilidade(instancia, pesos):
    """u_j = p_j / soma_i(w_i * r_ij). Itens que nao consomem recursos escassos recebem u_j infinito."""
    denominador = pesos @ instancia.consumos
    utilidade = np.full(instancia.n, np.inf)
    positivos = denominador > 1e-12
    utilidade[positivos] = instancia.lucros[positivos] / denominador[positivos]
    return utilidade


def construirSolucaoAleatoria(instancia, consumos_por_item, gerador):
    """Percorre os itens em ordem aleatoria e adiciona cada um que ainda cabe."""
    solucao = np.zeros(instancia.n, dtype=np.int8)
    folga = instancia.capacidades.copy()
    for j in gerador.permutation(instancia.n):
        if (consumos_por_item[j] <= folga).all():
            solucao[j] = 1
            folga -= consumos_por_item[j]
    return solucao


def repararSolucao(solucao, instancia, consumos_por_item, ordem_crescente, ordem_decrescente):
    """Operador de reparo de Chu e Beasley (altera a solucao no lugar).

    DROP: remove os itens de menor pseudo-utilidade ate a solucao ficar viavel.
    ADD:  adiciona, do maior para o menor u_j, todo item que ainda cabe.
    """
    folga = instancia.capacidades - instancia.consumos @ solucao

    # DROP
    if (folga < 0).any():
        for j in ordem_crescente[solucao[ordem_crescente] == 1]:
            solucao[j] = 0
            folga += consumos_por_item[j]
            if (folga >= 0).all():
                break

    # ADD: a folga so diminui, entao um item que nao cabe agora nao cabera depois
    candidatos = ordem_decrescente[solucao[ordem_decrescente] == 0]
    candidatos = candidatos[(consumos_por_item[candidatos] <= folga).all(axis=1)]
    for j in candidatos:
        if (consumos_por_item[j] <= folga).all():
            solucao[j] = 1
            folga -= consumos_por_item[j]

    return solucao


def torneioBinario(aptidao, gerador):
    """Sorteia dois individuos e devolve o indice do de maior aptidao."""
    a, b = gerador.integers(len(aptidao), size=2)
    return a if aptidao[a] >= aptidao[b] else b


def crossoverUniforme(pai1, pai2, gerador):
    """Cada gene do filho vem de um dos pais com 50% de chance."""
    mascara = gerador.random(len(pai1)) < 0.5
    return np.where(mascara, pai1, pai2).astype(np.int8)


def mutacao(solucao, bits, gerador):
    """Inverte 'bits' posicoes sorteadas da solucao."""
    posicoes = gerador.choice(len(solucao), size=min(bits, len(solucao)), replace=False)
    solucao[posicoes] = 1 - solucao[posicoes]
    return solucao


def algoritmoGeneticoChuBeasley(instancia, num_filhos=1_000_000, tamanho_populacao=100,
                                bits_mutacao=2, semente=None, tempo_limite=None,
                                max_duplicados_seguidos=100_000, aoProgresso=None):
    """Executa o AG steady-state de Chu e Beasley e devolve um dicionario com os resultados.

    Criterio de parada: num_filhos filhos nao duplicados, tempo_limite (segundos)
    ou max_duplicados_seguidos filhos duplicados em sequencia (populacao estagnada).
    aoProgresso(filhos_gerados, melhor_lucro), se informada, e chamada a cada 256 iteracoes.
    """
    inicio = time.perf_counter()
    gerador = np.random.default_rng(semente)

    # Pre-processamento: relaxacao linear, pseudo-utilidade e ordenacao dos itens (feitos uma vez)
    valor_lp, pesos = resolverRelaxacaoLinear(instancia)
    utilidade = calcularPseudoUtilidade(instancia, pesos)
    ordem_crescente = np.argsort(utilidade, kind="stable")
    ordem_decrescente = ordem_crescente[::-1].copy()
    consumos_por_item = np.ascontiguousarray(instancia.consumos.T)  # linha j = consumo do item j

    def reparar(solucao):
        return repararSolucao(solucao, instancia, consumos_por_item, ordem_crescente, ordem_decrescente)

    # Populacao inicial: solucoes aleatorias viaveis, evitando repeticoes quando possivel
    populacao = np.zeros((tamanho_populacao, instancia.n), dtype=np.int8)
    contagem = {}  # chave da solucao -> quantas copias existem na populacao
    tentativas = 0
    k = 0
    while k < tamanho_populacao:
        solucao = construirSolucaoAleatoria(instancia, consumos_por_item, gerador)
        chave = solucao.tobytes()
        tentativas += 1
        if chave in contagem and tentativas < 50 * tamanho_populacao:
            continue
        populacao[k] = solucao
        contagem[chave] = contagem.get(chave, 0) + 1
        k += 1
    aptidao = populacao.astype(np.int64) @ instancia.lucros

    indice_melhor = int(np.argmax(aptidao))
    melhor_solucao = populacao[indice_melhor].copy()
    melhor_lucro = int(aptidao[indice_melhor])
    filho_do_melhor = 0
    tempo_do_melhor = time.perf_counter() - inicio

    filhos_gerados = 0
    duplicados = 0
    duplicados_seguidos = 0
    motivo_parada = "numero de filhos"
    iteracoes = 0

    while filhos_gerados < num_filhos:
        iteracoes += 1
        if aoProgresso is not None and iteracoes % 256 == 0:
            aoProgresso(filhos_gerados, melhor_lucro)
        if tempo_limite is not None and time.perf_counter() - inicio >= tempo_limite:
            motivo_parada = "tempo limite"
            break
        if duplicados_seguidos >= max_duplicados_seguidos:
            motivo_parada = "populacao estagnada (so duplicados)"
            break

        pai1 = populacao[torneioBinario(aptidao, gerador)]
        pai2 = populacao[torneioBinario(aptidao, gerador)]
        filho = crossoverUniforme(pai1, pai2, gerador)
        filho = mutacao(filho, bits_mutacao, gerador)
        filho = reparar(filho)

        chave = filho.tobytes()
        if chave in contagem:
            duplicados += 1
            duplicados_seguidos += 1
            continue
        duplicados_seguidos = 0

        # Substituicao steady-state: o filho entra no lugar do pior individuo
        pior = int(np.argmin(aptidao))
        chave_pior = populacao[pior].tobytes()
        contagem[chave_pior] -= 1
        if contagem[chave_pior] == 0:
            del contagem[chave_pior]

        lucro_filho = int(instancia.lucros @ filho)
        populacao[pior] = filho
        aptidao[pior] = lucro_filho
        contagem[chave] = 1
        filhos_gerados += 1

        if lucro_filho > melhor_lucro:
            melhor_lucro = lucro_filho
            melhor_solucao = filho.copy()
            filho_do_melhor = filhos_gerados
            tempo_do_melhor = time.perf_counter() - inicio

    return {
        "melhor_solucao": melhor_solucao,
        "melhor_lucro": melhor_lucro,
        "valor_lp": valor_lp,
        "duais_lp": linprog is not None and valor_lp is not None,
        "filhos_gerados": filhos_gerados,
        "duplicados": duplicados,
        "filho_do_melhor": filho_do_melhor,
        "tempo_do_melhor": tempo_do_melhor,
        "tempo_total": time.perf_counter() - inicio,
        "motivo_parada": motivo_parada,
        "media_populacao": float(aptidao.mean()),
    }
