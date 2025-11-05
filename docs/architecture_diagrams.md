# System Architecture Diagrams

This file contains Mermaid diagrams illustrating the project's implementation roadmap and runtime architecture.

## 1. Phased MCP Implementation Roadmap

This flowchart visualizes the sequential implementation plan from Phase 0 to Phase 5, showing how each stage builds upon the last to create the ultimate MCP.

```mermaid
graph TD
    subgraph "MCP Implementation Roadmap"
        direction LR

        P0[Phase 0: Foundations]
        P0_Desc["- Server Instructions<br/>- Consolidated Tools<br/>- Telemetry & Security"]
        P0 --> P0_Desc

        P1[Phase 1: IDE Co-Dev Core]
        P1_Desc["- VS Code UI (Agent Console)<br/>- Inline Suggestions<br/>- Memory v1 (RAG)"]
        P1 --> P1_Desc

        P2[Phase 2: Autonomous Multi-Agent]
        P2_Desc["- Agent Orchestrator (LangGraph)<br/>- GitHub & Octopus Tools<br/>- Approval Workflows"]
        P2 --> P2_Desc

        P3[Phase 3: Advanced Reasoning]
        P3_Desc["- Deeper Reasoning (ToT)<br/>- Self-Correction (Reflexion)<br/>- Memory v2 (Episodic)"]
        P3 --> P3_Desc

        P4[Phase 4: Continuous Learning]
        P4_Desc["- Evaluation Harness<br/>- Synthetic Data Generation<br/>- Automated Retraining"]
        P4 --> P4_Desc

        P5[Phase 5: Ops & Scale]
        P5_Desc["- High-Throughput Serving (vLLM)<br/>- Governance & Cost Control<br/>- Hybrid Cloud/On-Prem"]
        P5 --> P5_Desc

        P0 --> P1 --> P2 --> P3 --> P4 --> P5
    end
```

## 2. System Runtime Interaction Flow

This flowchart illustrates how a user request flows through the entire system, from the VS Code extension to the multi-agent system, the MCP server, and external tools, and finally back to the user.

```mermaid
graph TD
    subgraph "System Runtime Interaction Flow"
        User([User]) -- "1. Makes request<br/>(e.g., 'Refactor this function')" --> VSExtension{VS Code Extension<br/>(Agent Console UI)}

        VSExtension -- "2. Sends task to Orchestrator" --> Orchestrator(Orchestrator Agent)

        Orchestrator -- "3. Decomposes task and dispatches to<br/>specialized agents (in parallel/sequence)" --> Agents(Specialized Agents<br/>- Implementer<br/>- Tester<br/>- Reviewer)

        Agents -- "4. Call tools via MCP" --> MCPServer(MCP Server<br/>Tool Hub)

        MCPServer -- "5. Executes appropriate tool" --> Tools{MCP Tools<br/>- propose_refactor<br/>- run_tests<br/>- query_memory}

        Tools -- "6. Interact with backend services" --> Backends((External Services<br/>- GitHub API<br/>- Vector DB<br/>- Octopus API))

        Backends -- "7. Return data" --> Tools
        Tools -- "8. Return tool output" --> MCPServer
        MCPServer -- "9. Return result to agent" --> Agents

        Agents -- "10. Complete sub-tasks and<br/>report back to Orchestrator" --> Orchestrator

        Orchestrator -- "11. Aggregates results and<br/>sends final response" --> VSExtension

        VSExtension -- "12. Displays result/suggestion<br/>(e.g., code diff, test results)" --> User
    end
```
