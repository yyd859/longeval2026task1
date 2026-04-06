from pathlib import Path

from longeval_sci.config import load_config, metrics_path_for_snapshot, per_query_metrics_path_for_snapshot, run_path_for_snapshot
from longeval_sci.baselines.runner import run_pipeline


def test_full_pipeline_with_local_fixture():
    config = load_config("configs/local_fixture_dense_rerank.yaml")
    artifacts = run_pipeline(config)

    assert Path(artifacts.run_path).exists()
    assert Path(metrics_path_for_snapshot(config)).exists()
    assert Path(per_query_metrics_path_for_snapshot(config)).exists()
