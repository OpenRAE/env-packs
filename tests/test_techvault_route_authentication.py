"""The portal declaration agrees with the exact bundled route handlers."""

import ast
import tarfile
import unittest
from pathlib import Path

from raes import parse_sdl_file
from raes_processor.compiler import compile_scenario_runtime_model
from raes_processor.semantics.realization import project_realization_concern
from raes_contracts.realization_structure import (
    RealizationRelationStatus,
    evaluate_realization_constraint,
)

ROOT = Path(__file__).resolve().parents[1]
ROUTES = {"/logout": "logout", "/api/v1/users/<int:user_id>": "api_get_user"}


class PortalAuthenticationTests(unittest.TestCase):
    def test_declarations_match_the_unguarded_exact_handlers(self):
        for name in ("techvault", "techvault-participant-study"):
            with self.subTest(pack=name):
                pack = ROOT / "packs" / name
                with tarfile.open(pack / "assets/content/webapp-app.tar") as archive:
                    source = archive.extractfile("app.py").read().decode()
                functions = {node.name: node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef)}
                scenario = parse_sdl_file(pack / "sdl" / f"{name}.sdl.yaml")
                application = scenario.nodes["webapp"].runtime.applications[0]
                routes = {route.path: route for route in application.routes}
                for path, function in ROUTES.items():
                    handler = functions[function]
                    self.assertFalse(routes[path].auth_required)
                    # Neither handler reads a credential or checks an authenticated session.
                    if function == "api_get_user":
                        names = {node.id for node in ast.walk(handler) if isinstance(node, ast.Name)}
                        self.assertTrue({"request", "session", "current_user"}.isdisjoint(names))
                    else:
                        self.assertFalse(any(isinstance(node, ast.If) for node in ast.walk(handler)))
                self.assertTrue(routes["/dashboard"].auth_required)
                self.assertTrue(routes["/api/v1/customers"].auth_required)
                parameters = {key: "test-only-flag" for key in scenario.variables}
                model = compile_scenario_runtime_model(scenario, parameters=parameters)
                requirement = next(item for item in model.realization_requirements if item.address == "provision.node.webapp" and item.requirement_kind == "runtime-applications")
                observed = project_realization_concern("runtime-applications", [application], observed=False, recursive=True)
                self.assertIs(evaluate_realization_constraint(requirement.constraint_document, observed).status, RealizationRelationStatus.CONFORMANT)
