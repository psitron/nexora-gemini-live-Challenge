"""
Nova Sonic S2S Event Builders for VTA.

Adapted from the Nova S2S Workshop SDK reference.
Stripped of all tool configuration — Sonic is voice-only now.
Brain (Bedrock Converse API) handles intent classification and Q&A.
"""

import json


# Minimal voice-only system prompt — task-specific instructions are
# baked into per-task prompt_override via reconnect().
ARIA_SYSTEM_PROMPT = """You are ARIA, a friendly AI tutor. Speak naturally and engagingly.
Follow the instructions below."""


class S2sEvent:
    """Static event builders for Nova Sonic bidirectional streaming."""

    DEFAULT_INFER_CONFIG = {
        "maxTokens": 1024,
        "topP": 0.95,
        "temperature": 0.7,
    }

    DEFAULT_AUDIO_INPUT_CONFIG = {
        "mediaType": "audio/lpcm",
        "sampleRateHertz": 16000,
        "sampleSizeBits": 16,
        "channelCount": 1,
        "audioType": "SPEECH",
        "encoding": "base64",
    }

    DEFAULT_AUDIO_OUTPUT_CONFIG = {
        "mediaType": "audio/lpcm",
        "sampleRateHertz": 24000,
        "sampleSizeBits": 16,
        "channelCount": 1,
        "voiceId": "matthew",
        "encoding": "base64",
        "audioType": "SPEECH",
    }

    @staticmethod
    def session_start(inference_config=None):
        config = inference_config or S2sEvent.DEFAULT_INFER_CONFIG
        return {"event": {"sessionStart": {"inferenceConfiguration": config}}}

    @staticmethod
    def prompt_start(prompt_name, audio_output_config=None):
        return {
            "event": {
                "promptStart": {
                    "promptName": prompt_name,
                    "textOutputConfiguration": {"mediaType": "text/plain"},
                    "audioOutputConfiguration": audio_output_config or S2sEvent.DEFAULT_AUDIO_OUTPUT_CONFIG,
                }
            }
        }

    @staticmethod
    def content_start_text(prompt_name, content_name, role="USER", interactive=False):
        return {
            "event": {
                "contentStart": {
                    "promptName": prompt_name,
                    "contentName": content_name,
                    "type": "TEXT",
                    "interactive": interactive,
                    "role": role,
                    "textInputConfiguration": {"mediaType": "text/plain"},
                }
            }
        }

    @staticmethod
    def text_input(prompt_name, content_name, system_prompt=None):
        return {
            "event": {
                "textInput": {
                    "promptName": prompt_name,
                    "contentName": content_name,
                    "content": system_prompt or ARIA_SYSTEM_PROMPT,
                }
            }
        }

    @staticmethod
    def content_end(prompt_name, content_name):
        return {
            "event": {
                "contentEnd": {
                    "promptName": prompt_name,
                    "contentName": content_name,
                }
            }
        }

    @staticmethod
    def content_start_audio(prompt_name, content_name, audio_input_config=None):
        return {
            "event": {
                "contentStart": {
                    "promptName": prompt_name,
                    "contentName": content_name,
                    "type": "AUDIO",
                    "interactive": True,
                    "role": "USER",
                    "audioInputConfiguration": audio_input_config or S2sEvent.DEFAULT_AUDIO_INPUT_CONFIG,
                }
            }
        }

    @staticmethod
    def audio_input(prompt_name, content_name, content):
        return {
            "event": {
                "audioInput": {
                    "promptName": prompt_name,
                    "contentName": content_name,
                    "content": content,
                }
            }
        }

    @staticmethod
    def prompt_end(prompt_name):
        return {"event": {"promptEnd": {"promptName": prompt_name}}}

    @staticmethod
    def session_end():
        return {"event": {"sessionEnd": {}}}
