# Demo Walkthrough

## 1) Ingest example fragments
```powershell
python -m src.memory_cluster.cli ingest --input data/examples/multi_agent_memory_fragments.jsonl --store outputs/memory_store.jsonl
```

## 2) Build clustered memory state
```powershell
python -m src.memory_cluster.cli build --store outputs/memory_store.jsonl --output outputs/cluster_state.json --preferences data/examples/preference_profile.json --similarity-threshold 0.4 --merge-threshold 0.85
```

## 3) Query compressed memory
```powershell
python -m src.memory_cluster.cli query --state outputs/cluster_state.json --query "alpha 冲突参数" --top-k 3 --expand
```

## 4) Export metrics
```powershell
python -m src.memory_cluster.cli eval --state outputs/cluster_state.json --output outputs/perf_metrics.json
```

## 5) Run benchmark script
```powershell
python scripts/run_benchmark.py --input data/examples/multi_agent_memory_fragments.jsonl --preferences data/examples/preference_profile.json --output outputs/benchmark.json --runs 5 --similarity-threshold 0.4 --merge-threshold 0.85
```

## Expected signals
- 至少出现一个 `alpha` 冲突记录。
- 方法类重复碎片应被合并，压缩比明显小于 1。
- `noise` 分类碎片在摘要中保留粒度更低。
- `backrefs` 可用于展开原始证据碎片。
