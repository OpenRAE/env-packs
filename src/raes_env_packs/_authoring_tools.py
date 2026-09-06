"""Closed request shapes for the authoring adapter and MCP discovery."""

def text(maximum: int = 256) -> dict[str, object]:
    """Describe a bounded string parameter."""
    return {"type": "string", "maxLength": maximum}


def fields(properties: dict[str, object], required: tuple[str, ...] = ()) -> dict[str, object]:
    """Describe a closed object with explicitly required fields."""
    return {"type": "object", "properties": properties, "required": list(required),
            "additionalProperties": False}


_SOURCE = {"source": text()}
_CARD = {**_SOURCE, "as_of": text(32)}
_PROPOSAL = fields({"proposal": text(64)}, ("proposal",))
TOOLS = {
    "pack_search": ("Search admitted packs using the shared catalog projection.",
                    fields({"query": text(256), "as_of": text(32)}, ("as_of",))),
    "pack_inspect": ("Inspect one admitted pack as the canonical catalog card.",
                     fields(_CARD, ("source", "as_of"))),
    "pack_compatibility_card": ("Project declared compatibility; does not probe a backend.",
                                fields(_CARD, ("source", "as_of"))),
    "pack_validate": ("Run the shared static, import-denying consumer check.",
                      fields(_SOURCE, ("source",))),
    "pack_explain": ("Explain a stable diagnostic using the shared check presentation.",
                     fields({"code": text(128)}, ("code",))),
    "pack_examples": ("Return a packaged starter example and its optional pack layers.",
                      fields({"route": text(64)})),
    "pack_scaffold": ("Preview the complete create-only wizard proposal without writing.",
                      fields({"inputs": {"type": "object"}}, ("inputs",))),
    "pack_kits": ("List/search admitted local kit releases, without acquisition.",
                  fields({"source": text(), "query": text()}, ("source",))),
    "pack_kit_inspect": ("Inspect an admitted import-free kit using public RAES models.",
                         fields({"source": text(), "kit": text(), "version": text()},
                                ("source", "kit", "version"))),
    "pack_compose": ("Plan local preparation for kit add/update/replace/remove; writes nothing.",
                     fields({"source": text(), "operation": {"enum": ["add", "update", "replace", "remove"]},
                             "kit_source": text(), "kit": text(), "version": text(),
                             "namespace": text(), "target_sdl": text(), "materialization": text(),
                             "parameters": {"type": "object"}}, ("source", "operation"))),
    "pack_prepare": ("Execute the stored preparation in its disclosed private scratch target; "
                     "requires host permission.",
                     _PROPOSAL),
    "pack_apply": ("Apply the exact previously returned proposal; requires host write permission.", _PROPOSAL),
    "pack_sdl": ("Delegate in-memory SDL services to RAES; plan uses the reference manifest and never executes.",
                 fields({"operation": {"enum": ["parse", "diagnostics", "completion", "format", "compile", "plan"]},
                         "content": text(65536), "cursor_path": text(), "prefix": text(),
                         "parameters": {"type": "object"}}, ("operation", "content"))),
    "pack_publication_plan": ("Plan signing/registry effects for admitted release evidence; "
                              "does not publish or establish readiness.",
                              fields({"source": text(), "repository": text(), "reference": text()},
                                     ("source", "repository", "reference"))),
}
