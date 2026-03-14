"""
Bedrock Knowledge Base Client - RAG for off-script student questions.

Only used when students ask questions outside the curriculum.
Never used for curriculum task execution.
"""

import logging
import os
from typing import Optional

import boto3

logger = logging.getLogger(__name__)

REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
KB_ID = os.environ.get("VTA_KB_ID", "")


class KBClient:
    """Client for Bedrock Knowledge Base retrieve-and-generate."""

    def __init__(self, kb_id: str = None, region: str = None):
        self.kb_id = kb_id or KB_ID
        self.region = region or REGION
        self.client = boto3.client(
            "bedrock-agent-runtime", region_name=self.region,
        )

    async def query(self, question: str) -> str:
        """
        Query the Knowledge Base and return a generated answer.

        Args:
            question: Student's question

        Returns:
            Generated answer string
        """
        if not self.kb_id:
            return "Knowledge Base is not configured."

        try:
            response = self.client.retrieve_and_generate(
                input={"text": question},
                retrieveAndGenerateConfiguration={
                    "type": "KNOWLEDGE_BASE",
                    "knowledgeBaseConfiguration": {
                        "knowledgeBaseId": self.kb_id,
                        "modelArn": f"arn:aws:bedrock:{self.region}::foundation-model/anthropic.claude-3-haiku-20240307-v1:0",
                        "retrievalConfiguration": {
                            "vectorSearchConfiguration": {
                                "numberOfResults": 3,
                            }
                        },
                    },
                },
            )

            output = response.get("output", {}).get("text", "")
            if not output:
                return "I couldn't find relevant information for that question."
            return output

        except Exception as e:
            logger.error(f"KB query failed: {e}")
            return f"I wasn't able to look that up right now. Let me answer from what I know."

    async def retrieve(self, question: str) -> list[str]:
        """
        Retrieve raw documents without generation.

        Args:
            question: Search query

        Returns:
            List of retrieved text chunks
        """
        if not self.kb_id:
            return []

        try:
            response = self.client.retrieve(
                knowledgeBaseId=self.kb_id,
                retrievalQuery={"text": question},
                retrievalConfiguration={
                    "vectorSearchConfiguration": {
                        "numberOfResults": 3,
                    }
                },
            )

            results = []
            for item in response.get("retrievalResults", []):
                text = item.get("content", {}).get("text", "")
                if text:
                    results.append(text)
            return results

        except Exception as e:
            logger.error(f"KB retrieve failed: {e}")
            return []
