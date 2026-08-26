"""Regression tests for generated Harbor packaging."""

from __future__ import annotations

import unittest

from benchmark.counselbench100.builder import world_dockerfile


class BuilderPackagingTests(unittest.TestCase):
    def test_world_image_copies_every_runtime_module(self) -> None:
        dockerfile = world_dockerfile()

        self.assertIn("COPY contracts.py scoring.py world.py server.py spec.json ./", dockerfile)


if __name__ == "__main__":
    unittest.main()
