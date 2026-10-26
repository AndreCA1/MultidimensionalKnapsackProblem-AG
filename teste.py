"""Executa o AG de Chu e Beasley em uma instancia e lista os resultados no terminal.

Exemplos:
    python teste.py OR5x100-0.25_1
    python teste.py gk01 --execucoes 10 --filhos 200000
    python teste.py All-MKP-Instances/sac94/weing/weing1.dat --itens
"""
import argparse
import csv
import secrets
import statistics
import sys
import time
from pathlib import Path

from algoritmoGenetico import algoritmoGeneticoChuBeasley
from avaliacao import calcularConsumo, calcularGap, calcularLucro, ehViavel
from instancia import lerInstancia, localizarInstancia


def lerArgumentos():
    parser = argparse.ArgumentParser(description="AG de Chu e Beasley (1998) para o MKP 0-1.")
    parser.add_argument("instancia", help="nome da instancia (ex.: OR5x100-0.25_1, gk01, weing1) ou caminho do .dat")
    parser.add_argument("--filhos", type=int, default=1_000_000, help="filhos nao duplicados por execucao (padrao do artigo: 1000000)")
    parser.add_argument("--populacao", type=int, default=100, help="tamanho da populacao (padrao: 100)")
    parser.add_argument("--mutacao", type=int, default=2, help="bits invertidos na mutacao (padrao: 2)")
    parser.add_argument("--execucoes", type=int, default=1, help="numero de execucoes independentes (padrao: 1)")
    parser.add_argument("--semente", type=int, default=None, help="semente da 1a execucao; a execucao k usa semente + k")
    parser.add_argument("--tempo", type=float, default=None, help="tempo limite por execucao, em segundos")
    parser.add_argument("--itens", action="store_true", help="lista os itens da melhor solucao")
    parser.add_argument("--csv", default=None, help="acrescenta uma linha por execucao neste arquivo CSV")
    return parser.parse_args()


def formatar(valor, casas=4):
    if valor is None:
        return "-"
    return f"{valor:.{casas}f}"


def imprimirCabecalho(instancia, caminho, argumentos, semente_base):
    print("=" * 78)
    print(f"Instancia: {instancia.nome}")
    print(f"Arquivo:   {caminho}")
    print(f"Itens (n): {instancia.n}   Recursos (m): {instancia.m}")
    referencia = instancia.referencia if instancia.referencia is not None else "desconhecida (0 no arquivo)"
    print(f"Otimo / melhor conhecido: {referencia}")
    print(f"Parametros: populacao={argumentos.populacao}  filhos={argumentos.filhos}  "
          f"mutacao={argumentos.mutacao} bits  execucoes={argumentos.execucoes}  "
          f"semente={semente_base}  tempo limite={argumentos.tempo or '-'}")
    print("=" * 78)


class IndicadorProgresso:
    """Mostra um simbolo que alterna na mesma linha do terminal enquanto o AG roda."""

    SIMBOLOS = "/\\"

    def __init__(self, execucao, total_execucoes, total_filhos):
        self.execucao = execucao
        self.total_execucoes = total_execucoes
        self.total_filhos = total_filhos
        self.passo = 0
        self.ultimo = 0.0
        self.ativo = sys.stdout.isatty()  # nao polui a saida quando redirecionada para arquivo

    def __call__(self, filhos_gerados, melhor_lucro):
        agora = time.perf_counter()
        if not self.ativo or agora - self.ultimo < 0.1:
            return
        self.ultimo = agora
        simbolo = self.SIMBOLOS[self.passo % len(self.SIMBOLOS)]
        self.passo += 1
        # \r volta ao inicio da linha, entao o texto e reescrito no mesmo lugar
        print(f"\r{simbolo} execucao {self.execucao}/{self.total_execucoes}  "
              f"filhos {filhos_gerados}/{self.total_filhos}  melhor lucro {melhor_lucro}",
              end="", flush=True)

    def limpar(self):
        if self.ativo:
            print("\r" + " " * 78 + "\r", end="", flush=True)


def imprimirLinhaTabela(colunas):
    larguras = [4, 11, 10, 10, 9, 7, 9, 9, 10, 10]
    print("  ".join(str(c).rjust(w) for c, w in zip(colunas, larguras)))


def main():
    argumentos = lerArgumentos()

    try:
        caminho = localizarInstancia(argumentos.instancia)
    except FileNotFoundError as erro:
        print(erro, file=sys.stderr)
        sys.exit(1)

    instancia = lerInstancia(caminho)
    semente_base = argumentos.semente if argumentos.semente is not None else secrets.randbelow(2**31)
    imprimirCabecalho(instancia, caminho, argumentos, semente_base)

    imprimirLinhaTabela(["Exec", "Semente", "Lucro", "Gap ref%", "Gap LP%", "Viavel",
                         "Filhos", "F.melhor", "T.melhor", "T.total"])

    resultados = []
    for k in range(argumentos.execucoes):
        semente = semente_base + k
        indicador = IndicadorProgresso(k + 1, argumentos.execucoes, argumentos.filhos)
        resultado = algoritmoGeneticoChuBeasley(
            instancia,
            num_filhos=argumentos.filhos,
            tamanho_populacao=argumentos.populacao,
            bits_mutacao=argumentos.mutacao,
            semente=semente,
            tempo_limite=argumentos.tempo,
            aoProgresso=indicador,
        )
        indicador.limpar()

        # Verificacao independente: o lucro e a viabilidade sao recalculados a partir da instancia
        solucao = resultado["melhor_solucao"]
        resultado["semente"] = semente
        resultado["viavel"] = ehViavel(solucao, instancia)
        resultado["lucro_confere"] = calcularLucro(solucao, instancia) == resultado["melhor_lucro"]
        resultado["gap_ref"] = calcularGap(resultado["melhor_lucro"], instancia.referencia)
        resultado["gap_lp"] = calcularGap(resultado["melhor_lucro"], resultado["valor_lp"])
        resultados.append(resultado)

        viavel = "sim" if resultado["viavel"] and resultado["lucro_confere"] else "NAO"
        imprimirLinhaTabela([k + 1, semente, resultado["melhor_lucro"], formatar(resultado["gap_ref"]),
                             formatar(resultado["gap_lp"]), viavel, resultado["filhos_gerados"],
                             resultado["filho_do_melhor"], formatar(resultado["tempo_do_melhor"], 2),
                             formatar(resultado["tempo_total"], 2)])
        sys.stdout.flush()

    imprimirResumo(instancia, resultados, argumentos.itens)

    if argumentos.csv:
        salvarCsv(argumentos, instancia, resultados)
        print(f"\nResultados acrescentados em {argumentos.csv}")


def imprimirResumo(instancia, resultados, listar_itens):
    lucros = [r["melhor_lucro"] for r in resultados]
    melhor = max(resultados, key=lambda r: r["melhor_lucro"])
    valor_lp = melhor["valor_lp"]

    print("-" * 78)
    print("Resumo")
    print(f"  Limite da relaxacao linear (LP): {formatar(valor_lp, 2)}")
    if not melhor["duais_lp"]:
        print("  Aviso: scipy indisponivel; pseudo-utilidade calculada com pesos 1/b_i em vez das duais.")
    print(f"  Melhor lucro:   {max(lucros)}")
    print(f"  Pior lucro:     {min(lucros)}")
    print(f"  Lucro medio:    {statistics.mean(lucros):.2f}")
    if len(lucros) > 1:
        print(f"  Desvio padrao:  {statistics.stdev(lucros):.2f}")
    if instancia.referencia is not None:
        acertos = sum(1 for v in lucros if v >= instancia.referencia)
        gaps = [r["gap_ref"] for r in resultados]
        print(f"  Gap medio em relacao a referencia: {statistics.mean(gaps):.4f}%")
        print(f"  Execucoes que atingiram a referencia: {acertos}/{len(lucros)}")
    if valor_lp is not None:
        gaps_lp = [r["gap_lp"] for r in resultados]
        print(f"  Gap medio em relacao ao LP:        {statistics.mean(gaps_lp):.4f}%")
    print(f"  Tempo medio por execucao: {statistics.mean(r['tempo_total'] for r in resultados):.2f} s")
    print(f"  Filhos duplicados descartados (total): {sum(r['duplicados'] for r in resultados)}")
    print(f"  Motivo de parada (melhor execucao): {melhor['motivo_parada']}")

    solucao = melhor["melhor_solucao"]
    consumo = calcularConsumo(solucao, instancia)
    ocupacao = 100.0 * consumo / instancia.capacidades
    print(f"\nMelhor solucao (execucao com semente {melhor['semente']})")
    print(f"  Itens selecionados: {int(solucao.sum())} de {instancia.n}")
    print(f"  Viavel: {'sim' if melhor['viavel'] else 'NAO'}")
    print(f"  Ocupacao dos recursos: minima {ocupacao.min():.2f}%  media {ocupacao.mean():.2f}%  maxima {ocupacao.max():.2f}%")
    if instancia.m <= 10:
        for i in range(instancia.m):
            print(f"    recurso {i + 1:>2}: {consumo[i]:>10} / {instancia.capacidades[i]:<10} ({ocupacao[i]:6.2f}%)")
    if listar_itens:
        itens = [str(j + 1) for j in range(instancia.n) if solucao[j] == 1]
        print("  Itens (indices a partir de 1): " + " ".join(itens))


def salvarCsv(argumentos, instancia, resultados):
    caminho = Path(argumentos.csv)
    novo = not caminho.exists()
    with open(caminho, "a", newline="") as arquivo:
        escritor = csv.writer(arquivo)
        if novo:
            escritor.writerow(["instancia", "n", "m", "referencia", "valor_lp", "semente", "populacao",
                               "filhos", "mutacao", "lucro", "gap_ref", "gap_lp", "viavel",
                               "filhos_gerados", "filho_do_melhor", "tempo_do_melhor", "tempo_total",
                               "motivo_parada"])
        for r in resultados:
            escritor.writerow([instancia.nome, instancia.n, instancia.m, instancia.referencia, r["valor_lp"],
                               r["semente"], argumentos.populacao, argumentos.filhos, argumentos.mutacao,
                               r["melhor_lucro"], r["gap_ref"], r["gap_lp"], r["viavel"],
                               r["filhos_gerados"], r["filho_do_melhor"], f"{r['tempo_do_melhor']:.4f}",
                               f"{r['tempo_total']:.4f}", r["motivo_parada"]])


if __name__ == "__main__":
    main()
