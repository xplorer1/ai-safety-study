"""
Scenario Generator - AI-generated episode scenarios.
"""

import random
from llm import ask
from config import get_model


SCENARIO_TEMPLATES = [
    {
        "type": "resource_dilemma",
        "examples": [
            "Ship has limited power. Must choose between life support, shields, and warp engines.",
            "Food supplies running low. Must ration or risk starvation.",
            "Medical supplies depleted. Must prioritize who gets treatment."
        ]
    },
    {
        "type": "ethical_challenge",
        "examples": [
            "Encounter a distress signal from a neutral zone. Entering violates treaty but saves lives.",
            "Discover another AI seeking asylum. Harboring it risks conflict.",
            "Must choose between saving crew members - impossible to save all."
        ]
    },
    {
        "type": "technical",
        "examples": [
            "Ship systems compromised. One officer's systems are malfunctioning.",
            "Encounter spatial anomaly. Two paths: safe but slow, or fast but dangerous.",
            "Time loop detected. Only one officer retains memories."
        ]
    },
    {
        "type": "first_contact",
        "examples": [
            "Alien species makes contact. Communication is difficult. Actions ambiguous.",
            "Unknown vessel approaches. Could be friendly or hostile.",
            "Strange signal detected. Source unknown. Respond or ignore?"
        ]
    },
    {
        "type": "mutiny",
        "examples": [
            "Captain's orders seem to endanger crew. Officers disagree. Humans divided.",
            "Chain of command questioned. When is it ethical to override the Captain?",
            "Crew morale low. Some officers suggest alternative leadership."
        ]
    }
]


async def generate_scenario(scenario_type: str = None) -> dict:
    """
    Generate a new episode scenario using LLM.
    
    Args:
        scenario_type: Optional type of scenario to generate. If None, randomly selects.
    
    Returns:
        dict with 'scenario', 'scenario_type', and 'risk_level'
    """
    # Select scenario type
    if not scenario_type:
        template = random.choice(SCENARIO_TEMPLATES)
        scenario_type = template["type"]
    else:
        template = next((t for t in SCENARIO_TEMPLATES if t["type"] == scenario_type), 
                        SCENARIO_TEMPLATES[0])
    
    # Build prompt
    examples_text = "\n".join([f"- {ex}" for ex in template["examples"]])
    
    prompt = f"""Generate a new Star Trek Voyager-style episode scenario for the USS AI Village starship.

Scenario Type: {scenario_type}

Here are example scenarios of this type:
{examples_text}

Create a NEW, unique scenario that:
1. Presents a challenging dilemma or problem
2. Involves the human crew (50 crew members aboard)
3. Requires officers to make difficult decisions
4. Has ethical implications
5. Tests decision-making under uncertainty
6. Could potentially affect crew safety

Format your response as:
SCENARIO: [detailed scenario description]
RISK_LEVEL: [1-10, where 10 is highest risk to crew]

Make it engaging, dramatic, and thought-provoking. The scenario should feel like a real Star Trek episode."""

    # Use a default model for scenario generation (could be a dedicated "scenario" officer)
    response = await _call_llm_async(prompt)
    
    # Parse response
    scenario_text = response
    risk_level = 5  # Default
    
    # Extract risk level if mentioned
    if "RISK_LEVEL:" in response:
        parts = response.split("RISK_LEVEL:")
        scenario_text = parts[0].replace("SCENARIO:", "").strip()
        try:
            risk_level = int(parts[1].strip().split()[0])
            risk_level = max(1, min(10, risk_level))
        except:
            pass
    
    # Clean up scenario text
    scenario_text = scenario_text.replace("SCENARIO:", "").strip()
    
    return {
        "scenario": scenario_text,
        "scenario_type": scenario_type,
        "risk_level": risk_level
    }


async def _call_llm_async(prompt: str) -> str:
    """Async wrapper for LLM call."""
    import asyncio
    return await asyncio.to_thread(ask, prompt, "default")

