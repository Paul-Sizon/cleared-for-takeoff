"""Check registry. Each module in this package registers checks with @check."""
from __future__ import annotations

import importlib
import pkgutil
from dataclasses import dataclass
from typing import Callable

from ..finding import Finding


@dataclass
class CheckSpec:
    id: str
    title: str
    area: str          # report checklist grouping
    fn: Callable
    bundle: bool       # also runs against built products (.app/.ipa/.xcarchive)
    source: bool       # runs against source trees


REGISTRY: dict = {}


def check(id: str, title: str, area: str, bundle: bool = False, source: bool = True):
    def deco(fn):
        REGISTRY[id] = CheckSpec(id, title, area, fn, bundle, source)
        return fn
    return deco


def make(check_id: str):
    """Return a Finding factory bound to a check id."""
    def f(rule, title, severity, confidence, guideline, evidence, fix, **kw) -> Finding:
        return Finding(check=check_id, rule=f"{check_id}/{rule}", title=title, severity=severity,
                       confidence=confidence, guideline=guideline, evidence=evidence, fix=fix, **kw)
    return f


def load_all() -> dict:
    for mod in pkgutil.iter_modules(__path__):
        importlib.import_module(f"{__name__}.{mod.name}")
    return REGISTRY
