from longeval_sci.config import load_config
from longeval_sci.io.dataset import load_dataset_bundle


def test_local_fixture_dataset_loading():
    config = load_config("configs/local_fixture_dense_rerank.yaml")
    bundle = load_dataset_bundle(config.dataset)

    assert bundle.metadata.backend == "local_files"
    assert bundle.metadata.snapshot_id == "snapshot-1"
    assert len(bundle.documents) == 5
    assert len(bundle.queries) == 2
    assert bundle.qrels is not None
