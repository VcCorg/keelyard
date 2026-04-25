"""LLM-based judges for evaluating agent responses."""

import json
import os
from abc import ABC, abstractmethod
from typing import Optional


class LLMJudge(ABC):
    """Base class for LLM judges."""

    @abstractmethod
    async def evaluate(
        self,
        input_text: str,
        expected_output: str,
        actual_output: str,
        metric: str,
        criteria: str,
    ) -> float:
        """Evaluate and return a score (0-1 for quantitative, 1-5 for qualitative).

        Args:
            input_text: The input/question
            expected_output: Expected output
            actual_output: Agent's actual output
            metric: Metric name (e.g., "helpfulness", "relevance")
            criteria: Evaluation criteria description

        Returns:
            Score: 0-1 for binary, 1-5 for qualitative
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the judge is available (credentials, etc)."""
        pass


class VertexAIJudge(LLMJudge):
    """Vertex AI based judge using PaLM or Claude models."""

    def __init__(self, project_id: Optional[str] = None):
        """Initialize Vertex AI judge.

        Args:
            project_id: GCP project ID (uses GOOGLE_CLOUD_PROJECT if not provided)
        """
        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
        self.judge_model = "gemini-pro"  # Default to Gemini
        self._client = None

    def is_available(self) -> bool:
        """Check if Vertex AI credentials are available."""
        if not self.project_id:
            return False

        try:
            import google.auth
            google.auth.default()
            return True
        except Exception:
            return False

    async def evaluate(
        self,
        input_text: str,
        expected_output: str,
        actual_output: str,
        metric: str,
        criteria: str,
    ) -> float:
        """Evaluate using Vertex AI."""
        try:
            from google.cloud import aiplatform

            # Initialize client
            if not self._client:
                aiplatform.init(project=self.project_id)

            # Prepare evaluation prompt
            prompt = self._prepare_prompt(
                input_text, expected_output, actual_output, metric, criteria
            )

            # Call Vertex AI
            model = aiplatform.TextGenerationModel.from_pretrained(self.judge_model)
            response = model.predict(prompt, temperature=0, max_output_tokens=10)

            # Parse score from response
            return self._parse_score(response.text, metric)

        except ImportError:
            raise ImportError("google-cloud-aiplatform not installed")
        except Exception as e:
            raise RuntimeError(f"Vertex AI evaluation failed: {e}")

    def _prepare_prompt(
        self,
        input_text: str,
        expected_output: str,
        actual_output: str,
        metric: str,
        criteria: str,
    ) -> str:
        """Prepare evaluation prompt."""
        return f"""Evaluate the agent's response using the following metric.

Question: {input_text}

Expected Output: {expected_output}

Actual Output: {actual_output}

Metric: {metric}
Criteria: {criteria}

Provide a score from 1-5 where:
1 = Very Poor
2 = Poor
3 = Fair
4 = Good
5 = Excellent

Respond with only a single number (1-5)."""

    @staticmethod
    def _parse_score(text: str, metric: str) -> float:
        """Parse score from response text."""
        text = text.strip()
        try:
            # Try to extract first number
            for char in text:
                if char.isdigit():
                    score = int(char)
                    if 1 <= score <= 5:
                        return score
            return 3.0  # Default to neutral score
        except Exception:
            return 3.0


class AnthropicJudge(LLMJudge):
    """Claude-based judge using Anthropic API."""

    def __init__(self, model: str = "claude-opus-4-7"):
        """Initialize Anthropic judge.

        Args:
            model: Claude model to use
        """
        self.model = model
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        self._client = None

    def is_available(self) -> bool:
        """Check if Anthropic API key is available."""
        return bool(self.api_key)

    async def evaluate(
        self,
        input_text: str,
        expected_output: str,
        actual_output: str,
        metric: str,
        criteria: str,
    ) -> float:
        """Evaluate using Claude."""
        try:
            from anthropic import Anthropic

            if not self._client:
                self._client = Anthropic(api_key=self.api_key)

            prompt = self._prepare_prompt(
                input_text, expected_output, actual_output, metric, criteria
            )

            response = self._client.messages.create(
                model=self.model,
                max_tokens=10,
                messages=[{"role": "user", "content": prompt}],
            )

            return self._parse_score(response.content[0].text, metric)

        except ImportError:
            raise ImportError("anthropic not installed")
        except Exception as e:
            raise RuntimeError(f"Claude evaluation failed: {e}")

    def _prepare_prompt(
        self,
        input_text: str,
        expected_output: str,
        actual_output: str,
        metric: str,
        criteria: str,
    ) -> str:
        """Prepare evaluation prompt."""
        return f"""Evaluate the agent's response using the following metric.

Question: {input_text}

Expected Output: {expected_output}

Actual Output: {actual_output}

Metric: {metric}
Criteria: {criteria}

Provide a score from 1-5 where:
1 = Very Poor
2 = Poor
3 = Fair
4 = Good
5 = Excellent

Respond with only a single number (1-5)."""

    @staticmethod
    def _parse_score(text: str, metric: str) -> float:
        """Parse score from response text."""
        text = text.strip()
        try:
            for char in text:
                if char.isdigit():
                    score = int(char)
                    if 1 <= score <= 5:
                        return float(score)
            return 3.0
        except Exception:
            return 3.0


class OpenAIJudge(LLMJudge):
    """GPT-4 based judge using OpenAI API."""

    def __init__(self, model: str = "gpt-4"):
        """Initialize OpenAI judge.

        Args:
            model: OpenAI model to use
        """
        self.model = model
        self.api_key = os.getenv("OPENAI_API_KEY")
        self._client = None

    def is_available(self) -> bool:
        """Check if OpenAI API key is available."""
        return bool(self.api_key)

    async def evaluate(
        self,
        input_text: str,
        expected_output: str,
        actual_output: str,
        metric: str,
        criteria: str,
    ) -> float:
        """Evaluate using GPT-4."""
        try:
            from openai import OpenAI

            if not self._client:
                self._client = OpenAI(api_key=self.api_key)

            prompt = self._prepare_prompt(
                input_text, expected_output, actual_output, metric, criteria
            )

            response = self._client.chat.completions.create(
                model=self.model,
                max_tokens=10,
                messages=[{"role": "user", "content": prompt}],
            )

            return self._parse_score(response.choices[0].message.content, metric)

        except ImportError:
            raise ImportError("openai not installed")
        except Exception as e:
            raise RuntimeError(f"GPT-4 evaluation failed: {e}")

    def _prepare_prompt(
        self,
        input_text: str,
        expected_output: str,
        actual_output: str,
        metric: str,
        criteria: str,
    ) -> str:
        """Prepare evaluation prompt."""
        return f"""Evaluate the agent's response using the following metric.

Question: {input_text}

Expected Output: {expected_output}

Actual Output: {actual_output}

Metric: {metric}
Criteria: {criteria}

Provide a score from 1-5 where:
1 = Very Poor
2 = Poor
3 = Fair
4 = Good
5 = Excellent

Respond with only a single number (1-5)."""

    @staticmethod
    def _parse_score(text: str, metric: str) -> float:
        """Parse score from response text."""
        text = text.strip()
        try:
            for char in text:
                if char.isdigit():
                    score = int(char)
                    if 1 <= score <= 5:
                        return float(score)
            return 3.0
        except Exception:
            return 3.0


def get_judge(
    judge_type: str = "vertex-ai",
    **kwargs,
) -> LLMJudge:
    """Get a judge instance by type.

    Args:
        judge_type: Type of judge (vertex-ai, anthropic, openai)
        **kwargs: Additional arguments for judge initialization

    Returns:
        LLMJudge instance

    Raises:
        ValueError: If judge type is unknown
    """
    judges = {
        "vertex-ai": VertexAIJudge,
        "anthropic": AnthropicJudge,
        "claude": AnthropicJudge,
        "openai": OpenAIJudge,
        "gpt-4": OpenAIJudge,
    }

    judge_class = judges.get(judge_type.lower())
    if not judge_class:
        raise ValueError(f"Unknown judge type: {judge_type}")

    return judge_class(**kwargs)


def get_available_judges() -> list[tuple[str, LLMJudge]]:
    """Get list of available judges."""
    judges = []
    judge_names = ["vertex-ai", "anthropic", "openai"]

    for name in judge_names:
        try:
            judge = get_judge(name)
            if judge.is_available():
                judges.append((name, judge))
        except Exception:
            pass

    return judges
