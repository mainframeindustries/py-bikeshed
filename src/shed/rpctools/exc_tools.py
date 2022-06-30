import importlib
import traceback


class RemoteException(Exception):
    """
    The exception which is created out of the remote exception.  We cannot reconstruct the remote exception precisely
    because its type may not exist locally.
    Also, there is no way in python to customize exception formatting.
    """

    def __init__(self, *args):
        super().__init__(*args)
        self.exception = args[0]

    @classmethod
    def FromTracebackException(cls, tbe):
        # If we provide a single argument which isn't something simple, then it doesn't
        # get formatted with the exception.  So, provide two
        result = cls(tbe, list(tbe.format()))
        return result

    @classmethod
    def FromStrings(cls, strings):
        # If we provide a single argument which isn't something simple, then it doesn't
        # get formatted with the exception.  So, provide two
        result = cls(list(strings))
        return result


class FakeException(type):
    """
    Represent an exc_type of a TracebackException which isn't found here.
    TracebackException.format() expects `exc_type` to be a real type.
    """

    @classmethod
    def create(cls, module, name, reprstr):
        """
        Dynamically create a new exception type to be used.
        """
        fake = cls(name, (Exception,), {})
        fake.__module__ = module
        fake.repr = reprstr
        return fake


# Methods to serialize / deserialize tracebackexceptions

_traceback_exception_attrs = ["__suppress_context__", "_str"]
_traceback_exception_syntax_attrs = [
    "filename",
    "lineno",
    "end_lineno",
    "text",
    "offset",
    "end_offset",
    "msg",
]


def traceback_exception_serialize(te: traceback.TracebackException) -> dict:
    result = {
        "type": "TracebackException:1.0",
        "__cause__": traceback_exception_serialize(te.__cause__) if te.__cause__ else None,
        "__context__": traceback_exception_serialize(te.__context__) if te.__context__ else None,
        "stack": stack_summary_serialize(te.stack),
        "exc_type": exc_type_serialize(te.exc_type),
    }
    for name in _traceback_exception_attrs:
        result[name] = getattr(te, name)
    if issubclass(te.exc_type, SyntaxError):
        se = {}
        for name in _traceback_exception_syntax_attrs:
            se[name] = getattr(te, name, None)
        result["syntax_error"] = se
    else:
        result["syntax_error"] = None
    return result


def traceback_exception_deserialize(te: dict) -> traceback.TracebackException:
    tbtype = te.get("type", "TracebackException:1.0")
    assert tbtype in ["TracebackException:1.0"]

    # construct a dummy TracebackException and fill its atributes
    try:
        raise RuntimeError()
    except RuntimeError as e:
        result = traceback.TracebackException.from_exception(e)
    else:
        result = None  # to paciy linters
    result.__cause__ = traceback_exception_deserialize(te["__cause__"]) if te["__cause__"] else None
    result.__context__ = traceback_exception_deserialize(te["__context__"]) if te["__context__"] else None
    result.stack = stack_summary_deserialize(te["stack"])
    result.exc_type = exc_type_deserialize(te["exc_type"])
    for name in _traceback_exception_attrs:
        setattr(result, name, te[name])
    if te.get("syntax_error"):
        for name in _traceback_exception_syntax_attrs:
            value = te["syntax_error"].get(name)
            setattr(result, name, value)
    return result


def exc_type_serialize(exc_type: type) -> dict:
    return {
        "module": exc_type.__module__,
        "name": exc_type.__name__,
        "repr": repr(exc_type),
    }


def exc_type_deserialize(exc_type: dict):
    """
    returns either the type (if it exists locally) or a string
    """
    try:
        mod = importlib.import_module(exc_type["module"])
        return getattr(mod, exc_type["name"])
    except (ImportError, AttributeError):
        return FakeException.create(exc_type["module"], exc_type["name"], exc_type["repr"])


def stack_summary_serialize(stack_summary: traceback.StackSummary) -> list:
    return [frame_summary_serialize(frame_summary) for frame_summary in stack_summary]


def stack_summary_deserialize(stack_summary: list) -> traceback.StackSummary:
    lines = [frame_summary_deserialize(frame_summary) for frame_summary in stack_summary]
    return traceback.StackSummary.from_list(lines)


def frame_summary_serialize(frame_summary: traceback.FrameSummary) -> list:
    filename, lineno, name, line = tuple(frame_summary)
    return [filename, lineno, name, line, frame_summary.locals]


def frame_summary_deserialize(frame_summary: list) -> traceback.FrameSummary:
    filename, lineno, name, line, frame_locals = frame_summary
    fs = traceback.FrameSummary(filename, lineno, name, locals=frame_locals, line=line)
    return fs
