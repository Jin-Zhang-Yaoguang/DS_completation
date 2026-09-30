"""V117 独立经营专家注册表。"""

from .balanced import BalancedExpert, BalancedGenome
from .base import ContractExpert, ExpertQualification
from .scarcity import ScarcityVegetableExpert
from .yarn import YarnWoolExpert


def build_expert_registry(balanced_genome: BalancedGenome | dict | None = None) -> dict[str, ContractExpert]:
    experts: list[ContractExpert] = [BalancedExpert(balanced_genome), YarnWoolExpert(), ScarcityVegetableExpert()]
    return {expert.expert_id: expert for expert in experts}


__all__ = [
    "BalancedExpert", "BalancedGenome", "ContractExpert", "ExpertQualification", "ScarcityVegetableExpert",
    "YarnWoolExpert", "build_expert_registry",
]
