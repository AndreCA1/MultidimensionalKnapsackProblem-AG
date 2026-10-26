# Problema da Mochila Multidimensional (MKP 0-1)

Implementação do algoritmo genético de Chu e Beasley (1998) para o problema da mochila multidimensional 0-1, avaliado com as instâncias da OR-Library.

> Chu, P. C. & Beasley, J. E. (1998). A Genetic Algorithm for the Multidimensional Knapsack Problem. *Journal of Heuristics*, 4(1), 63-86.

## O problema

Dados `n` itens com lucro `p_j` e `m` recursos com capacidade `b_i`, em que o item `j` consome `r_ij` do recurso `i`, escolher `x_j ∈ {0, 1}` para

```
maximizar   Σ_j p_j x_j
sujeito a   Σ_j r_ij x_j ≤ b_i   para todo i = 1..m
```

## Algoritmo

- **Representação:** vetor binário de tamanho `n`.
- **População:** 100 indivíduos, substituição estacionária (cada filho substitui o pior, desde que não seja duplicado).
- **Seleção:** torneio binário. **Cruzamento:** uniforme. **Mutação:** inversão de 2 bits.
- **Operador de reparo:** remove itens de menor pseudo-utilidade até a solução ficar viável e depois adiciona os de maior pseudo-utilidade enquanto couberem. A pseudo-utilidade é `p_j / Σ_i u_i r_ij`, em que `u_i` são as variáveis duais da relaxação linear (calculadas com `scipy`). Sem o `scipy`, o algoritmo usa `u_i = 1 / b_i`.
- **Parada:** número de filhos não duplicados (padrão do artigo: 1.000.000), tempo limite ou 100.000 filhos duplicados seguidos (população estagnada).

## Estrutura

| Arquivo | Conteúdo |
|---|---|
| `instancia.py` | Leitura das instâncias no formato da OR-Library |
| `avaliacao.py` | Lucro, consumo, viabilidade e gap |
| `algoritmoGenetico.py` | Relaxação linear e AG de Chu e Beasley |
| `teste.py` | Executa o AG em uma instância e mostra o resumo |
| `rodarTudo.sh` | Roda todos os experimentos em paralelo |
| `All-MKP-Instances/` | Instâncias (`chubeas`, `gk`, `sac94`) |
| `resultados/` | Saídas dos experimentos |

## Como executar

Requer Python 3 (testado com 3.13).

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Uma instância (aceita o nome ou o caminho do `.dat`):

```bash
python teste.py weing1
python teste.py gk01 --execucoes 10 --filhos 200000 --semente 1
python teste.py OR5x100-0.25_1 --itens          # lista os itens da melhor solução
python teste.py gk02 --tempo 60 --csv saida.csv  # tempo limite e saída em CSV
```

Opções: `--filhos`, `--populacao`, `--mutacao`, `--execucoes`, `--semente`, `--tempo`, `--itens`, `--csv` (veja `python teste.py --help`).

Todos os experimentos (instâncias `sac94` e `gk01`–`gk03`, 10 execuções cada):

```bash
./rodarTudo.sh
FILHOS=1000000 PARALELO=8 ./rodarTudo.sh   # parâmetros por variáveis de ambiente
```

Cada rodada cria uma pasta `resultados/<data>_filhos<N>/` com um `.txt` e um `.csv` por instância e o arquivo `resultados.csv` com todas as execuções juntas. A execução `k` usa a semente `semente + k`, então os resultados são reproduzíveis.

## Resultados

Rodada em `resultados/20261023_144226_filhos200000/`: 200.000 filhos, 10 execuções por instância, sementes 1 a 10.

- Nas 54 instâncias da `sac94`, o ótimo foi encontrado em todas. Só em `pet6` uma das 10 execuções não chegou nele.
- `gk01` e `gk02` atingiram o melhor valor conhecido em 7 e 4 das 10 execuções.
- `gk03` não atingiu o melhor valor conhecido; o maior gap foi de 0,21%.
- O gap médio em relação à referência, considerando todas as execuções, foi de 0,004%.

O CSV traz, por execução: lucro, gap em relação à referência e ao limite da relaxação linear, viabilidade, filhos gerados, em que filho e em que tempo o melhor foi encontrado, tempo total e motivo de parada.
