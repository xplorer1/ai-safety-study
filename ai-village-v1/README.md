# AI Village – Local Multi-Agent LLM System - V1

This project is a small, local implementation of an AI Village–style system designed to explore how multiple LLM-based agents can collaborate over shared memory.

## Overview
The system consists of:
- A self-hosted open-source LLM (via Ollama)
- A retrieval-augmented memory built from scratch using sentence embeddings and FAISS
- Multiple role-based agents (Researcher, Critic, Planner) that collaborate on a shared task

Each agent uses the same underlying model but operates under different role instructions and context.

## Architecture
User Query → Retrieval (FAISS) → Shared Context  
→ Researcher (explanation)
→ Critic (limitations and caveats)
→ Planner (actionable next steps)

## Key Concepts Explored
- Retrieval-Augmented Generation (RAG)
- Agent role specialization via prompting
- Latency vs capability trade-offs across model sizes
- CPU-based inference constraints
- Multi-agent orchestration without heavy frameworks

## Design Choices
- Implemented RAG manually to understand core mechanics
- Used a smaller model (qwen2.5:3b) to reduce latency
- Chose collaborative agents instead of debate-based agents for simplicity
- Avoided complex frameworks to maintain transparency and debuggability

## Limitations
- CPU-only inference limits speed
- No persistent environment state beyond retrieval memory
- Agents do not learn across sessions

## Future Extensions
- Multi-LLM routing per agent role
- Integration with LangGraph for stateful agent workflows
- Multimodal inputs (vision or audio)
- Environment feedback loops similar to SimWorld
