# Changelog

## 3.0.0 (2026)

First version under the Urai App name. Previously called "MarkItDown untuk Windows" (MarkItDown for Windows; versions 1 and 2, based on Tkinter).

- New web-based interface inside the app window (pywebview + WebView2), following the Windows light/dark theme.
- Drag and drop for files and folders, a **Send to** menu entry, and a list order you can rearrange by dragging.
- Output as one file per document or merged into one.
- Offline scan reading with the bundled Tesseract OCR (ind, eng, jav, sun, ara); PDF pages are rendered with pypdfium2. PyMuPDF (AGPL) is no longer used.
- Detection of scanned and mixed PDFs; text from images inside Word, PowerPoint, and Excel.
- AI mode for Claude, Gemini, DeepSeek, OpenAI, OpenRouter, and OpenAI-compatible servers; API keys in Windows Credential Manager.
- Mind maps (markmap, offline): document structure or staged AI summaries for long documents; per-level styling; save as PDF, PNG, HTML, or Markdown.
- About, Guide, and Support pages (QRIS GoPay Merchant).
- Per-user installer (Inno Setup) and portable version, built automatically on GitHub Actions with a self-test.
