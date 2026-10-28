# System recipes

System policy is part of the dotfiles repository. See the
[unified workflow guide](../../docs/tjikup.md) for installation, templates,
Bitwarden authentication, file ownership, validation and recovery.

`system/tjikup/recipes.json` is included by the parent `tjikup.json`.
Fi system files use `system/native/fi/manifest.json`. Remaining system templates
render through `scripts/legacy-system.py`, which invokes Chezmoi directly and
does not depend on the retired Chezetc wrapper or separate Systjik checkout.
