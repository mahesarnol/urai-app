# Changelog

## 3.1.0 (2026)

- Optional **Accurate (Docling)** PDF engine: much cleaner tables, headings, and paragraphs for PDFs with text. It is a separate one-time download (about 1 GB) that resumes if interrupted, is verified with SHA-256, works offline, and can be removed again. Fully scanned PDFs and other formats keep the standard reader; if the engine fails, the app falls back to the standard reader and notes it on the row.
- New **Summary** tab before the mind map: AI summaries in three lengths (Short, Medium, Detailed) that can be copied, saved as `.md`, or turned into a mind map with the new **From summary** source (offline, no extra AI call).
- **Settings › Prompts**: edit the AI instructions for each summary length and mind map type, with Reset to default; the output-format and language rules are always added so results still display correctly.
- The accurate engine is compiled while it installs, so the first conversion afterwards is about four times faster.
- Document-structure mind maps keep a lone level-1 heading that comes after other headings, and handle the heading style of the accurate engine.

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
