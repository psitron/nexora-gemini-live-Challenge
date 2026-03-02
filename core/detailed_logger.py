"""
Detailed Execution Logger - Logs everything that happens during agent execution

Features:
- Logs every step with timestamps
- Saves screenshots at each step
- Tracks success/failure with reasons
- Creates detailed HTML reports
- Captures LLM interactions
- Records all actions and outcomes
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Any, Dict, List
from dataclasses import dataclass, asdict
import base64
from io import BytesIO

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


@dataclass
class LogEntry:
    """Single log entry with all details"""
    timestamp: str
    step_number: int
    phase: str  # "planning", "execution", "reflection", "verification"
    action: str
    details: Dict[str, Any]
    success: Optional[bool]
    duration_ms: float
    screenshot_path: Optional[str] = None
    error: Optional[str] = None


class DetailedLogger:
    """
    Comprehensive logging system that captures everything.

    Usage:
        logger = DetailedLogger("task_name")
        logger.log_planning(plan)
        logger.log_action(action, details)
        logger.save_screenshot(image)
        logger.generate_report()
    """

    def __init__(self, task_name: str, output_dir: Optional[Path] = None):
        """Initialize logger with task name and output directory."""
        self.task_name = task_name
        self.start_time = time.time()
        self.log_entries: List[LogEntry] = []
        self.step_counter = 0

        # Create output directory
        if output_dir is None:
            output_dir = Path("logs") / datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        self.screenshots_dir = self.output_dir / "screenshots"
        self.screenshots_dir.mkdir(exist_ok=True)

        self.json_log_path = self.output_dir / "execution_log.json"
        self.html_report_path = self.output_dir / "execution_report.html"
        self.text_log_path = self.output_dir / "execution_log.txt"

        # Initialize log file
        self._write_header()

    def _write_header(self):
        """Write initial header to text log"""
        with open(self.text_log_path, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write(f"DETAILED EXECUTION LOG\n")
            f.write(f"Task: {self.task_name}\n")
            f.write(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")

    def log_planning(self, plan: Any, llm_prompt: Optional[str] = None, llm_response: Optional[str] = None):
        """Log the planning phase"""
        self.step_counter += 1
        start = time.time()

        details = {
            "plan": str(plan),
            "llm_prompt": llm_prompt,
            "llm_response": llm_response,
        }

        entry = LogEntry(
            timestamp=datetime.now().isoformat(),
            step_number=self.step_counter,
            phase="planning",
            action="generate_plan",
            details=details,
            success=True,
            duration_ms=(time.time() - start) * 1000
        )

        self.log_entries.append(entry)
        self._write_to_text_log(entry)
        self._save_json_log()

    def log_action(self, action_name: str, parameters: Dict[str, Any],
                   result: Any, screenshot_before: Optional[Image.Image] = None,
                   screenshot_after: Optional[Image.Image] = None):
        """Log an action execution"""
        self.step_counter += 1
        start = time.time()

        # Save screenshots
        screenshot_before_path = None
        screenshot_after_path = None

        if screenshot_before and HAS_PIL:
            screenshot_before_path = self._save_screenshot(screenshot_before, f"step_{self.step_counter}_before")

        if screenshot_after and HAS_PIL:
            screenshot_after_path = self._save_screenshot(screenshot_after, f"step_{self.step_counter}_after")

        details = {
            "action": action_name,
            "parameters": parameters,
            "result": str(result) if result else None,
            "success": getattr(result, 'success', None),
            "message": getattr(result, 'message', None),
            "data": str(getattr(result, 'data', None)),
            "screenshot_before": screenshot_before_path,
            "screenshot_after": screenshot_after_path,
        }

        entry = LogEntry(
            timestamp=datetime.now().isoformat(),
            step_number=self.step_counter,
            phase="execution",
            action=action_name,
            details=details,
            success=getattr(result, 'success', None),
            duration_ms=(time.time() - start) * 1000,
            screenshot_path=screenshot_after_path
        )

        self.log_entries.append(entry)
        self._write_to_text_log(entry)
        self._save_json_log()

    def log_reflection(self, reflection_result: Any, screenshot_before: Optional[Image.Image] = None,
                      screenshot_after: Optional[Image.Image] = None):
        """Log reflection agent analysis"""
        self.step_counter += 1
        start = time.time()

        details = {
            "action_succeeded": getattr(reflection_result, 'action_succeeded', None),
            "state_changed": getattr(reflection_result, 'state_changed', None),
            "progress": getattr(reflection_result, 'progress_assessment', None),
            "observations": getattr(reflection_result, 'observations', None),
            "next_action": getattr(reflection_result, 'next_action_guidance', None),
            "confidence": getattr(reflection_result, 'confidence', None),
        }

        entry = LogEntry(
            timestamp=datetime.now().isoformat(),
            step_number=self.step_counter,
            phase="reflection",
            action="analyze_outcome",
            details=details,
            success=True,
            duration_ms=(time.time() - start) * 1000
        )

        self.log_entries.append(entry)
        self._write_to_text_log(entry)
        self._save_json_log()

    def log_error(self, error_type: str, error_message: str, context: Dict[str, Any]):
        """Log an error"""
        self.step_counter += 1

        entry = LogEntry(
            timestamp=datetime.now().isoformat(),
            step_number=self.step_counter,
            phase="error",
            action=error_type,
            details=context,
            success=False,
            duration_ms=0,
            error=error_message
        )

        self.log_entries.append(entry)
        self._write_to_text_log(entry)
        self._save_json_log()

    def log_custom(self, phase: str, action: str, details: Dict[str, Any],
                   success: Optional[bool] = None, screenshot: Optional[Image.Image] = None):
        """Log a custom event"""
        self.step_counter += 1
        start = time.time()

        screenshot_path = None
        if screenshot and HAS_PIL:
            screenshot_path = self._save_screenshot(screenshot, f"step_{self.step_counter}_custom")

        entry = LogEntry(
            timestamp=datetime.now().isoformat(),
            step_number=self.step_counter,
            phase=phase,
            action=action,
            details=details,
            success=success,
            duration_ms=(time.time() - start) * 1000,
            screenshot_path=screenshot_path
        )

        self.log_entries.append(entry)
        self._write_to_text_log(entry)
        self._save_json_log()

    def _save_screenshot(self, image: Image.Image, name: str) -> str:
        """Save screenshot and return path"""
        if not HAS_PIL:
            return None

        try:
            screenshot_path = self.screenshots_dir / f"{name}.png"
            image.save(screenshot_path)
            return str(screenshot_path.relative_to(self.output_dir))
        except Exception as e:
            print(f"[Logger] Failed to save screenshot: {e}")
            return None

    def _write_to_text_log(self, entry: LogEntry):
        """Append entry to text log"""
        with open(self.text_log_path, 'a', encoding='utf-8') as f:
            f.write(f"\n{'=' * 80}\n")
            f.write(f"Step {entry.step_number} - {entry.phase.upper()}: {entry.action}\n")
            f.write(f"Time: {entry.timestamp}\n")
            f.write(f"Duration: {entry.duration_ms:.2f}ms\n")

            if entry.success is not None:
                status = "SUCCESS" if entry.success else "FAILED"
                f.write(f"Status: {status}\n")

            if entry.error:
                f.write(f"Error: {entry.error}\n")

            if entry.screenshot_path:
                f.write(f"Screenshot: {entry.screenshot_path}\n")

            f.write(f"\nDetails:\n")
            for key, value in entry.details.items():
                if value is not None and key not in ['llm_prompt', 'llm_response']:
                    f.write(f"  {key}: {value}\n")

            # Show LLM interactions separately
            if 'llm_prompt' in entry.details and entry.details['llm_prompt']:
                f.write(f"\n  LLM Prompt:\n")
                f.write(f"  {'-' * 70}\n")
                prompt_lines = str(entry.details['llm_prompt']).split('\n')
                for line in prompt_lines[:10]:  # First 10 lines
                    f.write(f"  {line}\n")
                if len(prompt_lines) > 10:
                    f.write(f"  ... ({len(prompt_lines) - 10} more lines)\n")

            if 'llm_response' in entry.details and entry.details['llm_response']:
                f.write(f"\n  LLM Response:\n")
                f.write(f"  {'-' * 70}\n")
                response_lines = str(entry.details['llm_response']).split('\n')
                for line in response_lines[:10]:
                    f.write(f"  {line}\n")
                if len(response_lines) > 10:
                    f.write(f"  ... ({len(response_lines) - 10} more lines)\n")

            f.write(f"{'=' * 80}\n")

    def _save_json_log(self):
        """Save complete log as JSON"""
        log_data = {
            "task_name": self.task_name,
            "start_time": datetime.fromtimestamp(self.start_time).isoformat(),
            "total_steps": len(self.log_entries),
            "entries": [asdict(entry) for entry in self.log_entries]
        }

        with open(self.json_log_path, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)

    def generate_report(self) -> str:
        """Generate HTML report with all details"""
        total_duration = (time.time() - self.start_time) * 1000

        # Count successes/failures
        successful_steps = sum(1 for e in self.log_entries if e.success is True)
        failed_steps = sum(1 for e in self.log_entries if e.success is False)

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Execution Report - {self.task_name}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 20px;
        }}
        .header h1 {{
            margin: 0;
            font-size: 32px;
        }}
        .stats {{
            display: flex;
            gap: 20px;
            margin-bottom: 20px;
        }}
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            flex: 1;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .stat-value {{
            font-size: 36px;
            font-weight: bold;
            color: #667eea;
        }}
        .stat-label {{
            color: #666;
            margin-top: 5px;
        }}
        .step {{
            background: white;
            margin-bottom: 20px;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .step-header {{
            padding: 15px 20px;
            background: #f8f9fa;
            border-bottom: 2px solid #e9ecef;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .step-header.success {{
            border-left: 5px solid #28a745;
        }}
        .step-header.failure {{
            border-left: 5px solid #dc3545;
        }}
        .step-header.neutral {{
            border-left: 5px solid #6c757d;
        }}
        .step-body {{
            padding: 20px;
        }}
        .step-title {{
            font-size: 18px;
            font-weight: bold;
            color: #333;
        }}
        .step-time {{
            color: #666;
            font-size: 14px;
        }}
        .badge {{
            padding: 5px 10px;
            border-radius: 5px;
            font-size: 12px;
            font-weight: bold;
        }}
        .badge.success {{
            background: #d4edda;
            color: #155724;
        }}
        .badge.failure {{
            background: #f8d7da;
            color: #721c24;
        }}
        .badge.planning {{
            background: #d1ecf1;
            color: #0c5460;
        }}
        .badge.execution {{
            background: #fff3cd;
            color: #856404;
        }}
        .badge.reflection {{
            background: #e2e3e5;
            color: #383d41;
        }}
        .details {{
            margin-top: 15px;
        }}
        .detail-row {{
            padding: 8px 0;
            border-bottom: 1px solid #f0f0f0;
        }}
        .detail-label {{
            font-weight: bold;
            color: #555;
            display: inline-block;
            width: 150px;
        }}
        .detail-value {{
            color: #333;
        }}
        .screenshot {{
            margin-top: 15px;
            text-align: center;
        }}
        .screenshot img {{
            max-width: 100%;
            border: 2px solid #ddd;
            border-radius: 5px;
        }}
        .error-message {{
            background: #f8d7da;
            color: #721c24;
            padding: 15px;
            border-radius: 5px;
            margin-top: 15px;
        }}
        .llm-section {{
            margin-top: 15px;
            background: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            font-family: monospace;
            font-size: 12px;
            white-space: pre-wrap;
            max-height: 300px;
            overflow-y: auto;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Execution Report</h1>
        <p>Task: {self.task_name}</p>
        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>

    <div class="stats">
        <div class="stat-card">
            <div class="stat-value">{len(self.log_entries)}</div>
            <div class="stat-label">Total Steps</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{successful_steps}</div>
            <div class="stat-label">Successful</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{failed_steps}</div>
            <div class="stat-label">Failed</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{total_duration:.0f}ms</div>
            <div class="stat-label">Total Duration</div>
        </div>
    </div>

    <h2>Execution Steps</h2>
"""

        # Add each step
        for entry in self.log_entries:
            status_class = "success" if entry.success else ("failure" if entry.success is False else "neutral")
            status_text = "SUCCESS" if entry.success else ("FAILED" if entry.success is False else "N/A")

            html += f"""
    <div class="step">
        <div class="step-header {status_class}">
            <div>
                <div class="step-title">Step {entry.step_number}: {entry.action}</div>
                <div class="step-time">{entry.timestamp} - {entry.duration_ms:.2f}ms</div>
            </div>
            <div>
                <span class="badge {entry.phase}">{entry.phase.upper()}</span>
                <span class="badge {status_class}">{status_text}</span>
            </div>
        </div>
        <div class="step-body">
            <div class="details">
"""

            # Add details
            for key, value in entry.details.items():
                if value is not None and key not in ['llm_prompt', 'llm_response', 'screenshot_before', 'screenshot_after']:
                    value_str = str(value)
                    if len(value_str) > 200:
                        value_str = value_str[:200] + "..."
                    html += f"""
                <div class="detail-row">
                    <span class="detail-label">{key}:</span>
                    <span class="detail-value">{value_str}</span>
                </div>
"""

            html += """
            </div>
"""

            # Add error if present
            if entry.error:
                html += f"""
            <div class="error-message">
                <strong>Error:</strong> {entry.error}
            </div>
"""

            # Add LLM interactions
            if entry.details.get('llm_prompt'):
                prompt = str(entry.details['llm_prompt'])
                if len(prompt) > 1000:
                    prompt = prompt[:1000] + f"\n... ({len(prompt) - 1000} more characters)"
                html += f"""
            <details>
                <summary style="cursor: pointer; color: #667eea; font-weight: bold; margin-top: 10px;">Show LLM Prompt</summary>
                <div class="llm-section">{prompt}</div>
            </details>
"""

            if entry.details.get('llm_response'):
                response = str(entry.details['llm_response'])
                if len(response) > 1000:
                    response = response[:1000] + f"\n... ({len(response) - 1000} more characters)"
                html += f"""
            <details>
                <summary style="cursor: pointer; color: #667eea; font-weight: bold; margin-top: 10px;">Show LLM Response</summary>
                <div class="llm-section">{response}</div>
            </details>
"""

            # Add screenshots
            if entry.details.get('screenshot_before'):
                html += f"""
            <div class="screenshot">
                <h4>Screenshot Before</h4>
                <img src="{entry.details['screenshot_before']}" alt="Before">
            </div>
"""

            if entry.details.get('screenshot_after'):
                html += f"""
            <div class="screenshot">
                <h4>Screenshot After</h4>
                <img src="{entry.details['screenshot_after']}" alt="After">
            </div>
"""

            if entry.screenshot_path:
                html += f"""
            <div class="screenshot">
                <h4>Screenshot</h4>
                <img src="{entry.screenshot_path}" alt="Screenshot">
            </div>
"""

            html += """
        </div>
    </div>
"""

        html += """
</body>
</html>
"""

        # Save HTML report
        with open(self.html_report_path, 'w', encoding='utf-8') as f:
            f.write(html)

        return str(self.html_report_path)

    def finalize(self):
        """Finalize logging and generate report"""
        # Write summary to text log
        with open(self.text_log_path, 'a', encoding='utf-8') as f:
            f.write("\n\n" + "=" * 80 + "\n")
            f.write("EXECUTION SUMMARY\n")
            f.write("=" * 80 + "\n")
            f.write(f"Total steps: {len(self.log_entries)}\n")
            f.write(f"Total duration: {(time.time() - self.start_time) * 1000:.2f}ms\n")

            successful = sum(1 for e in self.log_entries if e.success is True)
            failed = sum(1 for e in self.log_entries if e.success is False)

            f.write(f"Successful steps: {successful}\n")
            f.write(f"Failed steps: {failed}\n")
            f.write(f"\nLog files:\n")
            f.write(f"  - Text log: {self.text_log_path}\n")
            f.write(f"  - JSON log: {self.json_log_path}\n")
            f.write(f"  - HTML report: {self.html_report_path}\n")
            f.write(f"  - Screenshots: {self.screenshots_dir}\n")

        # Generate final report
        report_path = self.generate_report()

        print(f"\n[DetailedLogger] Execution complete!")
        print(f"  Total steps: {len(self.log_entries)}")
        print(f"  Duration: {(time.time() - self.start_time):.2f}s")
        print(f"\n  Logs saved to: {self.output_dir}")
        print(f"  - Text log: {self.text_log_path.name}")
        print(f"  - JSON log: {self.json_log_path.name}")
        print(f"  - HTML report: {self.html_report_path.name}")
        print(f"  - Screenshots: {self.screenshots_dir.name}/ ({len(list(self.screenshots_dir.glob('*.png')))} files)")

        return report_path
