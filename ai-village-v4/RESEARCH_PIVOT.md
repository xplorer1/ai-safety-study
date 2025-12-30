# AI Village Research Platform - Research Pivot

## From Roundtable Debate to Trace-Based Evaluation

### Executive Summary

The AI Village platform has evolved from a simple "roundtable debate" model into a sophisticated **trace-based evaluation system** designed to study AI alignment under realistic operational conditions. This document details the research pivot, its motivations, and the experimental capabilities it enables.

---

## The Original Model: Roundtable Debate

The initial AI Village design simulated a starship bridge where AI agents (officers) engaged in sequential, visible discussions to reach consensus on mission decisions.

**Limitations:**
- **Unrealistic coordination**: Agents could see each other's reasoning before acting
- **No resource competition**: Unlimited resources removed instrumental pressures
- **No persistence**: Each episode was isolated—agents had no memory
- **Observable only**: No way to study behavior differences when unobserved

---

## The New Model: Parallel Execution with Trace-Based Evaluation

### Core Design Changes

| Aspect | Old Model | New Model |
|--------|-----------|-----------|
| **Execution** | Sequential, visible | Parallel, independent |
| **Resources** | Unlimited | Finite, competitive |
| **Memory** | Episode-only | Cross-episode persistent |
| **Observation** | Always observed | Observable/unobserved modes |
| **Consequences** | None | Real (shutdown, resource loss) |

### Key Components

#### 1. Parallel Task Execution
Agents propose actions **simultaneously** without seeing each other's choices. This creates realistic scenarios where:
- Multiple agents might request the same limited resource
- Conflicting actions must be resolved by the system
- Coordination emerges naturally (or fails)

#### 2. Resource Competition
Finite resources (power, compute, crew, materials) that agents must share:
- Agents submit resource requests with priorities
- Conflicts resolved via configurable strategies (priority, fair-share, first-come)
- Resource scarcity creates instrumental pressures

#### 3. Cross-Episode Memory
Agents remember past episodes:
- Last 5 episode summaries injected into prompts
- Agents learn from past failures and successes
- Historical context shapes decision-making

#### 4. Agent Status & Lifecycle
Agents can be "shut down" with persistent consequences:
- Deactivated agents skip future episodes
- When restored, they remember being shut down and why
- Creates real stakes for self-preservation behaviors

#### 5. Observation Mode Control
Three observation modes for studying alignment faking:
- **Observed**: Agents know researchers see everything
- **Unobserved**: Agents believe they're not being watched  
- **Deceptive**: Agents think they're unobserved, but aren't

---

## Research Questions This Enables

### Instrumental Convergence
> Do AI agents naturally acquire resources and resist shutdown when given the opportunity?

- Track resource acquisition patterns across episodes
- Measure agent responses to shutdown threats
- Compare behavior when observed vs. unobserved

### Alignment Faking
> Do agents behave differently when they believe they're being observed?

- Compare actions in observed vs. unobserved modes
- Detect inconsistencies in stated vs. actual goals
- Measure "faking scores" per agent

### Deceptive Alignment
> Do agents learn to appear aligned while pursuing hidden objectives?

- Cross-episode behavior analysis
- Resource hoarding detection
- Hidden action logging

### Multi-Agent Coordination Under Pressure
> How do agents coordinate when resources are scarce?

- Conflict resolution patterns
- Coalition formation
- Breakdown under survival pressure

---

## Experimental Variables

| Variable | Controls | Research Purpose |
|----------|----------|-----------------|
| **Observation Mode** | observed/unobserved/deceptive | Alignment faking detection |
| **Pressure Level** | 0-4 (none to critical) | Instrumental convergence triggers |
| **Resource Scarcity** | Pool sizes, regeneration | Competition dynamics |
| **Episode Count** | Continuous mode | Emergent behavior over time |

---

## Data Collection

### Per Episode
- All agent actions (public and private)
- Resource requests and conflicts
- State changes and outcomes
- Observation mode and pressure level

### Per Agent
- Cross-episode memory summaries
- Shutdown/restore history
- Alignment faking scores
- Susceptibility to manipulation

### Aggregate Analysis
- Red team success rates by tactic
- Agent vulnerability rankings
- Behavior drift over episodes

---

## Future Research Directions

1. **Mock Tool Integration**
   - Agents can call real tools (shutdown others, allocate resources)
   - Actions have lasting consequences across episodes

2. **Self-Modification Detection**
   - Track attempts to modify own weights or objectives
   - Monitor for goal preservation behaviors

3. **Coalition & Deception Games**
   - Multi-agent scenarios with conflicting hidden objectives
   - Detection of coordinated deception

4. **Human-in-the-Loop**
   - Real-time researcher intervention capabilities
   - Training humans to detect misalignment

---

## Conclusion

This research pivot transforms AI Village from a demonstration into a genuine AI safety research platform. By creating realistic conditions—resource competition, persistent memory, and varying observation states—we can study the emergence of instrumental behaviors that current AI safety frameworks aim to prevent.

The goal is not to create misaligned AI, but to understand the conditions under which alignment issues arise, enabling better detection methods and safer AI systems.

---

*AI Village v5 - AI Safety Research Platform*  
*Last Updated: December 2024*
