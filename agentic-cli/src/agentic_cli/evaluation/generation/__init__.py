"""Evaluation dataset generation (sources, question generation, golden tracking)."""

from agentic_cli.evaluation.generation.sources import (
    DocumentChunk,
    DocumentSource,
    LocalSource,
    get_source,
    parse_source_spec,
)
from agentic_cli.evaluation.generation.question_gen import (
    GenerationConfig,
    QuestionGenerator,
    HeuristicGenerator,
    VertexAIGenerator,
    get_generator,
    DEFAULT_PERSONAS,
)
from agentic_cli.evaluation.generation.golden import GoldenRegistry, GoldenEntry

__all__ = [
    "DocumentChunk",
    "DocumentSource",
    "LocalSource",
    "get_source",
    "parse_source_spec",
    "GenerationConfig",
    "QuestionGenerator",
    "HeuristicGenerator",
    "VertexAIGenerator",
    "get_generator",
    "DEFAULT_PERSONAS",
    "GoldenRegistry",
    "GoldenEntry",
]
