"""
Demo: Code Agent Usage

Shows how to use the Code Agent for complex tasks that are better
handled with code than GUI automation.
"""

from core.code_agent import CodeAgent


def demo_spreadsheet_task():
    """Demo: Calculate sum of a column in a spreadsheet."""
    print("=" * 60)
    print("DEMO 1: Spreadsheet Calculation")
    print("=" * 60)

    agent = CodeAgent()

    task = """
    Open the file E:/data/sales.xlsx (create it if it doesn't exist).
    Calculate the sum of column A (rows 1-10).
    Write the result to cell B1.
    Save the file.
    """

    result = agent.execute_task(task)

    print(f"\nResult: {result.completion_reason}")
    print(f"Steps executed: {result.steps_executed}/{result.max_steps}")
    print(f"Summary: {result.summary}")

    if result.execution_history:
        print("\nExecution History:")
        for step in result.execution_history:
            print(f"  Step {step.step_number} ({step.code_type}): {'✓' if step.success else '✗'}")
            if step.error:
                print(f"    Error: {step.error}")


def demo_bulk_files():
    """Demo: Rename 10 files in bulk."""
    print("\n" + "=" * 60)
    print("DEMO 2: Bulk File Renaming")
    print("=" * 60)

    agent = CodeAgent()

    task = """
    In the directory E:/temp/test:
    1. Create 10 test files named test_1.txt through test_10.txt
    2. Rename them to file_001.txt through file_010.txt (zero-padded)
    3. List the final directory contents
    """

    context = {
        "directory": "E:/temp/test",
        "file_count": 10
    }

    result = agent.execute_task(task, context=context)

    print(f"\nResult: {result.completion_reason}")
    print(f"Steps executed: {result.steps_executed}/{result.max_steps}")

    if result.success:
        print("✓ Files renamed successfully!")


def demo_data_processing():
    """Demo: Process CSV data."""
    print("\n" + "=" * 60)
    print("DEMO 3: Data Processing")
    print("=" * 60)

    agent = CodeAgent()

    task = """
    Create a CSV file E:/temp/employees.csv with sample employee data:
    - name, department, salary (5 rows)

    Then:
    1. Calculate average salary by department
    2. Find highest paid employee
    3. Save summary to E:/temp/summary.txt
    """

    result = agent.execute_task(task)

    print(f"\nResult: {result.completion_reason}")
    print(f"Steps executed: {result.steps_executed}/{result.max_steps}")

    if result.success:
        print("✓ Data processed successfully!")
        print("\nCheck E:/temp/summary.txt for results")


if __name__ == "__main__":
    print("""
    ============================================================
                       CODE AGENT DEMO

      Demonstrates using the Code Agent for complex tasks
      that are better handled with code than GUI automation.
    ============================================================
    """)

    # Run demos
    try:
        demo_spreadsheet_task()
    except Exception as e:
        print(f"Demo 1 failed: {e}")

    try:
        demo_bulk_files()
    except Exception as e:
        print(f"Demo 2 failed: {e}")

    try:
        demo_data_processing()
    except Exception as e:
        print(f"Demo 3 failed: {e}")

    print("\n" + "=" * 60)
    print("DEMO COMPLETE")
    print("=" * 60)
