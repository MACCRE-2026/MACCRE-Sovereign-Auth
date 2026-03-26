# MACCREv2: Sovereign AI Architecture & Zero-Dependency Credentials

**Author:** Frank (Solo Developer) & The Alphabet Oracle  
**Date:** March 25, 2026  
**Status:** Request for Collaboration / Early Release  

### I. Abstract & The Catalyst
I am an indie developer. For the last several months, I've been quietly building a modular, local-first AI orchestration framework called MACCREv2. My primary design constraint was simple, bordering on paranoid: **I didn't want to trust third-party package wrappers with my API keys or my local filesystem.**

Over the last 48 hours, the `litellm` PyPI supply chain attack unfolded. Threat actors used `.pth` execution hooks to scrape plaintext `.env` files from local developer environments globally, stealing AI API keys and cloud credentials the moment a virtual environment was activated.

I am releasing the core architectural patterns of MACCREv2 today because the credential management system I built to satisfy my own paranoia is natively immune to the exact vector used in this attack. I am putting this out humbly to ask for critique, collaboration, and help from the community to harden the foundation for indie hackers relying on plaintext `.env` files.

*(Note: This is a "Bring Your Own Infrastructure" framework. You must generate your own Desktop OAuth `credentials.json` in GCP. There is no central server).*

### II. Core Pillar 1: Ephemeral Workspace Identity (OAuth 2.0)
For cloud routing, we deprecate `.env` entirely. Instead of passing an API key to the Google `genai` SDK, we bind the reasoning engine to Google Workspace using Desktop OAuth 2.0.
*   **The Mechanism:** The system generates a `token.json` payload restricted strictly to `cloud-platform` (Vertex AI), `generative-language`, `drive`, and `sheets` scopes.
*   **The Advantage:** If a `.pth` malware script scrapes the directory, it finds an access token that expires in 60 minutes, rather than a static API key with infinite liability.

### III. Core Pillar 2: The Zero-Dependency OS Vault
For endpoints that strictly require an API key (like Anthropic or specific Google endpoints), we use a 100% native OS integration.
1. **User-Driven Ingestion:** The developer manually inputs the API key directly into the native Windows Credential Manager GUI. Python never writes the key.
2. **The `ctypes` Bridge:** We use the Python Standard Library (`ctypes`) to directly interface with the Windows Kernel (`advapi32.dll`), completely air-gapping the auth layer from `pip`.

*(See `src/windows_vault.py` for the implementation).*

### IV. The Adversarial Audit (Defending the Edge)
During drafting, I ran these blueprints through an adversarial Red-Team AI audit. The automated auditor suggested abandoning the local Python orchestrator entirely and moving the Control Plane to **Google Apps Script (GAS)** to achieve a "true" serverless environment.

**I rejected the optimization, and here is why.**
Moving orchestration to cloud-native sandboxes like Apps Script destroys local sovereignty. It introduces a 6-minute execution guillotine, blocks the invocation of local binaries (like FFmpeg), and severs the air-gap required to route sensitive reasoning to `localhost` models like Gemma.

### V. Threat Modeling & Acknowledged Limitations
I am not a cybersecurity professional. No architecture is mathematically invulnerable.
1. **Process Memory Scraping:** Python is not memory-safe. Keys retrieved via `ctypes` exist in plaintext within the `python.exe` heap during execution. Targeted Ring-3 memory-dumping malware can extract this, though doing so typically triggers standard EDR heuristics, unlike silent `.env` scraping.
2. **First-Party SDK Compromise:** This architecture strips out third-party routing wrappers. It places its trust boundary at the Python Standard Library and official first-party vendor SDKs.

### VI. Call to Action: Let's Build This Together
The era of plaintext `.env` files needs to end. 

**Currently, the Zero-Dependency Vault is implemented purely for Windows (`advapi32.dll`).** I am opening this up to the community to help write the pure `ctypes` macOS (Keychain) and Linux (Secret Service API) equivalents to complete the cross-platform sovereign triad.

I invite you to fork this, critique the threat model, and help build the adapters.
# MACCRE-Sovereign-Auth
