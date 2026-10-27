"""Consumer compatibility with the released RAES descriptive runtime contracts."""

from __future__ import annotations

import unittest


class RuntimeContractCompatibilityTests(unittest.TestCase):
    def test_inventory_round_trips_through_the_materialization_archive(self):
        from raes_contracts.contracts.materialization_attestation import (
            MaterializationArchiveRecord,
        )
        from raes_contracts.materialization_inventory import RuntimeInventoryReport

        digest = "sha256:" + "a" * 64
        inventory = RuntimeInventoryReport.model_validate({
            "attempt_id": "attempt-1",
            "sequence": 1,
            "complete": True,
            "source_digest": digest,
            "run_id": "run-1",
            "target_scope": "target:example",
            "descendants": [{
                "address": "provision.worker",
                "parent_address": "provision.parent",
                "source_address": "provision.parent",
                "native_identity_digest": digest,
                "creation": {
                    "run_id": "run-1",
                    "operation_id": "operation-1",
                    "attempt_id": "attempt-1",
                    "evidence_digest": digest,
                },
            }],
        })
        archive = MaterializationArchiveRecord.model_validate({
            "reference": {
                "ref_id": "materialization-1",
                "ref_digest": digest,
                "ref_path": "runs/run-1/materialization.sdl.yaml",
            },
            "artifact": {
                "artifact_id": "materialization-1",
                "role": "materialization-attestation",
                "media_type": "application/vnd.raes.sdl+yaml",
                "uri": "urn:sha256:" + "b" * 64,
                "checksum": {"algorithm": "sha256", "value": "b" * 64},
                "size_bytes": 100,
                "created_at": "2026-10-27T12:00:00+00:00",
                "source": "synthetic-backend",
                "sensitivity": "restricted",
            },
            "run_id": "run-1",
            "operation_id": "operation-1",
            "inventory": inventory.model_dump(mode="json"),
        })

        restored = MaterializationArchiveRecord.model_validate_json(archive.model_dump_json())
        self.assertEqual(restored.inventory, inventory)
        self.assertEqual(restored.inventory.descendants[0].address, "provision.worker")
        self.assertEqual(restored.reference.ref_kind, "materialization-attestation")
        self.assertEqual(restored.inventory.contract_id, "backend-runtime-descendants-v1")


if __name__ == "__main__":
    unittest.main()
