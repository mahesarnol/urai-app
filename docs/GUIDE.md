# Urai App Guide

**English** · [Bahasa Indonesia](GUIDE.id.md)

Urai App converts documents into Markdown (`.md`) text: a simple text format that is easy for both people and AI assistants to read. An `.md` file opens in Notepad and is much smaller than the original PDF or PowerPoint.

The app is available in English (default) and Bahasa Indonesia, with a light, dark, or system theme. Change them in **Settings › General**; the change applies immediately.

## 1. Add documents

- **Drag** files or folders from File Explorer anywhere onto the Urai App window. A blue overlay appears while the files are over the window; release to add them.
- Or press **File** (select several files at once with Ctrl or Shift) and **Folder** (every supported file in that folder and its subfolders is added; `.md` files are skipped so old results are not read again).
- **Links**: paste a YouTube link or web page into the field at the very bottom, then press Enter. You can also drag a link from your browser onto the Urai App window.
- **Send to**: in File Explorer, right-click a file and choose **Send to › Urai App** (on Windows 11: **Show more options › Send to**).
- First time? Press **Try with sample files** to see how it works with six sample files.

Supported formats: PDF, Word (`.docx`), PowerPoint (`.pptx`), Excel (`.xlsx`, `.xls`), CSV, images (JPG, PNG, WEBP, BMP, TIFF), audio (WAV, MP3, M4A, MP4), EPUB, ZIP, HTML, Outlook (`.msg`), and text (TXT, JSON, XML).

Each row in the list shows the file type, the number of pages, slides, or sheets, and the file size. PDFs that turn out to be scans (no selectable text) are labeled **Scanned**.

### Select and remove documents

- Tick the box on a row to select it, or **Select all** above the list. The bar shows how many are selected.
- **Remove selected** removes the ticked rows. **Clear all** empties the list; press it once more within a few seconds to confirm.
- In the list before converting, you can also point to a row and press × to remove just that one.
- Removing only takes documents off the list. Files on your computer, and results that were already saved, are never deleted.

## 2. Choose output

### Output type

- **One file per document**: each document becomes one `.md` file with the same name. If that name already exists, the new file gets a number, for example `Report (2).md`. Existing files are never overwritten.
- **Combine into one**: all documents are merged into a single file. Set its name in **Combined file name** (default `Combined`). The contents follow the order of the list; drag the dotted handle on the left of a row to move it, or select the handle and press the up/down arrow keys. The file starts with a short table of contents listing all document names.

### Read images & scans

| Mode | Best for | Notes |
| --- | --- | --- |
| **Off** | Regular digital documents | Images and scanned PDFs are skipped. |
| **Offline** | Almost everything | Free, no internet, documents never leave your computer. Runs on your CPU. |
| **AI** | Blurry scans, handwriting, charts | More accurate and can describe charts. Billed by usage on your AI account. |

Press **Configure** under the modes, or **Settings › Offline reading**, to choose:

- **Languages in your documents**: Indonesian, English, Javanese, Sundanese, Arabic. Select only the languages that actually appear; fewer languages means faster, more accurate results.
- **Accuracy**: *Fast* for clean scans, *Thorough* for blurry scans or phone photos (about twice as slow).
- **Also read images inside Word, PowerPoint, and Excel files**: for example charts or tables pasted as pictures. Their text is added at the end of that document's result.

### Accurate PDF engine (optional)

The standard engine is fast, but tables with long text in their cells, headings, and multi-column layouts in PDFs can come out messy. The **Accurate (Docling)** engine reads the page layout first, so tables, headings, and paragraphs come out much cleaner.

1. Open **Settings › Offline reading** and choose **Accurate (Docling)** under **PDF engine**. Changes here apply right away.
2. The first time, the app offers a one-time download of about 1 GB. Press **Download**. You can close the window while it downloads; Accurate turns on by itself when it finishes. If the download is interrupted, it continues where it left off next time.
3. After that it works offline. PDFs in the list get an **Accurate** tag.

Good to know:

- It is about 3–5 times slower than the standard engine, and the first PDF after starting the app takes longer while the engine loads.
- Only PDFs with text use it. Word, PowerPoint, and Excel files, and fully scanned PDFs, keep using the standard reader and OCR. In PDFs that are only partly scanned, the scanned pages are read with offline OCR inside the accurate engine.
- If the accurate engine fails on a document, the app reads it with the standard engine instead and shows a note on that row.
- To free the space again, press **Remove** under the engine status.

### Using AI mode

1. Open **Settings › AI**.
2. Choose a provider, then use the link under the API key field to create an API key on that provider's website.
3. Paste the API key, press **Test connection**, then **Save & use this mode**.

API keys are stored in Windows Credential Manager, not in a plain file. The model name can be changed under **Advanced: model and server address**; to read images, the model must support image input. For the **Other** provider, enter the address of an OpenAI-compatible server (for example a local server) and the model name.

For confidential documents or personal data, use **Offline** mode.

### Save to

Results are saved to `Documents\Urai App` unless you choose another folder with **Change**, or tick **Save in the same folder as the original files**. If the destination folder cannot be written to (for example a write-protected flash drive), results are saved to `Documents\Urai App` automatically.

## 3. Convert and view results

Press the blue button or **Ctrl + Enter**. While it runs, you can see the percentage, the document being processed, and the current page when reading scans. Press **Cancel** to stop; documents that are already finished stay saved.

When it is done:

- **Open this file** / **Open file**: opens the `.md` file in the default Windows app.
- **Open folder**: opens the results folder in File Explorer.
- **Copy text**: copies the Markdown to the clipboard, ready to paste into ChatGPT or another app.
- Click a row in the list to see that document's result. The **Preview** tab shows headings, lists, and tables neatly; the **Markdown text** tab shows the file content as is.
- The **Size** indicator shows the word count. Above about 60,000 words, some AI assistants start to struggle; consider saving separately.

Yellow rows (**Needs review**) explain the problem in the row itself. For example, a scanned PDF while the mode is Off: press **Turn on offline scan reading** to read it again without redoing everything. Red rows (**Failed**) state the cause, for example a password-protected file.

**Convert other documents** clears the list. **Change settings and redo** returns to step 2 with the same list.

### Edit the results

Press **Edit** in the preview bar. The yellow bar shows whether there are unsaved changes.

- **Preview** tab: point to a part (a heading, paragraph, list, or table) and press the pencil to edit its Markdown, or the bin to delete it. Press **Apply** (or Ctrl + Enter) to keep the change, **Cancel** (or Esc) to drop it. Only the part you change is touched; everything else stays exactly as it was.
- **Markdown text** tab: type directly in the text. **Ctrl + S** saves.
- **Save changes** writes the edits to the `.md` file. **Discard** goes back to the last saved text. **Done** leaves edit mode.
- If you try to switch documents or start over with unsaved changes, the app asks you to save or discard them first.
- With **Combine into one**, you edit the whole combined file.
- After saving, mind maps of that document are rebuilt from the edited text.

## 4. Summary

Open the **Summary** tab in the results panel (or press the **Summary** button). Summaries are written by AI, so they need an API key (see *Using AI mode*). The whole text of the selected document, or of the whole combined file, is sent to your AI provider.

1. Choose a **Summary length**:
   - **Short**: one paragraph.
   - **Medium**: an opening paragraph, key points, and the conclusion.
   - **Detailed**: section by section, in the document's order.
2. Press **Create summary**. Very long documents are summarized in stages. The summary is written in the app's language.
3. Then you can **Copy** it, **Save .md** it as a file, switch to another length, press **Create again**, or press **Make a mind map from this**.

AI summaries can be wrong. Always check them against the original document.

### Adjust the AI instructions

Open **Settings › Prompts** to change what the AI focuses on, for each summary length (Short, Medium, Detailed) and each mind map type (Key points, Minutes, Full summary). Edited instructions are marked **Customized**, and **Reset to default** brings back the original text. Press **Save** to keep your changes. Urai App always adds the rules for the output format and language, so results still display correctly.

## 5. Mind map

Open the **Mind map** tab in the results panel (or press the **Mind map** button).

1. Choose what to **Summarize from**:
   - **Document structure**: free and offline. Branches come from the document's headings, subheadings, lists, and tables. Works best for Word and PowerPoint files that use heading styles.
   - **AI summary**: more concise, and can combine several documents. Choose a **Summary type**:
     - **Key points**: the core of the document in a few short points.
     - **Minutes**: meeting details, topics discussed, decisions, action items, and open questions. Good for meetings, interviews, and podcasts.
     - **Full summary**: every important part of the document, in its order, written concisely.

     The full document text is sent to the AI provider; its word count is shown before you press the button. Very long documents are summarized in stages. The summary is written in the app's language.
   - **From summary**: free and offline. Builds the map from a summary you made in the **Summary** tab; choose which summary length to use. Nothing more is sent to the AI.
2. Press **Create mind map** or **Create AI summary**.
3. In the mind map: pan by dragging, zoom with the mouse wheel or the − and + buttons, and click the circle on a branch to collapse or expand it. **Fit** returns to screen size, **Collapse** shows only the main branches, **Full screen** is for presenting, and **Text** shows the summary as a list.

The mind map covers the selected row. For combined results, view the whole combined file to summarize all documents at once.

### Edit the mind map

Press the pencil button in the mind map toolbar.

- Click a branch to open a small editor: change the text and press **Rename** (or Enter), or press **Delete branch** to remove it together with everything under it. The main title can only be renamed.
- In the **Text** view you can edit the whole outline, then press **Apply changes** (or Ctrl + Enter).
- **Undo** (or Ctrl + Z) reverses the last change. **Done** leaves edit mode.
- Saved mind maps (PDF, PNG, HTML, Markdown) use your edited version.

### Style

Press **Style** to set:

- **Color theme**: Rainbow, Urai, Soft, or Monochrome.
- **Coloring**: *By branch* (each branch has its own color) or *By level* (one color for each level).
- **Distinct branch colors down to**: levels below the chosen one take the color of their parent branch.
- **Color and line width per level**, **Maximum text width**, **Spacing between levels**, and **Show down to**.

The last style is remembered for the next mind map. **Reset to default** resets it.

### Save

Press **Save** and choose:

- **PDF (print-ready)**: A4, A3, or F4 (folio) paper, landscape or portrait. It can include the document title and date, a summary source label ("AI summary, please double-check"), and an extra page with the summary as text. The mind map is fitted to one page automatically; for large mind maps, choose A3.
- **PNG image**: for presentations or social media.
- **Interactive HTML**: a single file that opens in any browser and can still be collapsed and panned, with no internet needed.
- **Markdown (.md)**: the summary outline as text.

AI summaries can be wrong. Always check them against the original document before using them.

## 6. Experimental features

Both depend on third-party services that may change at any time.

- **YouTube links**: fetch the title, description, and transcript. Only works for videos that have subtitles or automatic transcripts; the Indonesian transcript is tried first, then English. If YouTube rejects requests from your network, try again later.
- **Voice recordings**: converted to Indonesian text through Google's speech recognition service, so this needs internet and the recording is sent to Google. WAV files work directly. MP3, M4A, and MP4 files need [FFmpeg](https://www.gyan.dev/ffmpeg/builds/) installed and on the Windows PATH. Long recordings may be rejected by the service; split them into parts of a few minutes.

## 7. Troubleshooting

| Problem | Cause and fix |
| --- | --- |
| The window is blank or Urai App will not open | Microsoft Edge WebView2 Runtime is not installed. Download it free from Microsoft's website, install it, and open the app again. |
| "Windows protected your PC" during installation | The installer is not signed yet. Click **More info › Run anyway** if the file came from the official page. |
| A scanned PDF comes out empty | Scan reading is set to Off. Choose Offline, or press **Turn on offline scan reading** on its row. |
| OCR results have many wrong letters | Set **Accuracy** to *Thorough*, make sure the selected languages are right, or use AI mode. |
| "The API key was rejected" | The API key is wrong or has been revoked. Create a new API key on the provider's website and paste it again. |
| The AI provider reports a usage limit or quota | Your AI account has run out of balance or quota. Top up, wait, or use Offline mode. |
| The file cannot be saved | A file with the same name is open in another app, or the folder is not writable. Results are saved to `Documents\Urai App` automatically. |

Still having trouble? Open an issue at <https://github.com/mahesarnol/urai-app/issues> and, if it helps, attach the file `%APPDATA%\UraiApp\logs\urai.log`. That log contains file names and error messages, not the contents of your documents. Issues are public, so check the log first and remove any file or folder names you don't want to share.
