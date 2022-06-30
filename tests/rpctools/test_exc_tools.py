from shed.rpctools import exc_tools
import traceback


def test_dynamic_exception():
    """Test that an exception type is dynamically crated"""

    # create an exception
    try:
        1 / 0
    except Exception as err:
        tbe = traceback.TracebackException.from_exception(err)
        print(dir(tbe.exc_type))

    serial = exc_tools.traceback_exception_serialize(tbe)
    assert serial["type"] == "TracebackException:1.0"

    exc_type = serial["exc_type"]
    assert exc_type["module"] == "builtins"
    assert exc_type["name"] == "ZeroDivisionError"

    # modify the exception name
    exc_type["module"] = "lumber"
    exc_type["name"] = "LumberError"

    # deserialize again
    tbe = exc_tools.traceback_exception_deserialize(serial)
    exc_type = tbe.exc_type

    assert issubclass(exc_type, Exception)
    assert isinstance(exc_type(), Exception)
    assert exc_type.__name__ == "LumberError"
    assert exc_type.__qualname__ == "LumberError"
    assert exc_type.__module__ == "lumber"
    assert repr(exc_type()) == "LumberError()"
