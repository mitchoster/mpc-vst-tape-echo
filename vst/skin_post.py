#!/usr/bin/env python3
"""DubTape2 skin touch-ups on the generated TUI.json (vst.json "skin_post": gen_vst.py runs this
after the skin is built). Pattern and rationale from MagicStino/pulytek's
tools/skin_post.py (see OPENCODE_MEM.md, Quellen-Register):

  1. Live text: use the firmware-native **Roboto** and set explicit heights (28 for values, 26 for
     names) instead of the generator's default, so the silver panel keeps calm, readable lettering
     (only Titillium/Roboto resolve on the device; anything else falls back).
  2. Switches: the generated toggles focus on tap by default -- make every generated toggle toggle
     on tap (`Mouse Down` -> `Toggle Switch`), which is what a switch should do.

Defensive by design: a missing key skips that touch-up instead of failing the build.
Run: python3 vst/skin_post.py <skin folder>
"""
import json
import sys
from pathlib import Path


def main():
    skin = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if not skin:
        raise SystemExit("usage: skin_post.py <skin folder>")
    tui = skin / "Plugin Skins" / "TUI.json"
    d = json.loads(tui.read_text())

    fonts = toggles = 0

    def walk(v):
        nonlocal fonts
        if isinstance(v, dict):
            if v.get("type") == "Label" and isinstance(v.get("data"), dict):
                data = v["data"]
                style = data.get("textStyle", {}).get("font")
                if style:
                    style["name"] = "Roboto"
                    style["style"] = "Regular"
                    style["height"] = 28 if data.get("type") == "Value" else 26
                    fonts += 1
            for child in v.values():
                walk(child)
        elif isinstance(v, list):
            for child in v:
                walk(child)

    walk(d)

    page = d.get("pageData", {})
    defs = page.get("componentDefinitions", {}).get("localComponentDefinitions", [])
    for definition in defs:
        if not str(definition.get("key", "")).startswith("shToggle"):
            continue
        value = definition.get("value", {})
        for action in value.get("actions", []):
            if action.get("onAction") == "Mouse Down":
                action["handler"] = "Toggle Switch"
                toggles += 1

    tui.write_text(json.dumps(d, indent=2) + "\n")
    print("skin_post: %d live text styles -> Roboto, %d toggle handlers -> Toggle Switch" % (fonts, toggles))


if __name__ == "__main__":
    main()
