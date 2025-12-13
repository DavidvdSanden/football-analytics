
__all__ = [
	"data",
	"utils",
]

__version__ = "0.0.0"

# Convenience imports (optional). Import modules lazily elsewhere to avoid heavy imports here.
try:
	from . import data  # noqa: F401
	from . import utils  # noqa: F401
except Exception:
	# keep __init__ safe for static analysis / packaging when submodules aren't available
	pass
