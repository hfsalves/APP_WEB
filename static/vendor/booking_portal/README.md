# PortoBreak self-hosted browser dependencies

The booking portal serves these dependencies from its own `/static/` endpoint.
Opening a page does not contact Google Fonts or unpkg to load fonts, CSS or
JavaScript. Map tile requests are controlled separately by the portal.

## Inter

- Family: Inter, normal variable weights 400–800, Latin and Latin Extended.
- CSS and original WOFF2 binaries: Google Fonts Inter v20 distribution, retrieved
  from `https://fonts.googleapis.com/css2?family=Inter:wght@400..800&display=swap`.
- Latin source:
  `https://fonts.gstatic.com/s/inter/v20/UcC73FwrK3iLTeHuS_nVMrMxCp50SjIa1ZL7W0Q5nw.woff2`.
- Latin Extended source:
  `https://fonts.gstatic.com/s/inter/v20/UcC73FwrK3iLTeHuS_nVMrMxCp50SjIa25L7W0Q5n-wU.woff2`.
- Upstream: https://github.com/rsms/inter.
- License: SIL Open Font License 1.1, included as `inter/OFL.txt`; license source:
  https://raw.githubusercontent.com/google/fonts/main/ofl/inter/OFL.txt.
- The local CSS preserves Google's font descriptors and Unicode ranges for
  these subsets. Only source paths and comments differ. Binary files are
  unmodified; the subsets cover the portal's PT, EN, ES and FR text.

## Leaflet 1.9.4

- Original distributed CSS, JavaScript, JavaScript source map and all five
  distributed PNG images from `https://unpkg.com/leaflet@1.9.4/dist/`.
- Files retain their original relative paths, including `images/`, so CSS and
  Leaflet's default markers load locally.
- Upstream: https://github.com/Leaflet/Leaflet/tree/v1.9.4.
- License: BSD 2-Clause, included as `leaflet-1.9.4/LICENSE`; license source:
  https://raw.githubusercontent.com/Leaflet/Leaflet/v1.9.4/LICENSE.
- Distributed files are unmodified.
