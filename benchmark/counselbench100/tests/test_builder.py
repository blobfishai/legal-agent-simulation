"""Regression tests for generated Harbor packaging."""

from __future__ import annotations

import unittest

from benchmark.counselbench100.builder import compose_yaml, world_dockerfile


class BuilderPackagingTests(unittest.TestCase):
    def test_world_image_copies_every_runtime_module(self) -> None:
        dockerfile = world_dockerfile()

        self.assertIn(
            "COPY world/contracts.py world/scoring.py world/world.py world/server.py world/spec.json ./",
            dockerfile,
        )
        self.assertIn("COPY documents /workspace/documents", dockerfile)

    def test_provider_evidence_is_baked_into_world_not_host_bound(self) -> None:
        compose = compose_yaml()

        self.assertIn("context: .", compose)
        self.assertIn("dockerfile: world/Dockerfile", compose)
        self.assertNotIn("source: ./documents", compose)


if __name__ == "__main__":
    unittest.main()
