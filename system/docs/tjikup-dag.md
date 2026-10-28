# System recipe graph

System maintenance is declared in `tjikup/recipes.json` and scheduled by the
Rust tjikup runner. See [Tjikup recipes](tjikup.md). Templates live in
`etc/.chezmoitemplates/tjikup`, outside the hook inventory. The system file pass
uses the native Fi manifest (legacy Chezmoi files on Li/Si), and rendered commands explicitly use
noninteractive sudo with a small environment allowlist. Resource names are shared
with home recipes. Final networking and release tasks wait for both layers.
