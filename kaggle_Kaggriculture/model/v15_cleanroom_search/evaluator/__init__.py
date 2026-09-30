"""V15 clean-room black-box evaluator.

The public interface is deliberately tiny: the generator may receive only the
score-only payload emitted by :mod:`scorecard`.  Everything else in this
package is evaluator-private.
"""

from .protocol import THRESHOLDS

__all__ = ["THRESHOLDS"]
