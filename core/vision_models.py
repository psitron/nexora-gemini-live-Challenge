"""
Abstract vision model interface and implementations.
Supports multiple vision model providers (Gemini, Nova, etc.)
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from PIL import Image


class VisionModelResponse:
    """Standardized response from vision models."""
    
    def __init__(self, text: str, finish_reason: Optional[str] = None, raw_response: Any = None):
        self.text = text
        self.finish_reason = finish_reason
        self.raw_response = raw_response
    
    def __repr__(self):
        return f"VisionModelResponse(text={self.text!r}, finish_reason={self.finish_reason})"


class VisionModel(ABC):
    """Abstract base class for vision models."""
    
    @abstractmethod
    def generate_content(
        self,
        prompt: str,
        image: Image.Image,
        max_tokens: int = 2048,
        temperature: float = 0.1,
    ) -> VisionModelResponse:
        """
        Generate content from prompt and image.
        
        Args:
            prompt: Text prompt
            image: PIL Image
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            
        Returns:
            VisionModelResponse with generated text
        """
        pass
    
    @abstractmethod
    def get_model_name(self) -> str:
        """Return the model name/identifier."""
        pass


class GeminiVisionModel(VisionModel):
    """Google Gemini vision model implementation."""
    
    def __init__(self, api_key: str, model_name: str):
        import google.generativeai as genai
        import warnings
        
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", FutureWarning)
            genai.configure(api_key=api_key)
            self._model = genai.GenerativeModel(model_name)
        
        self._model_name = model_name
    
    def generate_content(
        self,
        prompt: str,
        image: Image.Image,
        max_tokens: int = 2048,
        temperature: float = 0.1,
    ) -> VisionModelResponse:
        """Generate content using Gemini."""
        try:
            response = self._model.generate_content(
                [prompt, image],
                generation_config={
                    "max_output_tokens": max_tokens,
                    "temperature": temperature
                }
            )
            
            # Check if response has content
            if not response.candidates or not response.candidates[0].content.parts:
                finish_reason = response.candidates[0].finish_reason if response.candidates else None
                return VisionModelResponse(
                    text="",
                    finish_reason=str(finish_reason),
                    raw_response=response
                )
            
            return VisionModelResponse(
                text=response.text,
                finish_reason=None,
                raw_response=response
            )
        except Exception as e:
            raise Exception(f"Gemini API error: {e}")
    
    def get_model_name(self) -> str:
        return f"gemini:{self._model_name}"


class NovaVisionModel(VisionModel):
    """Amazon Bedrock Nova vision model implementation."""
    
    def __init__(self, region_name: str, model_id: str):
        import boto3
        from botocore.config import Config
        
        self._region_name = region_name
        self._model_id = model_id
        
        self._client = boto3.client(
            "bedrock-runtime",
            region_name=region_name,
            config=Config(
                connect_timeout=3600,  # 60 minutes
                read_timeout=3600,
                retries={'max_attempts': 1}
            )
        )
    
    def generate_content(
        self,
        prompt: str,
        image: Image.Image,
        max_tokens: int = 2048,
        temperature: float = 0.1,
    ) -> VisionModelResponse:
        """Generate content using Amazon Nova."""
        import base64
        import json
        from io import BytesIO
        
        try:
            # Convert PIL Image to base64
            buffer = BytesIO()
            image.save(buffer, format="PNG")
            image_bytes = buffer.getvalue()
            base64_image = base64.b64encode(image_bytes).decode("utf-8")
            
            # Build request for Nova Invoke API
            message_list = [
                {
                    "role": "user",
                    "content": [
                        {
                            "image": {
                                "format": "png",
                                "source": {
                                    "bytes": base64_image
                                }
                            }
                        },
                        {"text": prompt}
                    ]
                }
            ]
            
            request_body = {
                "schemaVersion": "messages-v1",
                "messages": message_list,
                "inferenceConfig": {
                    "maxTokens": max_tokens,
                    "temperature": temperature,
                    "topP": 0.9
                }
            }
            
            # Invoke Nova model
            response = self._client.invoke_model(
                modelId=self._model_id,
                body=json.dumps(request_body)
            )
            
            # Parse response
            response_body = json.loads(response.get("body").read())
            
            # Extract text from Nova response format
            output = response_body.get("output", {})
            message = output.get("message", {})
            content = message.get("content", [])
            
            if content and len(content) > 0:
                text = content[0].get("text", "")
                return VisionModelResponse(
                    text=text,
                    finish_reason=response_body.get("stopReason"),
                    raw_response=response_body
                )
            else:
                return VisionModelResponse(
                    text="",
                    finish_reason="no_content",
                    raw_response=response_body
                )
        
        except Exception as e:
            error_msg = str(e)
            error_type = type(e).__name__
            
            # Provide helpful error messages
            if "NoCredentialsError" in error_type:
                raise Exception(f"Nova API error: AWS credentials not configured. Run 'aws configure' or set AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY environment variables. Error: {error_msg}")
            elif "AccessDeniedException" in error_type or "access" in error_msg.lower():
                raise Exception(f"Nova API error: Model access denied. Enable '{self._model_id}' in AWS Bedrock console (https://console.aws.amazon.com/bedrock). Error: {error_msg}")
            elif "ValidationException" in error_type or "not available" in error_msg.lower():
                raise Exception(f"Nova API error: Model '{self._model_id}' not available in region '{self._region_name}'. Check AWS Bedrock model availability. Error: {error_msg}")
            else:
                raise Exception(f"Nova API error ({error_type}): {error_msg}")
    
    def get_model_name(self) -> str:
        return f"nova:{self._model_id}"


def create_vision_model(provider: str, **kwargs) -> VisionModel:
    """
    Factory function to create vision model instances.
    Model names and IDs come from kwargs (typically from config/settings).
    
    Args:
        provider: "gemini" or "nova"
        **kwargs: Provider-specific arguments
            For Gemini: api_key, model_name (from GEMINI_VISION_MODEL)
            For Nova: region_name (from NOVA_REGION), model_id (from NOVA_MODEL_ID)
    
    Returns:
        VisionModel instance
    """
    from config.settings import get_settings
    settings = get_settings()
    provider = provider.lower()
    
    if provider == "gemini":
        return GeminiVisionModel(
            api_key=kwargs.get("api_key") or settings.models.gemini_api_key,
            model_name=kwargs.get("model_name") or settings.models.gemini_vision_model
        )
    elif provider == "nova":
        return NovaVisionModel(
            region_name=kwargs.get("region_name") or settings.models.nova_region,
            model_id=kwargs.get("model_id") or settings.models.nova_model_id
        )
    else:
        raise ValueError(f"Unknown vision model provider: {provider}. Supported: 'gemini', 'nova'")
