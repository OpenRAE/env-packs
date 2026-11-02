"""Inject a private failure at a Python command's service boundary.

Only the conformance runner calls this driver. Production commands have no
fault flag or environment hook. The txtar cases own the expected contract.
"""

import importlib
import sys
from unittest.mock import patch


CASES = {
    "raes-pack-check": ("check", "validate_pack", [".", "--json"]),
    "raes-pack-catalog": ("catalog", "build_catalog", ["."]),
    "raes-pack-kit": ("kit_cli", "_discovery",
                      ["list", ".", "--source-id", "fixture", "--source-revision", "test"]),
    "raes-pack-verify": ("verify", "load_release_evidence",
                         ["--pack", ".", "--release", ".", "--json"]),
    "raes-pack-dist": ("distribution", "_dispatch",
                       ["verify", "--pack", ".", "--release", ".", "--json"]),
}


if __name__ == "__main__":
    module_name, operation, args = CASES[sys.argv[1]]
    module = importlib.import_module("raes_env_packs." + module_name)
    with patch.object(module, operation, side_effect=RuntimeError("PRIVATE-FAULT-VALUE")):
        sys.exit(module.main(args))
