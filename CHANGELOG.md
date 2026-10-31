# Changelog

## 3.0.0 (2026)

First version under the Urai App name. Previously called "MarkItDown untuk Windows" (MarkItDown for Windows; versions 1 and 2, based on Tkinter).

- New web-based interface inside the app window (pywebview + WebView2).
- Interface in English (default) or Bahasa Indonesia, including app messages, generated Markdown, AI prompts, and the installer; light, dark, or system theme.
- Drag and drop for files and folders, a **Send to** menu entry, and a list order you can rearrange by dragging.
- Select one, several, or all documents to remove them from the list, or clear the list; files on disk are never deleted.
- Edit results directly: change or delete parts in the preview, edit the Markdown text, or rename and delete mind map branches; edits are saved to the `.md` file.
- Output as one file per document or merged into one.
- Offline scan reading with the bundled Tesseract OCR (ind, eng, jav, sun, ara); PDF pages are rendered with pypdfium2. PyMuPDF (AGPL) is no longer used.
- Detection of scanned and mixed PDFs; text from images inside Word, PowerPoint, and Excel.
- AI mode for Claude, Gemini, DeepSeek, OpenAI, OpenRouter, and OpenAI-compatible servers; API keys in Windows Credential Manager.
- Mind maps (markmap, offline): document structure or AI summaries (Key points, Minutes, Full summary), staged for long documents; per-level styling; save as PDF, PNG, HTML, or Markdown.
- About, Help, and Support pages (QRIS GoPay Merchant).
- Per-user installer (Inno Setup) and portable version, built automatically on GitHub Actions with a self-test.
