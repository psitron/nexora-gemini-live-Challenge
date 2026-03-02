from __future__ import annotations

"""
Code Agent - Executes Python or Bash code for complex tasks.

Use cases:
- Spreadsheet calculations (formulas, totals, data filling)
- Bulk operations (process 1000 rows, rename 50 files)
- File manipulation (filter, sort, clean data)
- Data processing (calculate, aggregate, transform)

The code agent iteratively generates and executes code until the task
is complete or the step budget is exhausted.
"""

import subprocess
import sys
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

from config.settings import get_settings


@dataclass
class CodeExecutionStep:
    """A single code execution step."""
    step_number: int
    code_type: str  # "python" or "bash"
    code: str
    output: str
    error: Optional[str]
    success: bool


@dataclass
class CodeAgentResult:
    """Result of code agent execution."""
    success: bool
    steps_executed: int
    max_steps: int
    completion_reason: str  # "DONE", "BUDGET_EXHAUSTED", "ERROR"
    summary: str
    execution_history: List[CodeExecutionStep]


class CodeAgent:
    """
    Executes complex tasks via iterative code generation and execution.

    The agent uses an LLM to generate Python or Bash code, executes it,
    and continues until the task is complete or the budget is exhausted.
    """

    MAX_STEPS = 20
    CODE_TIMEOUT_SECONDS = 30

    def __init__(self):
        self._settings = get_settings()
        self._use_anthropic = bool(self._settings.models.anthropic_api_key)
        self._use_gemini = bool(self._settings.models.gemini_api_key)

        if not (self._use_anthropic or self._use_gemini):
            raise RuntimeError(
                "[CodeAgent] No API keys configured. "
                "Set ANTHROPIC_API_KEY or GEMINI_API_KEY in .env"
            )

    def execute_task(self, task_description: str, context: Optional[Dict[str, Any]] = None) -> CodeAgentResult:
        """
        Execute a task via iterative code generation.

        Args:
            task_description: Natural language description of the task
            context: Optional context (file paths, parameters, etc.)

        Returns:
            CodeAgentResult with execution history and results
        """
        steps_executed = 0
        execution_history: List[CodeExecutionStep] = []
        context_str = self._format_context(context) if context else ""

        print(f"\n[CodeAgent] Starting task: {task_description}")

        while steps_executed < self.MAX_STEPS:
            # Generate code for next step
            code, code_type = self._generate_code(
                task_description,
                context_str,
                execution_history
            )

            if not code:
                # LLM indicated task is complete
                return CodeAgentResult(
                    success=True,
                    steps_executed=steps_executed,
                    max_steps=self.MAX_STEPS,
                    completion_reason="DONE",
                    summary=f"Completed in {steps_executed} steps",
                    execution_history=execution_history
                )

            # Execute the code
            output, error, success = self._execute_code(code, code_type)

            # Record step
            step = CodeExecutionStep(
                step_number=steps_executed + 1,
                code_type=code_type,
                code=code,
                output=output,
                error=error,
                success=success
            )
            execution_history.append(step)
            steps_executed += 1

            print(f"  [Step {steps_executed}] {code_type}: {'✓' if success else '✗'}")

            # Check for fatal errors
            if not success and error:
                if "Permission denied" in error or "Access denied" in error:
                    return CodeAgentResult(
                        success=False,
                        steps_executed=steps_executed,
                        max_steps=self.MAX_STEPS,
                        completion_reason="ERROR",
                        summary=f"Permission error at step {steps_executed}",
                        execution_history=execution_history
                    )

        # Budget exhausted
        return CodeAgentResult(
            success=False,
            steps_executed=steps_executed,
            max_steps=self.MAX_STEPS,
            completion_reason="BUDGET_EXHAUSTED",
            summary=f"Exhausted {self.MAX_STEPS} step budget",
            execution_history=execution_history
        )

    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format context dictionary as readable text."""
        lines = ["Context:"]
        for key, value in context.items():
            lines.append(f"  {key}: {value}")
        return "\n".join(lines)

    def _generate_code(
        self,
        task: str,
        context: str,
        history: List[CodeExecutionStep]
    ) -> tuple[str, str]:
        """
        Generate code for the next step.

        Returns:
            (code, code_type) or ("", "") if task is complete
        """
        # Try Anthropic first (better at code generation), then Gemini
        if self._use_anthropic:
            try:
                return self._generate_with_claude(task, context, history)
            except Exception as e:
                print(f"[CodeAgent] Claude failed: {e}")

        if self._use_gemini:
            try:
                return self._generate_with_gemini(task, context, history)
            except Exception as e:
                print(f"[CodeAgent] Gemini failed: {e}")

        return ("", "")

    def _generate_with_claude(
        self,
        task: str,
        context: str,
        history: List[CodeExecutionStep]
    ) -> tuple[str, str]:
        """Generate code using Claude."""
        import anthropic

        client = anthropic.Anthropic(api_key=self._settings.models.anthropic_api_key)
        model = self._settings.models.anthropic_execution_model

        # Build history summary
        history_text = self._format_history(history)

        prompt = f"""You are a code generation agent. Your task:

{task}

{context}

Previous steps:
{history_text if history_text else "None yet - this is the first step."}

Generate Python or Bash code to make progress on this task.

Rules:
1. If the task is COMPLETE, respond with just: DONE
2. Otherwise, generate code wrapped in ```python or ```bash
3. Keep code simple and focused on one sub-task
4. Add error handling where appropriate
5. Use absolute paths for file operations
6. On Windows, use forward slashes in paths

Generate the next step:"""

        response = client.messages.create(
            model=model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )

        text = "".join(block.text for block in response.content if hasattr(block, "text"))
        return self._parse_code_response(text)

    def _generate_with_gemini(
        self,
        task: str,
        context: str,
        history: List[CodeExecutionStep]
    ) -> tuple[str, str]:
        """Generate code using Gemini."""
        import google.generativeai as genai

        genai.configure(api_key=self._settings.models.gemini_api_key)
        model = genai.GenerativeModel(self._settings.models.gemini_vision_model)

        history_text = self._format_history(history)

        prompt = f"""You are a code generation agent. Your task:

{task}

{context}

Previous steps:
{history_text if history_text else "None yet - this is the first step."}

Generate Python or Bash code to make progress on this task.

Rules:
1. If the task is COMPLETE, respond with just: DONE
2. Otherwise, generate code wrapped in ```python or ```bash
3. Keep code simple and focused on one sub-task
4. Add error handling where appropriate
5. Use absolute paths for file operations
6. On Windows, use forward slashes in paths

Generate the next step:"""

        response = model.generate_content(
            prompt,
            generation_config={"max_output_tokens": 1024, "temperature": 0.1}
        )

        return self._parse_code_response(response.text)

    def _format_history(self, history: List[CodeExecutionStep]) -> str:
        """Format execution history for prompt."""
        if not history:
            return ""

        lines = []
        for step in history[-3:]:  # Only last 3 steps to keep prompt short
            status = "✓" if step.success else "✗"
            lines.append(f"Step {step.step_number} ({step.code_type}) {status}:")
            lines.append(f"  Code: {step.code[:100]}..." if len(step.code) > 100 else f"  Code: {step.code}")
            if step.output:
                lines.append(f"  Output: {step.output[:200]}...")
            if step.error:
                lines.append(f"  Error: {step.error[:200]}...")

        return "\n".join(lines)

    def _parse_code_response(self, text: str) -> tuple[str, str]:
        """
        Parse code from LLM response.

        Returns:
            (code, code_type) or ("", "") if DONE
        """
        text = text.strip()

        # Check for completion
        if text.upper().startswith("DONE"):
            return ("", "")

        # Extract code blocks
        if "```python" in text:
            start = text.find("```python") + 9
            end = text.find("```", start)
            if end > start:
                code = text[start:end].strip()
                return (code, "python")

        if "```bash" in text:
            start = text.find("```bash") + 7
            end = text.find("```", start)
            if end > start:
                code = text[start:end].strip()
                return (code, "bash")

        # No code found
        return ("", "")

    def _execute_code(self, code: str, code_type: str) -> tuple[str, Optional[str], bool]:
        """
        Execute code safely.

        Returns:
            (output, error, success)
        """
        try:
            if code_type == "python":
                return self._execute_python(code)
            elif code_type == "bash":
                return self._execute_bash(code)
            else:
                return ("", f"Unknown code type: {code_type}", False)
        except Exception as e:
            return ("", str(e), False)

    def _execute_python(self, code: str) -> tuple[str, Optional[str], bool]:
        """Execute Python code."""
        try:
            result = subprocess.run(
                [sys.executable, "-c", code],
                capture_output=True,
                text=True,
                timeout=self.CODE_TIMEOUT_SECONDS,
                cwd=self._settings.paths.root_dir
            )

            output = result.stdout.strip()
            error = result.stderr.strip() if result.returncode != 0 else None
            success = result.returncode == 0

            return (output, error, success)

        except subprocess.TimeoutExpired:
            return ("", "Code execution timed out", False)
        except Exception as e:
            return ("", str(e), False)

    def _execute_bash(self, code: str) -> tuple[str, Optional[str], bool]:
        """Execute Bash code."""
        try:
            # On Windows, use Git Bash if available, otherwise cmd
            import platform
            if platform.system() == "Windows":
                shell = ["bash", "-c", code]  # Assumes Git Bash is in PATH
            else:
                shell = ["bash", "-c", code]

            result = subprocess.run(
                shell,
                capture_output=True,
                text=True,
                timeout=self.CODE_TIMEOUT_SECONDS,
                cwd=self._settings.paths.root_dir
            )

            output = result.stdout.strip()
            error = result.stderr.strip() if result.returncode != 0 else None
            success = result.returncode == 0

            return (output, error, success)

        except subprocess.TimeoutExpired:
            return ("", "Code execution timed out", False)
        except FileNotFoundError:
            return ("", "Bash not found. Install Git Bash on Windows.", False)
        except Exception as e:
            return ("", str(e), False)
