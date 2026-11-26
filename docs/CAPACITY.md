# Capacity plan: MonsoonMind

Full corpus target: All monsoon, cyclone and RMC reports since 2010 (4,000+ pages)

<!-- generated:start -->

## Measured capacity estimate

| Measure | Estimate |
|---|---:|
| Measured average tokens per page | 337 |
| Full corpus target | 4,000 pages |
| Projected full-corpus tokens | 1,347,708 (1.35 M) |
| Chunk size | 500 tokens |
| Projected chunks | 2,696 |
| Embedding dimensions | 1024 |
| Estimated embedding cost | $0.2695 (about Rs 25.61) |
| Estimated vector storage (float32) | 10.53 MB |
| Estimated raw text storage (rough) | 5.14 MB |

*Assumptions: tokens are estimated as extracted characters ÷ 4; embedding price is
the supplied USD per million tokens; vector storage assumes 4 bytes per dimension.
Actual database storage will be higher due to indexes, metadata and row overhead.*

<!-- generated:end -->

## What I conclude

1. Embedding cost is not a major concern at the 4,000-page target: about Rs 25.39, excluding other service costs.
2. Estimated vectors are 10.44 MB and raw text is about 5.10 MB. I still need to compare these estimates with my actual free Postgres storage limit.
3. Tokens per page is the least certain estimate because characters divided by 4 is approximate. I will measure actual tokenizer output on a representative sample.
4. At 10 times the corpus size, estimates become about 13.36 million tokens, 26,730 chunks, Rs 253.90 embedding cost and 104.4 MB of vectors. I will monitor storage and retrieval latency.
