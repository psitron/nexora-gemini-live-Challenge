"""
Real-World Task Examples - Test Your Agent!

Run these example tasks to see your agent in action.
Each task is self-contained and easy to verify.
"""

from core.agent_loop import AgentLoop
import tempfile
import os
from pathlib import Path


def example_1_simple_file():
    """Example 1: Create a simple text file (30 seconds)"""
    print("\n" + "=" * 70)
    print("EXAMPLE 1: Create a Simple Text File")
    print("=" * 70)
    print("\nTask: Create a file with your name and today's date")
    print("Difficulty: Easy")
    print("Uses: L0 (File Operations)\n")

    agent = AgentLoop()

    test_file = os.path.join(tempfile.gettempdir(), "my_first_agent_file.txt")

    task = f"""
    Create a text file at {test_file} with the following content:

    Hello! My name is AI Agent.
    Today's date is 2026-03-01.
    This is my first automated task!
    """

    print(f"Running task...\n")
    result = agent.run(task)

    print("\n" + "=" * 70)
    print("RESULT")
    print("=" * 70)
    print(f"Status: {result.goal_status}")
    print(f"Steps: {result.steps_executed}")

    # Verify
    if os.path.exists(test_file):
        with open(test_file, 'r') as f:
            content = f.read()
        print(f"\n[OK] File created successfully!")
        print(f"Location: {test_file}")
        print(f"\nContent preview:")
        print("-" * 70)
        print(content[:200])
        print("-" * 70)

        # Cleanup
        os.remove(test_file)
        print(f"\n[INFO] Test file cleaned up")
    else:
        print(f"\n[FAIL] File was not created at {test_file}")


def example_2_multiple_files():
    """Example 2: Create multiple related files (1 minute)"""
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Create Multiple Related Files")
    print("=" * 70)
    print("\nTask: Create a project structure with multiple files")
    print("Difficulty: Medium")
    print("Uses: L0 (File Operations)\n")

    agent = AgentLoop()

    test_dir = os.path.join(tempfile.gettempdir(), "agent_project")

    task = f"""
    Create a project structure:
    1. Create directory: {test_dir}
    2. Create file: {test_dir}/README.md with content "# My Project"
    3. Create file: {test_dir}/config.txt with content "version=1.0"
    4. Create file: {test_dir}/notes.txt with content "Project started today"
    """

    print(f"Running task...\n")
    result = agent.run(task)

    print("\n" + "=" * 70)
    print("RESULT")
    print("=" * 70)
    print(f"Status: {result.goal_status}")
    print(f"Steps: {result.steps_executed}")

    # Verify
    if os.path.exists(test_dir):
        files = os.listdir(test_dir)
        print(f"\n[OK] Project directory created!")
        print(f"Location: {test_dir}")
        print(f"\nFiles created: {len(files)}")
        for file in files:
            file_path = os.path.join(test_dir, file)
            size = os.path.getsize(file_path)
            print(f"  - {file} ({size} bytes)")

        # Show content of one file
        readme_path = os.path.join(test_dir, "README.md")
        if os.path.exists(readme_path):
            with open(readme_path, 'r') as f:
                content = f.read()
            print(f"\nREADME.md content:")
            print("-" * 70)
            print(content)
            print("-" * 70)

        # Cleanup
        import shutil
        shutil.rmtree(test_dir)
        print(f"\n[INFO] Test directory cleaned up")
    else:
        print(f"\n[FAIL] Directory was not created at {test_dir}")


def example_3_file_manipulation():
    """Example 3: Read and modify files (1 minute)"""
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Read and Modify Files")
    print("=" * 70)
    print("\nTask: Create a file, read it, and append content")
    print("Difficulty: Medium")
    print("Uses: L0 (File Operations)\n")

    agent = AgentLoop()

    test_file = os.path.join(tempfile.gettempdir(), "shopping_list.txt")

    task = f"""
    1. Create a file at {test_file} with content:
       Shopping List:
       - Milk
       - Bread

    2. Then append these items to the file:
       - Eggs
       - Butter
    """

    print(f"Running task...\n")
    result = agent.run(task)

    print("\n" + "=" * 70)
    print("RESULT")
    print("=" * 70)
    print(f"Status: {result.goal_status}")
    print(f"Steps: {result.steps_executed}")

    # Verify
    if os.path.exists(test_file):
        with open(test_file, 'r') as f:
            content = f.read()
        print(f"\n[OK] File modified successfully!")
        print(f"\nFinal content:")
        print("-" * 70)
        print(content)
        print("-" * 70)

        # Check if all items present
        items = ["Milk", "Bread", "Eggs", "Butter"]
        found_items = [item for item in items if item in content]
        print(f"\nItems found: {len(found_items)}/{len(items)}")
        for item in found_items:
            print(f"  [OK] {item}")

        # Cleanup
        os.remove(test_file)
        print(f"\n[INFO] Test file cleaned up")
    else:
        print(f"\n[FAIL] File was not created")


def example_4_open_notepad():
    """Example 4: Open Notepad and type (Windows only, 30 seconds)"""
    print("\n" + "=" * 70)
    print("EXAMPLE 4: Open Notepad and Type Text (Windows)")
    print("=" * 70)
    print("\nTask: Open Notepad and type a message")
    print("Difficulty: Medium")
    print("Uses: L2 (Desktop Automation)")
    print("\n[WARNING] This will actually open Notepad on your screen!")
    print("Close it manually when done.\n")

    import platform
    if platform.system() != "Windows":
        print("[SKIP] This example is Windows-only")
        print("Try example_5_open_app_mac() on macOS instead")
        return

    response = input("Continue? (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("[SKIP] User cancelled")
        return

    agent = AgentLoop()

    task = """
    1. Open Notepad
    2. Wait 2 seconds
    3. Type this message: "Hello! This was typed by an AI agent."
    4. Wait 3 seconds so I can see it
    """

    print(f"\nRunning task...\n")
    result = agent.run(task)

    print("\n" + "=" * 70)
    print("RESULT")
    print("=" * 70)
    print(f"Status: {result.goal_status}")
    print(f"Steps: {result.steps_executed}")
    print("\n[INFO] Check if Notepad opened and text was typed!")
    print("[INFO] Close Notepad manually when done (don't save)")


def example_5_open_app_mac():
    """Example 5: Open TextEdit and type (macOS only, 30 seconds)"""
    print("\n" + "=" * 70)
    print("EXAMPLE 5: Open TextEdit and Type Text (macOS)")
    print("=" * 70)
    print("\nTask: Open TextEdit and type a message")
    print("Difficulty: Medium")
    print("Uses: L2 (Desktop Automation)")
    print("\n[WARNING] This will actually open TextEdit on your screen!")
    print("Close it manually when done.\n")

    import platform
    if platform.system() != "Darwin":
        print("[SKIP] This example is macOS-only")
        print("Try example_4_open_notepad() on Windows instead")
        return

    response = input("Continue? (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("[SKIP] User cancelled")
        return

    agent = AgentLoop()

    task = """
    1. Open TextEdit
    2. Wait 2 seconds
    3. Type this message: "Hello! This was typed by an AI agent."
    4. Wait 3 seconds so I can see it
    """

    print(f"\nRunning task...\n")
    result = agent.run(task)

    print("\n" + "=" * 70)
    print("RESULT")
    print("=" * 70)
    print(f"Status: {result.goal_status}")
    print(f"Steps: {result.steps_executed}")
    print("\n[INFO] Check if TextEdit opened and text was typed!")
    print("[INFO] Close TextEdit manually when done (don't save)")


def example_6_calculator():
    """Example 6: Open Calculator (Windows, 30 seconds)"""
    print("\n" + "=" * 70)
    print("EXAMPLE 6: Open Calculator (Windows)")
    print("=" * 70)
    print("\nTask: Open Windows Calculator")
    print("Difficulty: Easy")
    print("Uses: L2 (Desktop Automation)")
    print("\n[WARNING] This will open Calculator on your screen!\n")

    import platform
    if platform.system() != "Windows":
        print("[SKIP] This example is Windows-only")
        return

    response = input("Continue? (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("[SKIP] User cancelled")
        return

    agent = AgentLoop()

    task = """
    Open Calculator application
    """

    print(f"\nRunning task...\n")
    result = agent.run(task)

    print("\n" + "=" * 70)
    print("RESULT")
    print("=" * 70)
    print(f"Status: {result.goal_status}")
    print(f"Steps: {result.steps_executed}")
    print("\n[INFO] Check if Calculator opened!")
    print("[INFO] Close it manually when done")


def example_7_organize_files():
    """Example 7: Organize files into folders (2 minutes)"""
    print("\n" + "=" * 70)
    print("EXAMPLE 7: Organize Files into Folders")
    print("=" * 70)
    print("\nTask: Create files and organize them by type")
    print("Difficulty: Hard")
    print("Uses: L0 (File Operations)\n")

    agent = AgentLoop()

    base_dir = os.path.join(tempfile.gettempdir(), "file_organizer_test")

    task = f"""
    1. Create directory: {base_dir}

    2. Create these files in {base_dir}:
       - notes.txt with content "My notes"
       - todo.txt with content "My tasks"
       - image_info.txt with content "Photos go here"

    3. Create subdirectories:
       - {base_dir}/documents
       - {base_dir}/images

    4. Move the txt files to the documents folder
    """

    print(f"Running task...\n")
    result = agent.run(task)

    print("\n" + "=" * 70)
    print("RESULT")
    print("=" * 70)
    print(f"Status: {result.goal_status}")
    print(f"Steps: {result.steps_executed}")

    # Verify
    if os.path.exists(base_dir):
        print(f"\n[OK] Base directory created!")

        docs_dir = os.path.join(base_dir, "documents")
        if os.path.exists(docs_dir):
            files = os.listdir(docs_dir)
            print(f"\nDocuments folder: {len(files)} files")
            for file in files:
                print(f"  - {file}")

        # Cleanup
        import shutil
        shutil.rmtree(base_dir)
        print(f"\n[INFO] Test directory cleaned up")
    else:
        print(f"\n[FAIL] Base directory was not created")


def show_menu():
    """Show menu of available examples"""
    print("""
    ======================================================================

                    REAL-WORLD TASK EXAMPLES

                Test Your AI Agent with Real Tasks!

    ======================================================================

    FILE OPERATIONS (No API key needed):

    1. Simple File Creation (30 sec)
       - Create a single text file with content
       - Easy verification

    2. Multiple Files (1 min)
       - Create a project structure with multiple files
       - See how the agent handles complex tasks

    3. File Manipulation (1 min)
       - Read, modify, and append to files
       - Tests sequential operations

    7. Organize Files (2 min)
       - Create files and organize into folders
       - Complex multi-step task

    ======================================================================

    DESKTOP AUTOMATION (Requires L2 support):

    4. Open Notepad (Windows, 30 sec)
       - Opens Notepad and types text
       - Visual confirmation

    5. Open TextEdit (macOS, 30 sec)
       - Opens TextEdit and types text
       - Visual confirmation

    6. Open Calculator (Windows, 30 sec)
       - Opens Calculator application
       - Simple desktop interaction

    ======================================================================

    Which example would you like to try?

    Enter 1-7, or 'all' to run all file examples (skips desktop apps)
    Enter 'q' to quit
    """)


def main():
    """Main function - run examples"""

    examples = {
        '1': example_1_simple_file,
        '2': example_2_multiple_files,
        '3': example_3_file_manipulation,
        '4': example_4_open_notepad,
        '5': example_5_open_app_mac,
        '6': example_6_calculator,
        '7': example_7_organize_files,
    }

    while True:
        show_menu()
        choice = input("Your choice: ").strip().lower()

        if choice == 'q':
            print("\nGoodbye!")
            break

        if choice == 'all':
            print("\nRunning all file operation examples...")
            for key in ['1', '2', '3', '7']:
                try:
                    examples[key]()
                    input("\nPress Enter to continue to next example...")
                except KeyboardInterrupt:
                    print("\n\nStopped by user")
                    break
                except Exception as e:
                    print(f"\n[ERROR] Example failed: {e}")
                    import traceback
                    traceback.print_exc()
            continue

        if choice in examples:
            try:
                examples[choice]()
            except KeyboardInterrupt:
                print("\n\nStopped by user")
            except Exception as e:
                print(f"\n[ERROR] Example failed: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"\n[ERROR] Invalid choice: {choice}")

        input("\nPress Enter to return to menu...")


if __name__ == "__main__":
    print("""
    ======================================================================
                        WELCOME TO AI AGENT TESTING!
    ======================================================================

    This script contains real-world examples you can test right now.

    Each example:
    - Shows what the agent will do
    - Runs the task automatically
    - Verifies the result
    - Cleans up after itself

    Safe to run - all tests use temporary files!

    ======================================================================
    """)

    try:
        main()
    except KeyboardInterrupt:
        print("\n\nGoodbye!")
