# Capacity plan: MonsoonMind

Full corpus target: All monsoon, cyclone and RMC reports since 2010 (4,000+ pages)

<!-- generated:start -->

## Measured capacity estimate

| Measure | Estimate |
|---|---:|
| Measured average tokens per page | 319 |
| Full corpus target | 4,000 pages |
| Projected full-corpus tokens | 1,274,113 (1.27 M) |
| Chunk size | 500 tokens |
| Projected chunks | 2,549 |
| Embedding dimensions | 1024 |
| Estimated embedding cost | $0.2548 (about Rs 24.21) |
| Estimated vector storage (float32) | 9.96 MB |
| Estimated raw text storage (rough) | 4.86 MB |

*Assumptions: tokens are estimated as extracted characters ÷ 4; embedding price is
the supplied USD per million tokens; vector storage assumes 4 bytes per dimension.
Actual database storage will be higher due to indexes, metadata and row overhead.*

<!-- generated:end -->

## What I conclude

1. Embedding cost is not a major concern at the 4,000-page target: about Rs 24.16, excluding other service costs.
2. Estimated vectors are 9.94 MB and raw text is about 4.85 MB. I still need to compare these estimates with my actual free Postgres storage limit.
3. Tokens per page is the least certain estimate because characters divided by 4 is approximate. I will measure actual tokenizer output on a representative sample.
4. At 10 times the corpus size, estimates become about 12.72 million tokens, 25,440 chunks, Rs 241.60 embedding cost and 99.4 MB of vectors. I will monitor storage and retrieval latency.
