#!/usr/bin/env bash
#
# Render the DOPPLER write-ups as shareable PDFs.
#
#   ./experiments/render_pdfs.sh
#
# Inputs   results/writeups/{ARTICLE,PAPER1_METHODS,PAPER2_MAIN}.md
# Outputs  results/writeups/pdf/DOPPLER_{ARTICLE,PAPER1_METHODS,PAPER2_MAIN}.pdf
#
# Needs pandoc and tectonic:  brew install pandoc tectonic
# Fonts are Charter, Avenir Next and Menlo, all of which ship with macOS.
# Styling lives in experiments/pdf/preamble.tex; the AST rewrites (title block,
# dead repo links, figure captions) live in experiments/pdf/doppler.lua.

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
src_dir="$repo_root/results/writeups"
out_dir="$src_dir/pdf"
asset_dir="$repo_root/experiments/pdf"

for tool in pandoc tectonic; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "error: $tool not found. brew install pandoc tectonic" >&2
    exit 1
  fi
done

mkdir -p "$out_dir"

common_opts=(
  --from=markdown
  --pdf-engine=tectonic
  --lua-filter="$asset_dir/doppler.lua"
  --include-in-header="$asset_dir/preamble.tex"
  --resource-path="$src_dir"
  -V documentclass=article
  -V papersize=a4
  -V mainfont=Charter
  -V sansfont="Avenir Next"
  -V monofont=Menlo
  -V monofontoptions=Scale=0.86
  -V colorlinks=true
  -V linkcolor=dopplaccent
  -V urlcolor=dopplaccent
  -V filecolor=dopplaccent
  -V linestretch=1.12
)

# render <source.md> <output.pdf> <fontsize> <geometry-margins>
render () {
  local source="$1" output="$2" fontsize="$3" margins="$4"

  echo "==> $output"
  pandoc "$src_dir/$source" \
    "${common_opts[@]}" \
    -V "fontsize=$fontsize" \
    -V "geometry=$margins" \
    -o "$out_dir/$output"
}

# The article is a reading document: generous margins, a short measure, 11pt.
render ARTICLE.md DOPPLER_ARTICLE.pdf \
  11pt "top=2.6cm,bottom=2.3cm,left=3.2cm,right=3.2cm"

# The papers carry wide tables, so they get a wider text block and 10pt.
render PAPER1_METHODS.md DOPPLER_PAPER1_METHODS.pdf \
  10pt "top=2.4cm,bottom=2.2cm,left=2.3cm,right=2.3cm"

render PAPER2_MAIN.md DOPPLER_PAPER2_MAIN.pdf \
  10pt "top=2.4cm,bottom=2.2cm,left=2.3cm,right=2.3cm"

echo
echo "Done. Wrote to $out_dir:"
ls -la "$out_dir"/*.pdf
