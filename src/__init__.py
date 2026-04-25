"""HW5 ECG / HRV analysis package.

Modules:
- config:   constants, session map, anchor keys, dispatch table
- pipeline: loaders, filters, QRS detection, HRV (scipy + NeuroKit2)
- plotting: shared matplotlib style + reusable publication plots

The submodules are not auto-imported here so that `from src import config`
still works during scaffolding (when pipeline.py may not yet exist).
"""
__all__ = ['config', 'pipeline', 'plotting']
