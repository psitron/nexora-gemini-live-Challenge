"""
Automated Excel test (no user input required)
"""

from core.vision_agent_logged import VisionAgentLogged

print("="*70)
print("AUTOMATED EXCEL TEST")
print("="*70)
print()

# Simple Excel task
task = """
Open Excel and create a simple budget spreadsheet:
1. Open Windows search (Win+S) and search for "Excel"
2. Click on Excel to launch it
3. Click "Blank workbook" to start a new spreadsheet
4. Click cell A1
5. Type "Income" and press Enter
6. Type "Salary: 5000" in A2 and press Enter
7. Type "Freelance: 2000" in A3 and press Enter
8. Click cell A5
9. Type "Total" and press Enter
10. In A6, enter the formula: =SUM(A2:A3)
11. Press Enter to calculate the total
12. When the total shows "7000", task is complete
"""

print(f"Task: {task}")
print()
print("Starting agent...")
print("="*70)
print()

# Run agent
agent = VisionAgentLogged()
result = agent.run(task)

print()
print("="*70)
print("RESULT")
print("="*70)
print(f"Success: {result.success}")
print(f"Steps: {result.steps_executed}")
print(f"Message: {result.message}")
print()

if result.success:
    print("✅ AGENT COMPLETED THE TASK!")
else:
    print(f"❌ Agent did not complete task:")
    print(f"   {result.message}")
