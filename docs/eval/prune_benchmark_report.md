# Merge Upper-Bound Prune Benchmark

- fragment_count: 100
- similarity_threshold: 2.0
- merge_threshold: 0.95

## Baseline (prune off)
- avg_ms: 256.231
- p95_ms: 279.819
- merge_attempts: 4950

## Optimized (prune on)
- avg_ms: 241.559
- p95_ms: 274.15
- merge_attempts: 4950
- merge_pairs_pruned_by_bound: 2519

## Summary
- avg_ms_delta: -14.672
- avg_speedup_ratio: 0.057261
- cluster_count_equal: True
