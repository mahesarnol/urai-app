# Urai App Guide

**English** · [Bahasa Indonesia](GUIDE.id.md)

> The app interface is in Indonesian. Buttons and options are written as they appear in the app, with an English translation in parentheses.

Urai App converts documents into Markdown (`.md`) text: a simple text format that is easy for both people and AI assistants to read. An `.md` file opens in Notepad and is much smaller than the original PDF or PowerPoint.

## 1. Add documents

- **Drag** files or folders from File Explorer anywhere onto the Urai App window. A blue overlay appears while the files are over the window; release to add them.
- Or press **File** (select several files at once with Ctrl or Shift) and **Folder** (every supported file in that folder and its subfolders is added; `.md` files are skipped so old results are not read again).
- **Links**: paste a YouTube link or web page into the field at the very bottom, then press Enter. You can also drag a link from your browser onto the Urai App window.
- **Send to**: in File Explorer, right-click a file and choose **Send to › Urai App** (on Windows 11: **Show more options › Send to**).
- First time? Press **Coba dengan file contoh** (Try with sample files) to see how it works with six sample files.

Supported formats: PDF, Word (`.docx`), PowerPoint (`.pptx`), Excel (`.xlsx`, `.xls`), CSV, images (JPG, PNG, WEBP, BMP, TIFF), audio (WAV, MP3, M4A, MP4), EPUB, ZIP, HTML, Outlook (`.msg`), and text (TXT, JSON, XML).

Each row in the list shows the file type, the number of pages, slides, or sheets, and the file size. PDFs that turn out to be scans (no selectable text) are labeled **Hasil scan** (Scanned). To remove a document from the list, hover over its row and press ×.

## 2. Set up the output

### Output format

- **Satu file per dokumen** (One file per document): each document becomes one `.md` file with the same name. If that name already exists, the new file gets a number, for example `Report (2).md`. Existing files are never overwritten.
- **Gabung jadi satu** (Merge into one): all documents are merged into a single file with a name you choose. The contents follow the order of the list; drag the dotted handle on the left of a row to move it, or select the handle and press the up/down arrow keys. The file starts with a short table of contents listing all document names.

### Reading images and scans (Baca gambar & hasil scan)

| Mode | Best for | Notes |
| --- | --- | --- |
| **Mati** (Off) | Regular digital documents | Images and scanned PDFs are skipped. |
| **Offline** | Almost everything | Free, no internet, documents never leave your computer. Runs on your CPU. |
| **AI** | Blurry scans, handwriting, charts | More accurate and can describe charts. Billed by usage on your AI account. |

Press **Atur** (Configure), or **Pengaturan** (Settings) at the top right, to choose:

- **Bahasa di dokumen** (Document languages, Offline mode): Indonesian, English, Javanese, Sundanese, Arabic. Select only the languages that actually appear; fewer languages means faster, more accurate results.
- **Ketelitian** (Accuracy): *Cepat* (Fast) for clean scans, *Teliti* (Thorough) for blurry scans or phone photos (about twice as slow).
- **Baca juga gambar di dalam Word, PowerPoint, dan Excel** (Also read images inside Word, PowerPoint, and Excel): for example charts or tables pasted as pictures. Their text is added at the end of that document's result.

### Using AI mode

1. Open **Pengaturan › AI (berbayar)** (Settings › AI (paid)).
2. Choose a provider, then press **Buka halaman pembuatan API key** (Open the API key page) to create an API key on that provider's website.
3. Paste the API key, press **Tes koneksi** (Test connection), then **Simpan & pakai mode ini** (Save & use this mode).

API keys are stored in Windows Credential Manager, not in a plain file. The model name can be changed under **Lanjutan** (Advanced); to read images, the model must support image input. For the **Lainnya** (Other) provider, enter the address of an OpenAI-compatible server (for example a local server) and the model name.

For confidential documents or personal data, use **Offline** mode.

### Save to (Simpan ke)

Results are saved to `Documents\Urai App` unless you choose another folder with **Ubah** (Change), or tick **Simpan di folder yang sama dengan file asli** (Save in the same folder as the original file). If the destination folder cannot be written to (for example a write-protected flash drive), results are saved to `Documents\Urai App` automatically.

## 3. Convert and view results

Press the blue button or **Ctrl + Enter**. While it runs, you can see the percentage, the document being processed, and the current page when reading scans. Press **Batalkan** (Cancel) to stop; documents that are already finished stay saved.

When it is done:

- **Buka file ini** / **Buka file** (Open this file / Open file): opens the `.md` file in the default Windows app.
- **Buka folder** (Open folder): opens the results folder in File Explorer.
- **Salin teks** (Copy text): copies the Markdown to the clipboard, ready to paste into ChatGPT or another app.
- Click a row in the list to see that document's result. The **Tampilan** (Preview) tab shows headings, lists, and tables neatly; the **Teks Markdown** (Markdown text) tab shows the file content as is.
- The **Ukuran** (Size) indicator shows the word count. Above about 60,000 words, some AI assistants start to struggle; consider saving separately.

Yellow rows (**Perlu dicek**, Needs review) explain the problem in the row itself. For example, a scanned PDF while the mode is Off: press **Aktifkan baca scan offline** (Turn on offline scan reading) to read it again without redoing everything. Red rows (**Gagal**, Failed) state the cause, for example a password-protected file.

**Ubah dokumen lain** (Convert other documents) clears the list. **Ubah pengaturan, ulangi** (Change settings, run again) returns to step 2 with the same list.

## 4. Mind map

Open the **Mind map** tab in the results panel (or press the **Mind map** button).

1. Choose a summary source:
   - **Struktur dokumen** (Document structure): free and offline. Branches come from the document's headings, subheadings, lists, and tables. Works best for Word and PowerPoint files that use heading styles.
   - **Rangkuman AI** (AI summary): more concise, and can combine several documents. Choose a type: **Umum** (General: main points), **Notulen** (Minutes: issues, decisions, follow-ups), or **Laporan** (Report: findings, actors, recommendations). The full document text is sent to the AI provider; its word count is shown before you press the button. Very long documents are summarized in stages.
2. Press **Buat mind map** (Create mind map) or **Buat rangkuman AI** (Create AI summary).
3. In the mind map: pan by dragging, zoom with the mouse wheel or the + and − buttons, and click the circle on a branch to collapse or expand it. **Pas** (Fit) returns to screen size, **Lipat** (Collapse) shows only the main branches, **Layar penuh** (Full screen) is for presenting, and **Teks** (Text) shows the summary as a list.

The mind map covers the selected row. For merged results, choose **Lihat semua** (View all) to summarize all documents at once.

### Style (Gaya)

Press **Gaya** (Style) to set:

- **Tema warna** (Color theme): Pelangi (Rainbow), Urai, Lembut (Soft), or Monokrom (Monochrome).
- **Cara mewarnai** (Coloring): *Per cabang* (By branch: each branch has its own color) or *Per sub* (By level: one color for each level).
- **Warna cabang dibedakan sampai** (Distinct branch colors down to): levels below the chosen one take the color of their parent branch.
- **Line color and width for each level**, **maximum text width**, **spacing between levels**, and **how many levels to show**.

The last style is remembered for the next mind map. **Kembalikan ke bawaan** (Restore defaults) resets it.

### Save (Simpan)

Press **Simpan** (Save) and choose:

- **PDF (siap cetak)** (Print-ready PDF): A4, A3, or F4 (folio) paper, landscape or portrait. It can include the title and date, an "AI summary, please double-check" label, and an extra page with the summary as text. The mind map is fitted to one page automatically; for large mind maps, choose A3.
- **Gambar PNG** (PNG image): for presentations or social media.
- **HTML interaktif** (Interactive HTML): a single file that opens in any browser and can still be collapsed and panned, with no internet needed.
- **Markdown (.md)**: the summary outline as text.

AI summaries can be wrong. Always check them against the original document before using them.

## 5. Experimental features

Both depend on third-party services that may change at any time.

- **YouTube links**: fetch the title, description, and transcript. Only works for videos that have subtitles or automatic transcripts; Indonesian is tried first, then English. If YouTube rejects requests from your network, try again later.
- **Voice recordings**: converted to Indonesian text through Google's speech recognition service, so this needs internet and the recording is sent to Google. WAV files work directly. MP3, M4A, and MP4 files need [FFmpeg](https://www.gyan.dev/ffmpeg/builds/) installed and on the Windows PATH. Long recordings may be rejected by the service; split them into parts of a few minutes.

## 6. Troubleshooting

| Problem | Cause and fix |
| --- | --- |
| The window is blank or Urai App will not open | Microsoft Edge WebView2 Runtime is not installed. Download it free from Microsoft's website, install it, and open the app again. |
| "Windows protected your PC" during installation | The installer is not signed yet. Click **More info › Run anyway** if the file came from the official page. |
| A scanned PDF comes out empty | Scan reading is set to Off. Choose Offline, or press **Aktifkan baca scan offline** (Turn on offline scan reading) on its row. |
| OCR results have many wrong letters | Set Accuracy to **Teliti** (Thorough), make sure the selected languages are right, or use AI mode. |
| "API key ditolak" (API key rejected) | The API key is wrong or has been revoked. Create a new API key on the provider's website and paste it again. |
| "Batas pemakaian atau kuota habis" (Usage limit or quota exceeded) | Your AI account has run out of balance or quota. Top up, wait, or use Offline mode. |
| The file cannot be saved | A file with the same name is open in another app, or the folder is not writable. Results are saved to `Documents\Urai App` automatically. |

Still having trouble? Email maheswara.as@gmail.com and attach the file `%APPDATA%\UraiApp\logs\urai.log`. That log contains file names and error messages, not the contents of your documents.
