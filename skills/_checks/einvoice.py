"""Loader: the rule lives in the repo checks dir; this makes it runnable from a skill."""
import importlib.util as _ilu
import sys as _sys
from pathlib import Path as _Path

_repo = None
for _base in [_Path(__file__).resolve(), _Path.cwd().resolve()]:
    for _parent in _base.parents:
        if (_parent / "standards/checks/einvoice.py").is_file():
            _repo = _parent
            break
    if _repo:
        break
if _repo is None:
    raise SystemExit("pack check: cannot find standards/checks/einvoice.py")

_sys.path.insert(0, str(_repo / "standards/checks"))
_spec = _ilu.spec_from_file_location("_pack_einvoice", _repo / "standards/checks/einvoice.py")
_mod = _ilu.module_from_spec(_spec)
_sys.modules["_pack_einvoice"] = _mod
_spec.loader.exec_module(_mod)
check = _mod.check
main = getattr(_mod, "main", None)
globals().update({k: v for k, v in vars(_mod).items() if not k.startswith("__")})
