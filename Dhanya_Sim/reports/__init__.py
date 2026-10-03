"""Reports package for Fair Drop adversarial simulation.

Exports ReportGenerator and FrontendBridge.
"""

from .generator import ReportGenerator
from ..metrics.frontend_bridge import FrontendBridge

__all__ = ["ReportGenerator", "FrontendBridge"]
