#!/bin/bash
set -e
cd "$(dirname "$0")"
pandoc paper.md \
    -o paper.pdf \
    --pdf-engine=weasyprint \
    --css=paper-style.css \
    --standalone \
    --metadata title=""
echo "Built paper.pdf"
