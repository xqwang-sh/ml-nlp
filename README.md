# ML NLP Handouts

Public teaching materials for the Module B financial text intelligence project.

This public repository intentionally excludes instructor-only notes, rubrics, and the top-level numbered Quarto source files. The rendered book is available under `_book/`, and student-facing labs, templates, and starter code are included.

## Contents

- `_book/`: rendered Quarto book HTML
- `labs/`: runnable classroom demos
- `starter_example/`: offline starter workflow and API smoke-test scaffold
- `templates/`: student project templates

## Quick Checks

```bash
cd starter_example
python3 -m pip install -r requirements.txt
python3 run.py all
```

For the live CNINFO classroom demo:

```bash
cd labs/cninfo_reduction_lab
python3 -m pip install -r requirements.txt
python3 src/pipeline_run.py --step all
```
