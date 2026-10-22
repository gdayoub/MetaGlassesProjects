# Inspected environment

2026-10-22, Windows 11 Home 10.0.26200. Resolved Desktop using `[Environment]::GetFolderPath('Desktop')`; actual permanent editable project is `C:\Users\george\Desktop\LensAgent`. No existing folder was overwritten. No applicable AGENTS.md was found in that project's ancestor directories.

| Area | Observed result |
|---|---|
| Python | Default 3.15.0;3.12.10 and3.14.7 also installed. Project uses3.12.10 in `.venv`. |
| Node |24.19.0 available; existing Codex bundled pnpm 11.25.0 used. No global Node replacement performed. |
| Git / GitHub | Git 2.55.0; GitHub CLI authenticated as gdayoub with repository access. New local repository; no remote created or code published. |
| Editor | VS Code `code.cmd` available; `LensAgent.code-workspace` supplied with virtual-environment interpreter setting. |
| Docker | Desktop shortcut and CLI present; engine not running. Project does not require it. |
| Ollama |0.40.6, initially no models. Installed official `gemma3:4b` tag 68ceab7e468a (~3.4GB) for live testing. |
| Hardware | Approximately 32GB RAM; NVIDIA RTX 5070 Laptop GPU with 8151MiB reported VRAM. Live inference used GPU. |
| macOS | Windows host; no configured SSH host or supported remote Mac was identified. No Xcode, iOS signing or native build claimed. |
| Credentials | No Gemini/Google/OpenAI/Anthropic inference credential variable found in the shell. Only variable names were inspected. Owner confirmed no Gemini key. No unrelated secret stores were searched. |
| Starter | Filename search in Desktop, Documents and Downloads found no `lensagent-messenger-starter` archive/project. This does not assert that no copy exists in other drives/cloud storage. |
| Collaboration | Three agents used concurrently for Meta/repository research, messaging/security, and backend/model research. Root handled web, integration, setup and live validation. |
| Network | Local app listening only at127.0.0.1:8765. Owner authorized a temporary HTTPS tunnel; automatic review rejected the download/start command before execution. |

Dependency locks are committed. Private `.env`, SQLite data, virtual environments, installed frontend packages, downloaded model files and test evidence under `work/` are not source-control content. Ollama owns its normal local model store outside the project. No paid infrastructure, external account, firewall change or machine-wide tool upgrade was created.
