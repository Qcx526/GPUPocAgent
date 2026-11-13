# GPUVulnAgent Development Progress

## Project Overview
Autonomous GPU vulnerability research expert agent for NVIDIA GPU ecosystem.

**Target Platform**: NVIDIA GPU (CUDA, drivers, tools)  
**LLM Model**: DeepSeek v4.1 via Qwen API Gateway  
**Framework**: LangChain + LangGraph + (Deep Agents planned)

---

## Milestone Status

### ✅ M0: Technical Research & Project Initialization
**Completed**: 2026-11-13

**Deliverables**:
- [x] Project structure initialization
- [x] Python dependency management (requirements.txt)
- [x] Configuration system with .env support
- [x] LLM client wrapper for Qwen API gateway
- [x] Unit tests for core components
- [x] M0 verification script

**Key Components**:
- `src/config.py` - Settings and environment configuration
- `src/llm/client.py` - LangChain LLM client wrapper
- `scripts/verify_m0.py` - Technology stack verification
- `tests/` - Unit tests (7 passing, 2 manual)

**Technology Stack Verified**:
- ✓ Python 3.14.6
- ✓ LangChain 1.5.0 (tool calling, message handling)
- ✓ LangGraph 1.2.21 (StateGraph, checkpoints)
- ✓ LangChain-OpenAI 1.7.4 (Qwen API compatibility)
- ✓ Pydantic 2.14.3 (settings management)

**Testing Environment**:
- Windows 10
- NVIDIA GeForce GTX 1660 (Compute Capability 7.5)
- CUDA 13.3
- WSL2 available

**Notes**:
- All unit tests pass (mock-based, no API key required)
- Manual verification script requires .env configuration
- Deep Agents evaluation deferred to M1 (need to verify real-world fit)

---

### 🔄 M1: Minimal GPU Agent Loop (In Progress)
**Target**: Real CUDA experiment with agent autonomy

**Goals**:
1. Agent can autonomously:
   - Detect available CUDA environment
   - Generate simple CUDA test program
   - Compile with nvcc
   - Execute and verify results
   - Save artifacts with evidence
2. Validate execution in isolated environment (Docker/WSL2)
3. Implement basic tool infrastructure:
   - CUDA environment detection
   - File generation and compilation
   - Safe execution with timeout
   - Artifact persistence

**Architecture Decision Points**:
- [ ] Deep Agents vs custom LangGraph workflow
- [ ] Execution environment (Docker vs WSL2 vs native)
- [ ] Tool design (granular vs high-level)
- [ ] State persistence approach

**Success Criteria**:
- Agent completes full cycle without manual intervention
- Generated code compiles successfully
- Execution results are captured with evidence
- Artifacts persisted correctly (not in temp dirs)

---

### 📋 M2: Long-term Research with Checkpoint/Resume
**Status**: Planned

**Goals**:
- Persistent research task management
- Process restart and resume capability
- Context window management
- Artifact linkage across sessions

---

### 📋 M3: Real CVE Reproduction Loop
**Status**: Planned

**Goals**:
- Intelligence gathering (CVE, patches, PoCs)
- Vulnerability analysis and trigger hypothesis
- PoC generation from vulnerability understanding
- Iterative refinement based on execution feedback
- Evidence-based verification

---

### 📋 M4: PoC Mutation & Exploration
**Status**: Planned

**Goals**:
- Structure-aware PoC mutation
- Feedback-driven refinement
- Anomaly detection and deduplication
- New vulnerability candidate identification

---

### 📋 M5: Extended Capabilities
**Status**: Planned

**Goals**:
- Multi-component support (drivers, firmware, virtualization)
- Multi-agent collaboration (if beneficial)
- API and Web UI
- Evaluation framework

---

## Current Technical Decisions

### Configuration Management
- **Approach**: Pydantic Settings with .env
- **Rationale**: Type-safe, validation built-in, standard pattern

### LLM Integration
- **Approach**: LangChain ChatOpenAI with custom base_url
- **Rationale**: Qwen API is OpenAI-compatible; avoid custom provider implementation
- **Status**: Basic connectivity verified (mock tests passing)

### Testing Strategy
- **Unit Tests**: Mock-based, no API key required (pytest)
- **Integration Tests**: Manual scripts with real API (scripts/verify_*.py)
- **Real Experiments**: Milestone deliverables with GPU/CUDA validation

### Execution Safety
- **Planned**: Docker containers for isolation
- **Current**: Native execution (acceptable for M1 simple tests)
- **Consideration**: Timeout, resource limits, error handling

---

## Development Guidelines

### Git Workflow
- Commit at logical checkpoints (feature complete, tests passing)
- Clear commit messages with context
- Branch for experimental features if needed

### Code Quality
- Type hints for function signatures
- Docstrings for public APIs
- Unit tests for core logic
- Integration tests for end-to-end flows

### API Usage
- Model: `deepseek-v4.1-flash-1017` (default)
- API Key: From `.env` (never committed)
- Cost tracking: Manual monitoring (token counts in verbose mode)

---

## Next Steps

1. **Complete M1 Implementation**:
   - Design minimal agent loop architecture
   - Implement CUDA tools (detect, compile, execute)
   - Create simple test workflow
   - Verify end-to-end with real CUDA program

2. **Evaluate Deep Agents**:
   - Review official docs for current version
   - Test compatibility with our LLM setup
   - Decide: adopt vs custom LangGraph

3. **Document Architecture**:
   - Finalize agent structure (nodes, state, tools)
   - Document tool interface design
   - Plan persistence strategy

---

## Open Questions

1. **Deep Agents Integration**: Does it fit our use case? Official Python SDK docs?
2. **Execution Environment**: Docker overhead acceptable? WSL2 performance?
3. **Tool Granularity**: Fine-grained (nvcc, execute) vs coarse (compile_and_run)?
4. **State Management**: Full graph state vs task-specific persistence?

---

## Resources

- **LangChain Docs**: https://python.langchain.com/docs/
- **LangGraph Docs**: https://langchain-ai.github.io/langgraph/
- **Deep Agents**: [To be researched]
- **CUDA Toolkit**: Installed locally (version to be verified in M1)

---

**Last Updated**: 2026-11-13  
**Current Milestone**: M1  
**Status**: Active Development
