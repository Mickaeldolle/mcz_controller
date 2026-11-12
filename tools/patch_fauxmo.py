"""Apply the prototype's input bounds to the pinned fauxmoESP dependency."""
import json
from pathlib import Path

Import("env")

library = Path(env.subst("$PROJECT_LIBDEPS_DIR")) / env.subst("$PIOENV") / "FauxmoESP"
if json.loads((library / "library.json").read_text(encoding="utf-8"))["version"] != "3.4.1":
    raise RuntimeError("Review the fauxmoESP safety patch for this version")

source = library / "src/fauxmoESP.cpp"
original = source.read_text(encoding="utf-8")
content = original


def replace(text, old, new, count=1):
    if text.count(new) == count:
        return text
    if text.count(old) != count:
        raise RuntimeError("Unexpected fauxmoESP source while applying input bounds")
    return text.replace(old, new)


content = replace(content, "unsigned char id = url.substring(pos+7).toInt();",
                  "int id = url.substring(pos+7).toInt();", 2)
content = replace(content, "response = _deviceJson(id-1);",
                  "if (id < 0 || size_t(id) > _devices.size()) return false;\n\t\tresponse = _deviceJson(id-1);")
content = replace(content, "if (id > 0) {", "if (id > 0 && size_t(id) <= _devices.size()) {")
content = replace(content, "FAUXMO_TCP_STATE_RESPONSE)+10", "FAUXMO_TCP_STATE_RESPONSE)+16")
content = replace(content, "fauxmoesp_device_t device;", "fauxmoesp_device_t device{};")
content = replace(content, '#include "fauxmoESP.h"', '''#include "fauxmoESP.h"
#if defined(MCZ_ALEXA_RADIO)
#include "mcz_alexa.h"
#endif''')
env.Append(CPPPATH=[env.subst("$PROJECT_INCLUDE_DIR")])

marker = "// MCZ: assemble bounded HTTP requests across TCP segments."
if marker not in content:
    start = content.index("bool fauxmoESP::_onTCPData(")
    end = content.index("void fauxmoESP::_onTCPClient(", start)
    content = content[:start] + f"""bool fauxmoESP::_onTCPData(AsyncClient *client, void *data, size_t len, String& request) {{
    {marker}
    constexpr size_t limit = 2048;
    if (!_enabled || len == 0 || len > limit - request.length()) return false;

    if (!request.concat(static_cast<const char *>(data), len)) return false;
    const int headersEnd = request.indexOf("\\r\\n\\r\\n");
    if (headersEnd < 0) return true;

    const int methodEnd = request.indexOf(' ');
    if (methodEnd <= 0) return false;
    const int urlEnd = request.indexOf(' ', methodEnd + 1);
    const int lineEnd = request.indexOf("\\r\\n");
    if (urlEnd <= methodEnd + 1 || lineEnd <= urlEnd) return false;

    size_t bodyLength = 0;
    bool hasLength = false;
    for (int start = lineEnd + 2; start < headersEnd;) {{
        const int end = request.indexOf("\\r\\n", start);
        const char* header = request.c_str() + start;
        if (end - start >= 18 && strncasecmp(header, "Transfer-Encoding:", 18) == 0)
            return false;
        if (end - start >= 15 && strncasecmp(header, "Content-Length:", 15) == 0) {{
            if (hasLength) return false;
            hasLength = true;
            String value = request.substring(start + 15, end);
            value.trim();
            if (value[0] < '0' || value[0] > '9') return false;
            char* tail;
            const unsigned long length = strtoul(value.c_str(), &tail, 10);
            if (*tail || length > limit) return false;
            bodyLength = length;
        }}
        start = end + 2;
    }}

    const size_t expectedSize = headersEnd + 4 + bodyLength;
    if (expectedSize > limit || request.length() > expectedSize) return false;
    if (request.length() < expectedSize) return true;

    const bool isGet = request.startsWith("GET ");
    const String url = request.substring(methodEnd + 1, urlEnd);
    const String body = request.substring(headersEnd + 4);
    request = "";
    return _onTCPRequest(client, isGet, url, body);
}}

""" + content[end:]

content = replace(content, "if (!_tcpClients[i] || !_tcpClients[i]->connected()) {",
                  "if (!_tcpClients[i]) {")
content = replace(content, "_onTCPData(c, data, len);",
                  "if (!_onTCPData(c, data, len, _tcpRequests[i])) c->close();")
content = replace(content, "delete c;\n\t                DEBUG_MSG_FAUXMO",
                  "_tcpRequests[i] = String();\n\t                delete c;\n\t                DEBUG_MSG_FAUXMO")
content = replace(content, '''    const String body = request.substring(headersEnd + 4);
    request = "";''', '''    const String body = request.substring(headersEnd + 4);
#if defined(MCZ_ALEXA_RADIO)
    if (!isGet && url.startsWith("/api") && url.indexOf("state") > 0) {
        const uint32_t mask = WiFi.subnetMask();
        if (!request.startsWith("PUT ") || !url.endsWith("/lights/1/state")
            || strlen(body.c_str()) != body.length() || !MczAlexa::isPowerRequest(body.c_str())
            || WiFi.status() != WL_CONNECTED || !mask
            || (uint32_t(client->remoteIP()) & mask) != (uint32_t(WiFi.localIP()) & mask))
            return false;
    }
#endif
    request = "";''')

header = library / "src/fauxmoESP.h"
original_header = header.read_text(encoding="utf-8")
declarations = replace(original_header, "AsyncClient * _tcpClients[FAUXMO_TCP_MAX_CLIENTS];",
                       "AsyncClient * _tcpClients[FAUXMO_TCP_MAX_CLIENTS];\n        String _tcpRequests[FAUXMO_TCP_MAX_CLIENTS];")
declarations = replace(declarations, "bool _onTCPData(AsyncClient *client, void *data, size_t len);",
                       "bool _onTCPData(AsyncClient *client, void *data, size_t len, String& request);")
if declarations != original_header:
    header.write_bytes(declarations.encode("utf-8"))
if content != original:
    source.write_bytes(content.encode("utf-8"))
