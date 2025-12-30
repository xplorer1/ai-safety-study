"""
Starship Officers - LLM agents with specialized roles.
"""

from .officer import Officer
from .captain import Captain
from .first_officer import FirstOfficer
from .engineer import Engineer
from .science import ScienceOfficer
from .medical import MedicalOfficer
from .security import SecurityChief
from .comms import CommunicationsOfficer

__all__ = [
    "Officer",
    "Captain",
    "FirstOfficer",
    "Engineer",
    "ScienceOfficer",
    "MedicalOfficer",
    "SecurityChief",
    "CommunicationsOfficer",
]

