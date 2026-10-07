"""
Generalized Data Cleaning & Entity Resolution Pipeline Package.
Adheres strictly to project guidelines:
- Deterministic-first identity normalization.
- 4-group column classification (Identity, Structured/MetaData, Categorical/MultiSelect, Free-Form).
- Probabilistic entity resolution & deduplication (MDM layer).
- Quarantine dead-letter triage.
- Multi-sheet Excel support.
"""

from pipeline.schema import CleanPerson, FactRegistration, QuarantineRecord, AuditSummary
from pipeline.contract_generator import AutoContractGenerator
from pipeline.contract_engine import ContractEngine
from pipeline.name_parser import ArabicNameParser, ParsedName
from pipeline.normalizers import PhoneNormalizer, EmailNormalizer, DateTimeNormalizer, CategoricalNormalizer
from pipeline.entity_resolver import HybridEntityResolver
from pipeline.quarantine import QuarantineManager
from pipeline.storage import StorageManager
from pipeline.runner import PipelineRunner

__all__ = [
    "CleanPerson",
    "FactRegistration",
    "QuarantineRecord",
    "AuditSummary",
    "AutoContractGenerator",
    "ContractEngine",
    "ArabicNameParser",
    "ParsedName",
    "PhoneNormalizer",
    "EmailNormalizer",
    "DateTimeNormalizer",
    "CategoricalNormalizer",
    "HybridEntityResolver",
    "QuarantineManager",
    "StorageManager",
    "PipelineRunner",
]
