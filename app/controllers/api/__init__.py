import pathlib
import importlib
this = pathlib.Path('.')
__all__ = []
for x in this.glob('api_v*.py'):
    __all__.append(x.stem)
    globals()[x.stem] = importlib.import_module(x.stem)