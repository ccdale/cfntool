"""
errors module
"""
import sys


def formatErrorMsg(funcname, exc):
    return "Error in {}: Exception: {}: {}\n".format(funcname, type(exc).__name__, exc)


def errorExit(funcname, exc, errorvalue=1):
    sys.stderr.write(formatErrorMsg(funcname, exc))
    sys.exit(errorvalue)


def errorRaise(funcname, exc):
    sys.stderr.write(formatErrorMsg(funcname, exc))
    raise (exc)


def errorNotify(funcname, exc):
    sys.stderr.write(formatErrorMsg(funcname, exc))
