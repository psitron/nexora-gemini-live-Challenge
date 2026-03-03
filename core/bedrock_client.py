from __future__ import annotations

"""
Unified Amazon Bedrock client using the Converse API.

The Converse API is model-agnostic: it works with Nova, Claude via Bedrock,
Llama, Mistral, and any other model available in the Bedrock console.

Key difference from invoke_model:
- Converse API takes **raw bytes** for images (NOT base64).
- Unified request/response format across all models.
"""

from io import BytesIO
from typing import List, Optional, Tuple

from PIL import Image


class BedrockClient:
    """Reusable Bedrock Converse API wrapper."""

    def __init__(self, region_name: str = "us-east-1") -> None:
        import boto3
        from botocore.config import Config

        self._region_name = region_name
        self._client = boto3.client(
            "bedrock-runtime",
            region_name=region_name,
            config=Config(
                connect_timeout=60,
                read_timeout=120,
                retries={"max_attempts": 2},
            ),
        )

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def converse_text(
        self,
        model_id: str,
        prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.1,
        system_prompt: Optional[str] = None,
    ) -> str:
        """Text-only call.  Returns the assistant's text response."""
        messages = [{"role": "user", "content": [{"text": prompt}]}]
        return self._converse(
            model_id=model_id,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            system_prompt=system_prompt,
        )

    def converse_with_image(
        self,
        model_id: str,
        prompt: str,
        image: Image.Image,
        max_tokens: int = 2048,
        temperature: float = 0.1,
    ) -> str:
        """Send a single image + prompt.  Returns assistant text."""
        img_bytes = self._pil_to_png_bytes(image)
        messages = [
            {
                "role": "user",
                "content": [
                    {"image": {"format": "png", "source": {"bytes": img_bytes}}},
                    {"text": prompt},
                ],
            }
        ]
        return self._converse(
            model_id=model_id,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    def converse_with_images(
        self,
        model_id: str,
        prompt: str,
        images: List[Tuple[str, Image.Image]],
        max_tokens: int = 2048,
        temperature: float = 0.1,
    ) -> str:
        """Send multiple labelled images + prompt.  Returns assistant text.

        Args:
            images: list of (label, PIL.Image) tuples.
        """
        content: list = []
        for label, img in images:
            content.append({"text": label})
            content.append(
                {"image": {"format": "png", "source": {"bytes": self._pil_to_png_bytes(img)}}}
            )
        content.append({"text": prompt})

        messages = [{"role": "user", "content": content}]
        return self._converse(
            model_id=model_id,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _pil_to_png_bytes(image: Image.Image) -> bytes:
        """Convert a PIL Image to raw PNG bytes (NOT base64)."""
        buf = BytesIO()
        image.save(buf, format="PNG")
        return buf.getvalue()

    def _converse(
        self,
        model_id: str,
        messages: list,
        max_tokens: int,
        temperature: float,
        system_prompt: Optional[str] = None,
    ) -> str:
        """Thin wrapper around ``client.converse()`` with error handling."""
        kwargs: dict = {
            "modelId": model_id,
            "messages": messages,
            "inferenceConfig": {
                "maxTokens": max_tokens,
                "temperature": temperature,
            },
        }
        if system_prompt:
            kwargs["system"] = [{"text": system_prompt}]

        try:
            response = self._client.converse(**kwargs)
        except Exception as exc:
            raise self._wrap_error(exc, model_id) from exc

        # Extract assistant text from Converse API response
        try:
            output = response["output"]["message"]["content"]
            parts = [block["text"] for block in output if "text" in block]
            return "\n".join(parts).strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(
                f"Bedrock Converse: unexpected response structure: {exc}"
            ) from exc

    def _wrap_error(self, exc: Exception, model_id: str) -> Exception:
        """Return a friendlier error message for common AWS problems."""
        error_type = type(exc).__name__
        msg = str(exc)

        if "NoCredentialsError" in error_type or "NoCredentialsError" in msg:
            return RuntimeError(
                "Bedrock: AWS credentials not configured. "
                "Run 'aws configure' or set AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY."
            )
        if "AccessDeniedException" in error_type or "access" in msg.lower():
            return RuntimeError(
                f"Bedrock: Access denied for model '{model_id}'. "
                "Enable the model in the AWS Bedrock console "
                "(https://console.aws.amazon.com/bedrock)."
            )
        if "ValidationException" in error_type or "not available" in msg.lower():
            return RuntimeError(
                f"Bedrock: Model '{model_id}' not available in region "
                f"'{self._region_name}'. Check Bedrock model availability."
            )
        return RuntimeError(f"Bedrock ({error_type}): {msg}")
