"""
Hybrid AI Agent – minimal Gradio UI.

Run: python ui_app.py
Then open the URL shown (e.g. http://127.0.0.1:7860).
"""

from __future__ import annotations

import gradio as gr

from core.agent_loop import AgentLoop


def run_agent(goal: str) -> str:
    if not goal or not goal.strip():
        return "Please enter a goal."
    loop = AgentLoop()
    result = loop.run(goal.strip())
    return (
        f"Status: {result.goal_status}\n"
        f"Steps executed: {result.steps_executed}\n"
        f"Final node: {result.final_node_id}\n"
        f"Outcomes: {[o.label.value for o in result.outcomes]}"
    )


def main() -> None:
    with gr.Blocks(title="Hybrid AI Agent") as app:
        gr.Markdown("# Hybrid AI Agent")
        goal_in = gr.Textbox(
            label="Goal",
            placeholder="e.g. Open https://python.org and list my sessions folder",
            lines=3,
        )
        run_btn = gr.Button("Run")
        out = gr.Textbox(label="Result", lines=8, interactive=False)
        run_btn.click(fn=run_agent, inputs=goal_in, outputs=out)
    app.launch()


if __name__ == "__main__":
    main()
