---
name: feishu-docx
description: Export Feishu/Lark cloud documents to Markdown. Supports docx, sheets, bitable, and wiki. Use this skill when you need to read, analyze, or reference content from Feishu knowledge base.
---

# Feishu Docx Exporter

Export Feishu/Lark cloud documents to Markdown format for AI analysis.

## Instructions

### Setup (One-time)

1. Install the tool:
```bash
pip install feishu-docx
```

2. Configure Feishu app credentials:
```bash
feishu-docx config set --app-id YOUR_APP_ID --app-secret YOUR_APP_SECRET
# or use environment variables
```

3. Authorize with OAuth (opens browser):
```bash
feishu-docx auth
```

### Export Documents

Export any Feishu document URL to Markdown:

```bash
feishu-docx export "<FEISHU_URL>" -o ./output
```

The exported Markdown file will be saved with the document's title as filename.

### Supported Document Types

- **docx**: Feishu cloud documents → Markdown with images
- **sheet**: Spreadsheets → Markdown tables
- **bitable**: Multidimensional tables → Markdown tables
- **wiki**: Knowledge base nodes → Auto-resolved and exported

## Examples

### Export a wiki page

```bash
feishu-docx export "https://xxx.feishu.cn/wiki/ABC123" -o ./docs
```

### Export a document with custom filename

```bash
feishu-docx export "https://xxx.feishu.cn/docx/XYZ789" -o ./docs -n meeting_notes
```

### Export spreadsheet as Markdown table

```bash
feishu-docx export "https://xxx.feishu.cn/sheets/DEF456" --table md
```

### Read content directly (recommended for AI Agent)

```bash
# Output content to stdout instead of saving to file
feishu-docx export "https://xxx.feishu.cn/wiki/ABC123" --stdout
# or use short flag
feishu-docx export "https://xxx.feishu.cn/wiki/ABC123" -c
```

### Read content without saving to file (Python)

```python
from feishu_docx import FeishuExporter

exporter = FeishuExporter(app_id="xxx", app_secret="xxx")
content = exporter.export_content("https://xxx.feishu.cn/wiki/xxx")
print(content)
```

## Command Reference

| Command                    | Description                 |
|----------------------------|-----------------------------|
| `feishu-docx export <URL>` | Export document to Markdown |
| `feishu-docx auth`         | OAuth authorization         |
| `feishu-docx config set`   | Set credentials             |
| `feishu-docx config show`  | Show current config         |
| `feishu-docx config clear` | Clear token cache           |

## Tips

- Images are automatically downloaded to a folder named after the document
- Use `--table md` for Markdown tables instead of HTML
- Token is cached and auto-refreshed, no need to re-authorize
- For Lark (overseas), add `--lark` flag
