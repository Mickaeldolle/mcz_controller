"""Embed the shared web page in the firmware image at build time."""
from pathlib import Path

Import("env")
source = Path(env.subst("$PROJECT_DIR")) / "app/web"
output = Path(env.subst("$BUILD_DIR")) / "generated/mcz_web_assets.h"
assets = (("PAGE", "index.html"), ("STYLE", "style.css"), ("SCRIPT", "app.js"))
parts = ["#pragma once", "namespace MczWeb {"]

for name, file in assets:
    content = (source / file).read_text(encoding="utf-8")
    if ')MCZ_WEB"' in content:
        raise ValueError(f"Reserved C++ delimiter in {file}")
    chunks = ((name, content),)
    if name == "PAGE":
        marker = 'data-transport="usb"'
        if content.count(marker) != 1:
            raise ValueError("Expected one transport marker in index.html")
        before, after = content.split(marker)
        chunks = (
            ("PAGE_PREFIX", before + 'data-transport="wifi" data-api-key="'),
            ("PAGE_SUFFIX", '"' + after),
        )
    for chunk_name, chunk in chunks:
        parts.append(f'constexpr char {chunk_name}[] = R"MCZ_WEB({chunk})MCZ_WEB";')

parts.append("}")
header = "\n".join(parts) + "\n"
output.parent.mkdir(parents=True, exist_ok=True)
if not output.exists() or output.read_text(encoding="utf-8") != header:
    output.write_bytes(header.encode("utf-8"))
