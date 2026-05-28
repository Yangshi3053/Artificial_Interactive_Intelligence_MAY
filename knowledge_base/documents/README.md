# Local Knowledge Base Documents

Put your local reference files in this folder.

The first version supports:

- `.txt`
- `.md`
- `.pdf`

PDF support works best for files that contain selectable text.

If a PDF is a scanned image, it may need OCR before the assistant can read it.

After adding or editing files, rebuild the index from the project root:

```bash
python knowledge_base/index_documents.py
```
