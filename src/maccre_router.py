"""
maccre_core/maccre_router.py — MACCRE Cognitive Router
========================================================
Central dispatch layer for all LLM generation within the MACCREv2 monorepo.

Rules (.agrules):
  - All LLM calls MUST route through this module.
  - Direct imports of `google.genai` are forbidden in project code.
  - Model names MUST use the `VerifiedModel` enum.
  - `generate_with_tools()` is the Cognitive Router entry-point; it loads
    the appropriate tool subset from `maccre_core.tools.tool_registry` and
    passes them to Gemini Function Calling automatically.
"""
import os
from enum import Enum
from typing import Any, Callable, Optional, Sequence, cast
import keyring
from dotenv import load_dotenv
from google import genai
from google.genai import types
from maccre_core.orchestration.google_auth import get_google_credentials
from maccre_core.orchestration.windows_vault import get_native_credential

class VerifiedModel(str, Enum):
    # Text Generation Models
    GEMMA_3_1B_IT = "gemma-3-1b-it"
    GEMMA_3_4B_IT = "gemma-3-4b-it"
    GEMMA_3_12B_IT = "gemma-3-12b-it"
    GEMMA_3_27B_IT = "gemma-3-27b-it"
    GEMMA_3N_E4B_IT = "gemma-3n-e4b-it"
    GEMMA_3N_E2B_IT = "gemma-3n-e2b-it"
    GEMINI_FLASH_LITE_LATEST = "gemini-flash-lite-latest"
    GEMINI_2_5_FLASH = "gemini-2.5-flash"
    GEMINI_2_5_FLASH_LITE = "gemini-2.5-flash-lite"
    GEMINI_2_5_FLASH_LITE_PREVIEW_09_2025 = "gemini-2.5-flash-lite-preview-09-2025"
    GEMINI_3_FLASH_PREVIEW = "gemini-3-flash-preview"
    GEMINI_3_1_FLASH_LITE_PREVIEW = "gemini-3.1-flash-lite-preview"
    
    # Native TTS Models
    GEMINI_2_5_FLASH_PREVIEW_TTS = "gemini-2.5-flash-preview-tts"
    GEMINI_2_5_PRO_PREVIEW_TTS = "gemini-2.5-pro-preview-tts"
    
    # Image Generation Models
    GEMINI_2_5_FLASH_IMAGE = "gemini-2.5-flash-image"
    GEMINI_3_PRO_IMAGE_PREVIEW = "gemini-3-pro-image-preview"
    GEMINI_3_1_FLASH_IMAGE_PREVIEW = "gemini-3.1-flash-image-preview"
    
    # Deep Research Models
    DEEP_RESEARCH_PRO_PREVIEW_12_2025 = "deep-research-pro-preview-12-2025"
    
    # Embedding Models
    GEMINI_EMBEDDING_001 = "gemini-embedding-001"
    GEMINI_EMBEDDING_2_PREVIEW = "gemini-embedding-2-preview"


class MaccreRouter:
    def __init__(self):
        # Load environment variables as specified
        load_dotenv("B:\\MACCREv2\\.env")
        
        # 1. Ephemeral OAuth for Workspace (Drive/Sheets)
        self.creds = get_google_credentials()
        
        # 2. Encrypted OS Vault for AI Studio
        api_key = get_native_credential("MACCRE_Sovereign")
        if not api_key:
            raise ValueError("CRITICAL: AI Studio API Key not found in Windows Credential Manager.")
            
        # 3. Initialize Standard AI Studio Clients
        self.client = genai.Client(api_key=api_key)
        self.client_beta = genai.Client(
            api_key=api_key, 
            http_options={"api_version": "v1beta"}
        )
        
        # Enterprise Escalation Point: Ready for Vertex AI if needed later
        # self.vertex_client = genai.Client(vertexai=True, project="your-gcp-project-id", location="us-central1")

    def generate_text(self, model: VerifiedModel, prompt: str) -> str:
        # Route to Google API client (Anthropic omitted as it was not present in the capability cards)
        response = self.client.models.generate_content(
            model=model.value,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.7)
        )
        return response.text

    def generate_audio(self, model: VerifiedModel, text: str, voice_name: str = "Puck") -> bytes:
        # Enforce explicit speech directive workaround for Google native TTS
        response = self.client.models.generate_content(
            model=model.value,
            contents=text,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=voice_name
                        )
                    )
                )
            )
        )
        assert response.candidates
        assert response.candidates[0].content
        assert response.candidates[0].content.parts
        return cast(bytes, response.candidates[0].content.parts[0].inline_data.data)

    def generate_image(self, model: VerifiedModel, prompt: str) -> bytes:
        # Image generation requires the v1beta client
        result = self.client_beta.models.generate_images(
            model=model.value,
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                output_mime_type="image/jpeg",
                aspect_ratio="16:9"
            )
        )
        assert result.generated_images
        assert result.generated_images[0].image
        return cast(bytes, result.generated_images[0].image.image_bytes)

    def generate_with_tools(
        self,
        model: VerifiedModel,
        prompt: str,
        tier: str = "fast",
        tools: Optional[Sequence[Any]] = None,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
    ) -> Any:
        """Cognitive Router entry-point: dispatch a prompt with Function Calling tools.

        Automatically selects the correct tool subset from ``tool_registry`` based
        on ``tier``, or accepts an explicit ``tools`` list for fine-grained control.
        The model receives the tools as Gemini Function Declarations so it can
        autonomously decide which to invoke.

        Args:
            model: A ``VerifiedModel`` enum value. Use Pro-class for ``tier="heavy"``,
                Flash-class for ``tier="fast"``.
            prompt: The user prompt to send to the model.
            tier: Tool-routing tier. Accepted values: ``"heavy"``, ``"fast"``.
                Ignored if ``tools`` is provided explicitly.
            tools: Optional explicit list of callables to expose to the model.
                Overrides ``tier``-based selection when provided.
            system_instruction: Optional system instruction string.  If ``None``,
                no system instruction is set.
            temperature: Sampling temperature (0.0-2.0).

        Returns:
            The raw ``GenerateContentResponse`` from the Gemini API.  Callers
            should inspect ``.text`` for plain-text responses or
            ``.candidates[0].content.parts`` for tool-call parts.

        Raises:
            ValueError: If ``MACCRE_PRIMARY_API_KEY`` is not set in the environment.
        """
        from maccre_core.tools.tool_registry import get_tools_for_tier

        active_tools = tools if tools is not None else get_tools_for_tier(tier)

        cfg = types.GenerateContentConfig(
            temperature=temperature,
            tools=active_tools if active_tools else None,
            system_instruction=system_instruction,
        )

        return self.client.models.generate_content(
            model=model.value,
            contents=prompt,
            config=cfg,
        )