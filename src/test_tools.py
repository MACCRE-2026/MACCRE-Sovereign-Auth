from google import genai
from google.genai import types
from maccre_core.tools.tool_registry import TOOL_DISPATCHER
from maccre_core.orchestration.windows_vault import get_native_credential
import json
import sys

def run_transparent_audit() -> None:
    api_key = get_native_credential("MACCRE_Sovereign")
    if not api_key:
        raise ValueError("CRITICAL: AI Studio API Key not found in Windows Vault.")

    client = genai.Client(api_key=api_key)

    print(f"--- INITIATING TRANSPARENT TOOL AUDIT ({len(TOOL_DISPATCHER)} TOOLS) ---")

    for tool_name, tool_func in TOOL_DISPATCHER.items():
        print(f"\n[AUDIT] Testing Tool: {tool_name}")

        config = types.GenerateContentConfig(
            tools=[tool_func],
            temperature=0.0,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            tool_config=types.ToolConfig(
                function_calling_config=types.FunctionCallingConfig(
                    mode="ANY",
                    allowed_function_names=[tool_func.__name__]
                )
            )
        )

        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=f"Execute the {tool_name} tool with placeholder testing data.",
                config=config
            )

            candidate = response.candidates[0]
            if not candidate.content or not candidate.content.parts:
                print(f"[FAIL] API RETURNED EMPTY CONTENT. Finish Reason: {candidate.finish_reason}")
                raise ValueError(f"Empty content payload for tool: {tool_name}")

            call = candidate.content.parts[0].function_call
            if call is None:
                raise RuntimeError(f"SCHEMA REFLECTION FAILED for {tool_name}: No function_call returned.")
            print(f"[SUCCESS] SCHEMA REFLECTION: {call.name}")
            print(f"  RAW ARGS: {json.dumps(dict(call.args), indent=2)}")

        except Exception as e:
            print(f"[CRITICAL FAILURE ON TOOL: {tool_name}]")
            raise e

if __name__ == "__main__":
    run_transparent_audit()
