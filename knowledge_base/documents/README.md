# Local Knowledge Base Documents

Put your local reference files in this folder.

Supported file types:

- `.txt`
- `.md`
- `.pdf`
- `.docx`

After adding or editing files, rebuild the index from the project root:

```bash
python knowledge_base/index_documents.py
```

You can also type `reindex` inside the chat program.

PDF support works best for files that contain selectable text. If a PDF is a scanned image, it may need OCR before the assistant can read it.

Word `.docx` support reads normal paragraphs and table text.
