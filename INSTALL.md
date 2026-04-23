# Quiet Channel Paper Package

Drop-in addition to your existing `quiet-channel/` project folder.

## Files

- `paper.md` — the paper itself, 5-6 pages, GitHub-renderable.
- `make_figs.py` — regenerates the 3 publication figures from your `trials.jsonl`.
- `paper-style.css` — typography rules for PDF rendering.
- `build_paper.sh` — one-line compile to `paper.pdf`.
- `fig/` — pre-built figures, already rendered from your 432-trial numbers. You can use these as-is or regenerate from your own data for authenticity (recommended).

## Install

From your `quiet-channel/` root:

```bash
# 1. Move these files in
# (assuming you unzipped this next to quiet-channel/)
cp -R quiet-channel-paper/* quiet-channel/
cd quiet-channel

# 2. (Optional but recommended) regenerate figures from your actual data
source .venv/bin/activate
python make_figs.py --run-dir results/run_20260423_142914

# 3. (Optional) build the PDF. Requires pandoc + wkhtmltopdf.
# Install once if missing:
#   brew install pandoc
#   brew install --cask wkhtmltopdf
chmod +x build_paper.sh
./build_paper.sh
# Output: paper.pdf
```

## Read the paper

- Directly: `paper.md` (GitHub renders images and tables automatically once you push).
- As PDF: after `./build_paper.sh`, open `paper.pdf`.

## Push to GitHub

```bash
# Assuming the repo already exists locally as a git repo
git add paper.md paper-style.css build_paper.sh make_figs.py fig/
git commit -m "Add paper: Quiet Channel, 432 trials, 44.4% unflagged success vs Opus monitor"
git push
```

If the repo does not yet exist:

```bash
gh repo create quiet-channel --public --source=. --remote=origin --push
```

That makes `github.com/<yourhandle>/quiet-channel` live. Update the paper's repo URL (currently `github.com/Rburra1/quiet-channel`) if your handle differs.
