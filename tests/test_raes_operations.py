"""Keep the Go operation map complete for its Python consumer contracts."""

import ast
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
RETAINED_TESTS = (
    "test_techvault_pack",
    "test_techvault_study_pack",
    "test_ai_escape_lab_pack",
    "test_owlbear_kit",
    "test_smtp_imap_mailbox_domain",
    "test_kit_compute_substrate",
    "test_published_kits",
    "test_hosted_pack_content_binding",
    "test_hosted_pack_byte_binding",
    "test_raes_reference_eligibility",
    "test_bundled_kits",
    "test_techvault_route_authentication",
    "test_raes_runtime_contracts",
)
RAES_PACKAGES = {
    "raes", "raes_contracts", "raes_processor", "raes_backend_stubs",
    "raes_backend_protocols",
}


class RAESOperationInventoryTests(unittest.TestCase):
    def test_each_scoped_raes_import_has_a_go_replacement(self):
        paths = sorted((ROOT / "src").rglob("*.py"))
        paths.extend(sorted((ROOT / "tools").rglob("*.py")))
        paths.extend(ROOT / "tests" / f"{name}.py" for name in RETAINED_TESTS)
        imports = {}
        for path in paths:
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                symbols = []
                if isinstance(node, ast.ImportFrom) and node.module:
                    if node.module.split(".")[0] in RAES_PACKAGES:
                        symbols = [f"{node.module}.{alias.name}" for alias in node.names]
                elif isinstance(node, ast.Import):
                    symbols = [alias.name for alias in node.names
                               if alias.name.split(".")[0] in RAES_PACKAGES]
                for symbol in symbols:
                    imports.setdefault(symbol, set()).add(str(path.relative_to(ROOT)))

        inventory = (ROOT / "docs/development/raes-operations.md").read_text(encoding="utf-8")
        mapped = set(re.findall(r"^\| `(raes[^`]+)` \| [^|]+ \|", inventory, re.MULTILINE))
        missing = {symbol: sorted(imports[symbol]) for symbol in sorted(imports.keys() - mapped)}
        self.assertFalse(missing, f"RAES imports without Go replacements: {missing}")
