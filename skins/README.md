# Alternative skins

`vst/` holds the Classic skin. These two are the other interfaces from the 1.1.0 release: the layout, the
stylesheet and the PIL art generators (no generated PNGs).

To build one: copy its `layout.conf`, `skin.css`, `skin_post.py` and `art/` over `vst/` (keep `vst/vst.json`
and `vst/src/`), run the art generators listed in the skin's own README section, then `vst/build.sh` and
`vst/preview.sh`.
