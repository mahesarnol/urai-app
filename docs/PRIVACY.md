# Urai App Privacy Policy

**English** · [Bahasa Indonesia](PRIVACY.id.md)

> **Draft, last updated 31 October 2026.** To be reviewed by the developer before publication.

Urai App is a free, open-source Windows app that converts documents into Markdown text on your own computer. This policy explains what happens to your data when you use it.

## In short

- Urai App has **no server, no account, no analytics or tracking, and no ads**. The developer does not receive any of your documents, results, settings, or usage data.
- Your documents are processed **on your computer**. They only leave it when you use one of the features listed under [When data leaves your computer](#when-data-leaves-your-computer), and only to the service that feature needs.

## What stays on your computer

| Data | Where it is stored | Notes |
| --- | --- | --- |
| Your documents and the `.md` results | Where the documents already are, and the output folder you choose (by default `Documents\Urai App`) | Urai App never deletes or uploads your original files. |
| Settings (language, theme, output options, chosen AI provider and model) | `%APPDATA%\UraiApp\settings.json` | Plain text file on your computer. |
| API keys for AI providers | Windows Credential Manager | Only if Credential Manager is unavailable, keys are stored in `%APPDATA%\UraiApp\keys.json`, readable only by your Windows account. |
| Log file | `%APPDATA%\UraiApp\logs\urai.log` (up to about 4 MB, older entries are removed automatically) | Contains file names, folder paths, and error messages to help solve problems. It does not contain the contents of your documents. |
| Temporary images for offline OCR | Your Windows temporary folder | Deleted right after each page is read. |

## When data leaves your computer

Data is only sent when **you** use one of these features:

| Feature | What is sent | Sent to |
| --- | --- | --- |
| **AI mode** (reading scans and images with AI) | Images of the pages or pictures being read, and your API key | The AI provider you chose (for example Anthropic, Google, DeepSeek, OpenAI, OpenRouter, or a server address you entered) |
| **AI summary** for mind maps | The text of the selected documents, and your API key | The AI provider you chose |
| **Test connection** in AI settings | A tiny test image and your API key | The AI provider you chose |
| **YouTube links and web pages** | A normal request for that page or video transcript | The website itself (for example YouTube) |
| **Voice recordings** (experimental) | The audio recording | Google's speech recognition service |
| **Check for updates** (only when you press the button) | A request for the latest version number | GitHub (`api.github.com`) |
| Links to provider pages, the source code, or downloads | Opened in your normal web browser | The website you open |

These services handle your data under their own privacy policies and terms, which the developer does not control. Like any website, they can see your IP address. AI usage is billed to your own account with the provider. **For confidential documents or personal data, use the Offline mode and the free Document structure mind map**, which never send anything.

The app window is shown with Microsoft Edge WebView2, a Windows component made by Microsoft. Its diagnostic data, if any, follows your Windows privacy settings and Microsoft's privacy statement.

## Supporting the developer

Support payments are made with QRIS, scanned from your own banking or e-wallet app. The payment is processed entirely by your bank or e-wallet and GoPay; Urai App does not receive any payment information. The **I've supported** button only saves a note on your computer so the support reminder is no longer shown.

## Reporting a problem

If you report a problem on GitHub Issues, everything you post there is **public**. Before attaching the log file, check it and remove file names or folder paths you do not want to share.

## Your choices

- Remove a saved API key in **Settings › AI**.
- Delete the `%APPDATA%\UraiApp` folder to remove all settings, saved keys in `keys.json`, and logs. Keys in Windows Credential Manager can be removed in the app or in Windows **Credential Manager** (entries named `UraiApp`).
- Uninstall the app from Windows **Settings › Apps › Installed apps**. Your documents and results are not removed.

## Changes to this policy

If the way Urai App handles data changes, this policy will be updated in the project repository, with a new date at the top.

## Contact

Questions about this policy: open an issue at <https://github.com/mahesarnol/urai-app/issues>.
