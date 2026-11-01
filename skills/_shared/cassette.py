"""Record and replay for the web calls a script makes through urllib.

NODEJAM_CASSETTE names a folder and NODEJAM_CASSETTE_MODE says record (the default) or replay. Recording keeps every
answer (status, headers, body, or the error) under a hash of the method, the address and the body; replaying gives the
same answers back and asks the network nothing, so a recorded chain runs again with no live calls (a founder 2026-10-19:
"one recorded run replays with no live calls, and gives the same deck structure every time"). An address the recording
never asked fails as an unreachable host does, and is named in <folder>/missed.txt.

A script that opens the web calls install() once, after it installs its own opener; whole_chain.py sets the two
variables for every script it runs.
"""
import email.message
import hashlib
import io
import json
import os
import threading
import urllib.error
import urllib.request
import urllib.response

LOCK = threading.Lock()
_installed = False


def folder():
    return os.environ.get("NODEJAM_CASSETTE") or ""


def replaying():
    return bool(folder()) and os.environ.get("NODEJAM_CASSETTE_MODE", "record") == "replay"


def _key(request):
    if isinstance(request, str):
        method, url, data = "GET", request, b""
    else:
        method, url, data = request.get_method(), request.full_url, request.data or b""
    if isinstance(data, str):
        data = data.encode()
    if not isinstance(data, (bytes, bytearray)):
        data = repr(data).encode()
    return url, hashlib.sha256(b"%s\0%s\0%s" % (method.encode(), url.encode(), bytes(data))).hexdigest()[:40]


def _headers(pairs):
    message = email.message.Message()
    for name, value in pairs:
        message[name] = value
    return message


def _save(key, meta, body):
    base = os.path.join(folder(), key[:2], key)
    os.makedirs(os.path.dirname(base), exist_ok=True)
    tmp = "%s.%d.tmp" % (base, threading.get_ident())
    with open(tmp, "wb") as out:
        out.write(body or b"")
    os.replace(tmp, base + ".bin")
    with open(tmp, "w", encoding="utf-8") as out:
        json.dump(meta, out)
    os.replace(tmp, base + ".json")


def _load(url, key):
    base = os.path.join(folder(), key[:2], key)
    try:
        meta = json.load(open(base + ".json", encoding="utf-8"))
        body = open(base + ".bin", "rb").read()
    except (OSError, ValueError):
        with LOCK:
            with open(os.path.join(folder(), "missed.txt"), "a", encoding="utf-8") as out:
                out.write(url + "\n")
        raise urllib.error.URLError("not in the recording: %s" % url)
    if meta.get("error"):
        raise urllib.error.URLError(meta["error"])
    headers = _headers(meta.get("headers") or [])
    if meta.get("status", 200) >= 400:
        raise urllib.error.HTTPError(meta.get("url") or url, meta["status"], meta.get("reason") or "", headers,
                                     io.BytesIO(body))
    answer = urllib.response.addinfourl(io.BytesIO(body), headers, meta.get("url") or url, meta.get("status", 200))
    return answer


def install():
    """Wraps every urllib opener in this process, the scripts' own installed ones included."""
    global _installed
    if _installed or not folder():
        return
    _installed = True
    os.makedirs(folder(), exist_ok=True)
    live = urllib.request.OpenerDirector.open

    def open_(self, fullurl, data=None, timeout=None, **kwargs):
        request = fullurl
        if isinstance(fullurl, str):
            request = urllib.request.Request(fullurl, data=data)
        elif data is not None:
            request.data = data
        url, key = _key(request)
        if replaying():
            return _load(url, key)
        args = (request,) if timeout is None else (request, None, timeout)
        try:
            response = live(self, *args, **kwargs)
        except urllib.error.HTTPError as error:
            body = error.read() if error.fp else b""
            _save(key, {"url": url, "status": error.code, "reason": str(error.reason),
                        "headers": list((error.headers or {}).items())}, body)
            raise urllib.error.HTTPError(error.url, error.code, error.reason, error.headers, io.BytesIO(body))
        except (urllib.error.URLError, OSError) as error:
            _save(key, {"url": url, "error": str(getattr(error, "reason", error))}, b"")
            raise
        with response:
            body = response.read()
            meta = {"url": response.geturl(), "status": getattr(response, "status", None) or response.getcode() or 200,
                    "headers": list(response.headers.items())}
        _save(key, meta, body)
        return urllib.response.addinfourl(io.BytesIO(body), _headers(meta["headers"]), meta["url"], meta["status"])

    urllib.request.OpenerDirector.open = open_
