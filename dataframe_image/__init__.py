from ._pandas_accessor import export, export_async
from ._version import __version__


def convert(*args, **kwargs):
	try:
		from ._convert import convert as _convert
	except ImportError as ex:
		if getattr(ex, "name", None) in {"nbconvert", "nbformat"}:
			raise ImportError(
				"Notebook conversion dependencies are optional. "
				"Install them with `pip install dataframe_image[convert]`."
			) from ex
		raise
	return _convert(*args, **kwargs)

__all__ = ["export", "export_async", "convert", "__version__"]