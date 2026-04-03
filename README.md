# daily-zine

[![GitHub Pages](https://img.shields.io/badge/site-live-2ea44f?style=flat-square)](https://fglass.github.io/daily-zine/)

Generate a daily zine from your news feed. Currently only supports Readwise Reader.

## Setup

Install Python dependencies:

```bash
uv sync
```

Install native PDF rendering libraries. On macOS:

```bash
brew install pango gdk-pixbuf libffi
```

Create `.env` with your Readwise token:

```bash
READWISE_TOKEN=your_readwise_access_token_here
```

## Usage

Preview article selection without rendering:

```bash
uv run ziner --dry
```

Render the default zine PDF:

```bash
uv run ziner
```

Render a plain sequential full-size PDF instead of the imposed zine:

```bash
uv run ziner --fullsize
```

Flags:

- `-s, --max-sheets` sets the sheet budget. Each sheet represents 2 printed page sides. Default: `5`
- `-o, --output` sets the output file
- `--fullsize` writes the normal sequential PDF instead of the imposed zine sheets
- `--title` sets the zine title
- `--dry` prints the selected articles without rendering

## Publishing

The repository includes a daily publishing workflow at `.github/workflows/daily-zine.yml`. Zines are served via [GitHub Pages](https://fglass.github.io/daily-zine/).

## Printing

Print the default zine PDF with the following settings:

- Double-sided
- Flip on short edge
- Actual size / 100%

Then keep the sheets in order, fold the stack in half, and staple on the fold if desired.
