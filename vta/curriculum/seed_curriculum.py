"""
Seed DynamoDB vta_curriculum table from a curriculum JSON file.

Usage:
    python -m vta.curriculum.seed_curriculum --file vta/curriculum/linux_basics.json
"""

import argparse
import json
import sys

import boto3


def seed(filepath: str, region: str = "us-east-1"):
    dynamodb = boto3.resource("dynamodb", region_name=region)
    table = dynamodb.Table("vta_curriculum")

    with open(filepath, "r") as f:
        tutorial = json.load(f)

    tutorial_id = tutorial["tutorial_id"]
    print(f"Seeding tutorial: {tutorial_id}")

    # Store tutorial metadata as root record
    table.put_item(Item={
        "tutorial_id": tutorial_id,
        "task_id": "__meta__",
        "title": tutorial["title"],
        "description": tutorial.get("description", ""),
        "pdf_s3_key": tutorial.get("pdf_s3_key", tutorial.get("pdf_url", "")),
    })

    for task in tutorial["tasks"]:
        item = {
            "tutorial_id": tutorial_id,
            "task_id": task["task_id"],
            "type": task["type"],
            "title": task["title"],
            "slide_number": task.get("slide_number"),
            "slide_context": task.get("slide_context"),
            "sonic_prompt": task.get("sonic_prompt"),
            "subtasks": task.get("subtasks", []),
            "goal": task.get("goal"),
        }
        # Remove None values (DynamoDB doesn't accept None)
        item = {k: v for k, v in item.items() if v is not None}
        table.put_item(Item=item)
        print(f"  Seeded task {task['task_id']}: {task['title']}")

    print(f"\nDone. {len(tutorial['tasks'])} tasks seeded for {tutorial_id}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed VTA curriculum into DynamoDB")
    parser.add_argument("--file", required=True, help="Path to curriculum JSON file")
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    args = parser.parse_args()
    seed(args.file, args.region)
