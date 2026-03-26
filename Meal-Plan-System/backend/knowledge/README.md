# Clinical prompt supplement (from `Prompt.pdf`)

The nutrition assistant’s **LLM** (when `OPENAI_API_KEY` or `OLLAMA_HOST` is set) can include extra instructions from a **plain-text** file:

- **Default path:** `backend/knowledge/clinical_prompt_supplement.txt`
- **Override:** set env `CLINICAL_PROMPT_SUPPLEMENT_PATH` to another `.txt` file.

## Using your PDF

`Prompt.pdf` is not read directly by the API. Convert it to text, then save as `clinical_prompt_supplement.txt`:

1. **Manual:** copy/paste from the PDF into `clinical_prompt_supplement.txt`.
2. **Script (optional):** with [pypdf](https://pypi.org/project/pypdf/) installed:
   ```bash
   cd backend
   pip install pypdf
   python scripts/extract_prompt_pdf.py "path/to/Prompt.pdf"
   ```
   This writes `knowledge/clinical_prompt_supplement.txt` (UTF-8).

Content is **truncated** (default 8000 characters) to limit tokens. Adjust with `CLINICAL_PROMPT_SUPPLEMENT_MAX_CHARS`.

The file is **optional**; if missing, behavior is unchanged.
