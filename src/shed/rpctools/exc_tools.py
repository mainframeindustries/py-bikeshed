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
        # If we provide a single argument which isn't somethign simple, then it doesn't
        # get formatted with the excetpion.  So, provide two
        result = cls(tbe, list(tbe.format()))
        return result

    @classmethod
    def FromStrings(cls, strings):
        # If we provide a single argument which isn't somethign simple, then it doesn't
        # get formatted with the excetpion.  So, provide two
        result = cls(list(strings))
        return result


# Methods to serialize / deserialize tracebackexceptions


def traceback_exception_serialize(te: traceback.TracebackException) -> dict:
    result = {
        "type": "TracebackException:1.0",
        "__cause__": traceback_exception_serialize(te.__cause__) if te.__cause__ else None,
        "__context__": traceback_exception_serialize(te.__context__) if te.__context__ else None,
        "__suppress_context__": te.__suppress_context__,
        "stack": stack_summary_serialize(te.stack),
        "exc_type": exc_type_serialize(te.exc_type),
    }
    for name in ["filename", "lineno", "text", "offset", "msg"]:
        result[name] = getattr(te, name, None)
    return result


def traceback_exception_deserialize(te: dict) -> traceback.TracebackException:
    # construct a dummy TracebackException
    try:
        raise RuntimeError()
    except RuntimeError as e:
        result = traceback.TracebackException.from_exception(e)
    tbtype = te.get("type", "TracebackException:1.0")
    assert tbtype in ["TracebackException:1.0"]
    result.__cause__ = traceback_exception_deserialize(te["__cause__"]) if te["__cause__"] else None
    result.__context__ = traceback_exception_deserialize(te["__context__"]) if te["__context__"] else None
    result.stack = stack_summary_deserialize(te["stack"])
    result.exc_type = exc_type_deserialize(te["exc_type"])

    for name in ["__suppress_context__", "filename", "lineno", "text", "offset", "msg"]:
        setattr(result, name, te[name])
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
        return exc_type["repr"]


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
