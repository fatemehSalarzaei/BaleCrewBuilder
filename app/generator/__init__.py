from dataclasses import dataclass
from pathlib import Path

from app.generator.context_builder import build_context
from app.generator.file_manifest import GenerationManifest, build_manifest
from app.generator.modules.backend import BackendModule
from app.generator.modules.core import CoreModule
from app.generator.renderer import Renderer
from app.generator.template_registry import TemplateRegistry
from app.generator.validators import assert_generator_preconditions, assert_no_duplicate_paths
from app.schemas.blueprint import BotBlueprint


@dataclass
class GeneratorResult:
    manifest: GenerationManifest
    output_dir: Path
    generated_files: list[str]


class GeneratorCore:
    def __init__(self) -> None:
        self._registry = TemplateRegistry()

    def run(self, blueprint: BotBlueprint, output_dir: Path) -> GeneratorResult:
        assert_generator_preconditions(blueprint, self._registry)

        context = build_context(blueprint)
        renderer = Renderer(output_dir)
        core_module = CoreModule()
        backend_module = BackendModule()

        pre_manifest_files = (
            core_module.generate_pre_manifest(renderer, context)
            + backend_module.generate_pre_manifest(renderer, context)
        )

        manifest_rel = "docs/generation_manifest.json"
        all_files = sorted(pre_manifest_files + [manifest_rel])
        assert_no_duplicate_paths(all_files)

        manifest = build_manifest(blueprint, all_files)
        renderer.write_file(manifest_rel, manifest.model_dump_json(indent=2))

        return GeneratorResult(
            manifest=manifest,
            output_dir=output_dir,
            generated_files=all_files,
        )
