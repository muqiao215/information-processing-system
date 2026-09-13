from __future__ import annotations

from dataclasses import dataclass, field

from .adapters import AcquisitionAdapter, default_adapters
from .models import AcquisitionTask


@dataclass(frozen=True)
class RecipeStep:
    adapter_name: str
    required_env: str | None = None
    stop_on_success: bool = True

    def is_enabled(self, env: dict[str, str] | None = None) -> bool:
        env = env or {}
        if not self.required_env:
            return True
        return bool(env.get(self.required_env))


@dataclass(frozen=True)
class AcquisitionRecipe:
    recipe_id: str
    description: str
    source_types: tuple[str, ...] = ()
    task_kinds: tuple[str, ...] = ()
    steps: tuple[RecipeStep, ...] = ()
    priority: int = 100

    def matches(self, task: AcquisitionTask) -> bool:
        source_type_match = not self.source_types or task.source_type in self.source_types
        task_kind_match = not self.task_kinds or task.task_kind in self.task_kinds
        return source_type_match and task_kind_match

    def step_names_without_disabled(self, env: dict[str, str] | None = None) -> list[str]:
        return [step.adapter_name for step in self.steps if step.is_enabled(env)]


@dataclass(frozen=True)
class Registry:
    adapters: dict[str, AcquisitionAdapter]
    recipes: tuple[AcquisitionRecipe, ...]

    def recipe_for_task(self, task: AcquisitionTask) -> AcquisitionRecipe:
        matches = sorted(
            (recipe for recipe in self.recipes if recipe.matches(task)),
            key=lambda recipe: recipe.priority,
        )
        if not matches:
            raise KeyError(f"No acquisition recipe for source_type={task.source_type} task_kind={task.task_kind}")
        return matches[0]


def default_registry() -> Registry:
    adapters = default_adapters()
    recipes = (
        AcquisitionRecipe(
            recipe_id="public_webpage_default",
            description="Default no-key public webpage fetch cascade before knowledge_pack.",
            source_types=("webpage", "article", "url"),
            task_kinds=("fetch", "scrape"),
            priority=10,
            steps=(
                RecipeStep("jina_reader"),
                RecipeStep("defuddle"),
                RecipeStep("direct_browser_ua"),
                RecipeStep("amp"),
                RecipeStep("archive_today"),
                RecipeStep("agent_fetch"),
                RecipeStep("firecrawl_web_agent", required_env="FIRECRAWL_API_KEY"),
            ),
        ),
        AcquisitionRecipe(
            recipe_id="raw_github_default",
            description="Specialized recipe for GitHub README and repository text files.",
            source_types=("raw_github_text", "github", "github_repo"),
            priority=15,
            steps=(
                RecipeStep("direct_raw"),
                RecipeStep("jina_reader"),
                RecipeStep("defuddle"),
                RecipeStep("agent_fetch"),
            ),
        ),
        AcquisitionRecipe(
            recipe_id="arxiv_paper_default",
            description="Specialized recipe for arXiv papers with abstract and PDF cascade.",
            source_types=("arxiv_paper", "arxiv", "paper"),
            priority=15,
            steps=(
                RecipeStep("arxiv_abstract"),
                RecipeStep("jina_reader"),
                RecipeStep("defuddle"),
                RecipeStep("agent_fetch"),
            ),
        ),
        AcquisitionRecipe(
            recipe_id="generic_default",
            description="Fallback recipe for URL-like tasks that still emits deterministic ledger entries.",
            priority=100,
            steps=(
                RecipeStep("jina_reader"),
                RecipeStep("defuddle"),
                RecipeStep("direct_browser_ua"),
                RecipeStep("agent_fetch"),
            ),
        ),
    )
    return Registry(adapters=adapters, recipes=recipes)


def select_recipe(task: AcquisitionTask, registry: Registry | None = None) -> AcquisitionRecipe:
    registry = registry or default_registry()
    return registry.recipe_for_task(task)
