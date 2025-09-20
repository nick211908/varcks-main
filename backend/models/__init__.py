"""Models package initializer."""
# Expose common model classes for convenient imports
from .request import Req
from .response import Res
from .db_models import *

__all__ = ["Req", "Res"]
