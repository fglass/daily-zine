# Daily Zine

Generate a zine from your Readwise Reader feed.

## Setup

Install Python dependencies:

```bash
uv sync
```

Install native PDF rendering libraries.

On macOS:

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

Render the PDF:

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
- `--title` sets the zine title. Default: `Fred Talks`
- `--fullsize` writes the normal sequential PDF instead of the imposed zine sheets
- `--dry` prints the selected articles without rendering

## Print and Fold

Print the default zine PDF:

- double-sided
- flip on short edge
- actual size / 100%

Then keep the sheets in order, nest later sheets inside earlier sheets, fold the stack in half, and staple on the fold if desired.
