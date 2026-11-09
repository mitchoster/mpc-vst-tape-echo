# Alternative skins

`vst/` holds the Classic skin. `rack/` is the other interface: the layout, the stylesheet and the PIL art
generators (no generated PNGs).

To build it by hand: copy its `layout.conf`, `skin.css`, `skin_post.py` and `art/` over a copy of `vst/`
(keep `vst/vst.json` and `vst/src/`), run `art/make_te_skin.py` and `art/make_vu.py`, then `vst/build.sh`
and `vst/preview.sh`.

`vst/make_skinset.sh` does exactly that, builds Classic, and merges both into one plugin folder
(`dist-local/`). It is what `vst/release.sh` packages.

## Adding a third interface

1. Copy `vst/` (or `skins/rack/`) into a scratch lab, keep `vst.json`, `params.json`/the module
   JSON and `vst/src/**` untouched, and change only `layout.conf`, `skin.css`, `skin_post.py` and the art
   generators.
2. Build it: `python3 tools/gen_vst.py <lab>/vst/vst.json`, then `studio.py preview` and look at every page.
3. Extend the switch: add `<name>` to the engine's `SKIN_DIRS`/`SKIN_TXT` list and to the `ui` options in the
   parameter source, then rebuild the plugin.
4. Add the folder under `skins/<name>/` and merge it in `vst/make_skinset.sh`
   (`classic=… rack=… <name>=… --active classic`).
5. Package with `vst/release.sh` / `tools/release.py`, check with `catalog_check.py <zip> --catalog`, and test on
   the device: tap the control, `cmp` `Plugin Skins/TUI.json` against `Plugin Skins/<name>/TUI.json`, then
   remove+insert the instance and look.

Cost to expect: a new interface is layout + art work only — the switch, the packaging and the release flow are
already there.

Note: the option texts of an `enum_h` row are baked into its segment PNGs, so changing the number of
interfaces always needs a fresh skin build — deleting a tile is not enough.
