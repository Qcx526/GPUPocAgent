# GPUVulnAgent

An autonomous GPU vulnerability research expert agent powered by LLM and mature agent frameworks.

## Project Goal

Build an AI agent capable of:
- **CVE Reproduction**: Automatically reproduce known NVIDIA GPU vulnerabilities
- **PoC Generation**: Generate and mutate proof-of-concept exploits
- **Vulnerability Discovery**: Explore new security issues through intelligent mutation
- **Evidence-driven Verification**: Maintain scientific rigor in vulnerability confirmation

## Architecture

- **Agent Framework**: LangChain + LangGraph + Deep Agents
- **LLM**: DeepSeek v4.1 (via Qwen API Gateway)
- **Target Platform**: NVIDIA GPU ecosystem (CUDA, drivers, tools)

## Current Status

🚧 **M0 Phase**: Technical research and project initialization

## Setup

1. Create Python virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure API keys:
```bash
cp .env.example .env
# Edit .env with your actual API key
```

4. Run initial tests:
```bash
python -m pytest tests/
```

## Development Milestones

- [x] M0: Technical research and initialization
- [ ] M1: Minimal GPU agent loop
- [ ] M2: Long-term research with checkpoint/resume
- [ ] M3: Real CVE reproduction
- [ ] M4: PoC mutation and exploration
- [ ] M5: Extended capabilities and productization

## Project Structure

```
GPUVulnAgent/
├── src/
│   ├── agent/          # Agent core logic
│   ├── tools/          # GPU research tools
│   ├── execution/      # Sandbox and execution
│   ├── storage/        # Persistence layer
│   └── knowledge/      # Domain knowledge
├── tests/              # Test suite
├── data/               # Research artifacts
├── docs/               # Documentation
└── scripts/            # Utility scripts
```

## License

[TBD]
