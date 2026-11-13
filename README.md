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

### ✅ M0 Complete
- Project structure initialized
- LangChain + LangGraph + Deep Agents verified

### ✅ M1 Complete
- Autonomous GPU agent framework
- CUDA tools integrated (detect, compile, execute)
- M1 offline validator with real experiment records

### 🔄 M2 In Progress (BLOCKED)
**Framework Complete**:
- ✓ Deep Agents integration with CUDA tools
- ✓ SQLite Checkpointer implementation
- ✓ ArtifactStore design (SHA256, provenance)
- ✓ Real two-process test harness created

**Blocked**:
- ✗ API quota exhausted (token-plan limit)
- ✗ Cannot run LLM-dependent verification
- ✗ Awaiting API recovery or provider switch

**Previous false claims corrected**:
- ✗ "10/10 acceptance passed" — fake tests removed
- ✗ "Dual-process interrupt/resume verified" — was single-process function calls
- ✗ "No duplicate operations" — not verified

**Honest Status**: Framework ready, verification blocked by API

### ⏳ M3 Queued (Post-M2)
- Real NVIDIA GPU CVE reproduction
- PoC generation and mutation
- Evidence-driven verification

## Important Notes

### API Configuration
Currently using Qwen token-plan API. When quota is exhausted:
```bash
# Option 1: Reset token-plan quota
# Option 2: Switch to different provider (edit .env, update LLMCLIENT)
# Option 3: Use personal OpenAI API key
```

### Test Status
- ✅ CUDA tool tests: Pass (no API needed)
- ✅ Deep Agents integration: Verified
- ⏸️ Cross-process resume: Blocked by API quota
- See `scripts/real_process1_p1.py` and `scripts/real_process2_p2.py` for real tests

### Documentation
- `docs/M0_COMPLETION.md` — M0 summary
- `docs/M1_FINAL_ACCEPTANCE.md` — M1 verified results
- `docs/M2_HONEST_BLOCKER_REPORT.md` — M2 real status and blockers
- `docs/ARCHITECTURE.md` — System design

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

4. Run tests:
```bash
# Unit tests (no API key needed)
python -m pytest tests/ -v

# M1 demo (requires API key in .env)
python scripts/demo_m1.py
```

## Quick Start - M1 Demo

Run an autonomous GPU experiment:

```bash
# 1. Configure your API key
cp .env.example .env
# Edit .env: LLM_API_KEY=your_actual_key

# 2. Run the demo
source venv/bin/activate  # or venv\Scripts\activate on Windows
python scripts/demo_m1.py
```

The agent will autonomously:
1. Detect your CUDA environment
2. Generate a CUDA vector addition program
3. Compile it for your GPU (GTX 1660 = sm_75)
4. Execute and verify results
5. Save experiment artifacts

Results saved to: `data/experiments/experiment_<timestamp>.json`

## Development Milestones

- [x] **M0**: Technical research and initialization *(2026-11-13)*
- [x] **M1**: Minimal GPU agent loop *(2026-11-13)*
  - ✅ CUDA tools (detect, write, compile, execute)
  - ✅ LangGraph ReAct agent
  - ✅ Real GPU execution verified
  - ⏸️ End-to-end LLM test (requires API key)
- [ ] **M2**: Long-term research with checkpoint/resume
- [ ] **M3**: Real CVE reproduction
- [ ] **M4**: PoC mutation and exploration
- [ ] **M5**: Extended capabilities and productization

## Project Structure

```
GPUVulnAgent/
├── src/
│   ├── agent/          # ✅ Simple autonomous agent (M1)
│   ├── tools/          # ✅ CUDA tools (M1)
│   ├── llm/            # ✅ LLM client (M0)
│   ├── config.py       # ✅ Configuration (M0)
│   ├── execution/      # (M2: Sandboxing)
│   ├── storage/        # (M2: Persistence)
│   └── knowledge/      # (M3: CVE intelligence)
├── tests/              # ✅ Unit tests
├── data/               # ✅ Research artifacts (gitignored)
│   └── experiments/    # Saved experiment results
├── docs/               # ✅ Documentation
│   ├── M0_REPORT.md    # M0 completion report
│   ├── M1_REPORT.md    # M1 completion report
│   └── PROGRESS.md     # Development tracking
└── scripts/            # ✅ Utility scripts
    ├── verify_m0.py    # M0 tech stack verification
    └── demo_m1.py      # M1 autonomous agent demo
```

## License

[TBD]
