import importlib.util
import unittest

from longeval_sci.config import DatasetConfig
from longeval_sci.io.dataset import load_dataset_bundle


@unittest.skipUnless(importlib.util.find_spec("ir_datasets_longeval") is not None, "ir-datasets-longeval not installed")
class OfficialDatasetSmokeTest(unittest.TestCase):
    def test_official_loader_metadata(self):
        bundle = load_dataset_bundle(
            DatasetConfig(
                backend="ir_datasets_longeval",
                dataset_name="longeval-sci-2026/snapshot-1",
                snapshot_id="snapshot-1",
                qrels_variant="dctr",
            )
        )
        self.assertEqual(bundle.metadata.snapshot_id, "snapshot-1")
        self.assertGreater(len(bundle.documents), 0)


if __name__ == "__main__":
    unittest.main()
