# Alternative skins

`vst/` holds the Classic skin. These two are the other interfaces from the 1.1.0 release: the layout, the
stylesheet and the PIL art generators (no generated PNGs).

To build one: copy its `layout.conf`, `skin.css`, `skin_post.py` and `art/` over `vst/` (keep `vst/vst.json`
and `vst/src/`), run the art generators listed in the skin's own README section, then `vst/build.sh` and
`vst/preview.sh`.

## Adding a fourth interface

1. Copy `vst/` (or one of the `skins/*` folders) into a scratch lab, keep `vst.json`, `params.json`/the module
   JSON and `vst/src/**` untouched, and change only `layout.conf`, `skin.css`, `skin_post.py` and the art
   generators.
2. Build it: `python3 tools/gen_vst.py <lab>/vst/vst.json`, then `studio.py preview` and look at every page.
3. Extend the switch: add `<name>` to the engine's `SKIN_DIRS`/`SKIN_TXT` list and to the `ui` options in the
   parameter source, then rebuild the plugin.
4. Merge: `python3 tools/make_skinset.py -o "<portable>/<folder>/Plugin Skins" studio=… classic=… rack=… <name>=…
   --active studio` (tools/make_skinset.py, also in sd88me/mpc-vst-plugins).
5. Package with `vst/release.sh` / `tools/release.py`, check with `catalog_check.py <zip> --catalog`, and test on
   the device: tap the control, `cmp` `Plugin Skins/TUI.json` against `Plugin Skins/<name>/TUI.json`, then
   remove+insert the instance and look.

Cost to expect: a new interface is layout + art work only — the switch, the packaging and the release flow are
already there.
