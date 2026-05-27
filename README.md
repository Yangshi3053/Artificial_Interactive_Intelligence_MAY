# Local Qwen Chat Assistant

This is a beginner-friendly Python project for chatting with a local Qwen3 14B model through Ollama.

You type text in the terminal. The program sends your message to Ollama, streams the AI response back to the terminal, and opens a small GPU and memory monitor window.

## Project Structure

```text
Artificial_Interactive_Intelligence_MAY/
|-- main.py
|-- requirements.txt
|-- README.md
|-- knowledge_base/
|   |-- __init__.py
|   |-- index_documents.py
|   |-- search.py
|   `-- documents/
|       `-- README.md
|-- model/
|   |-- __init__.py
|   `-- qwen_model.py
`-- monitor/
    |-- __init__.py
    `-- resource_monitor.py
```

## File Guide

### main.py

This is the program entry point.

It is kept small so it is easy to debug.

It does these things:

- shows the welcome message
- starts the GPU and memory monitor window
- asks you to type messages
- prints the AI response while it is being generated
- stores recent conversation history
- searches the local knowledge base before answering
- exits when you type `exit`, `quit`, or `q`
- closes the monitor window when the chat program exits
- lets you type `reindex` to reread local knowledge files

Run the project from this file:

```bash
python main.py
```

### model/qwen_model.py

This file contains the model-related code.

It does these things:

- stores the model name
- builds the prompt sent to Ollama
- keeps the recent chat history inside the prompt
- adds relevant local knowledge base results to the prompt
- calls Ollama's local HTTP API
- streams text pieces back to `main.py`
- handles Ollama connection errors and model errors

The default model is:

```python
MODEL_NAME = "qwen3:14b"
```

The Ollama API endpoint is:

```python
OLLAMA_URL = "http://localhost:11434/api/generate"
```

Long answers are controlled by:

```python
MAX_RESPONSE_TOKENS = 4096
```

Recent conversation history is controlled by:

```python
MAX_HISTORY_CHARACTERS = 12000
```

### knowledge_base/documents/

This folder is the local document library for the assistant.

Put files here when you want the model to search them later.

The first version supports:

```text
.txt
.md
```

### knowledge_base/index_documents.py

This script reads files from `knowledge_base/documents/`, splits them into smaller chunks, and saves a local index.

Run it after adding or editing documents:

```bash
python knowledge_base/index_documents.py
```

### knowledge_base/search.py

This file searches the local index when you ask a question.

It uses simple keyword matching, which keeps the code easy to understand and debug.

Later, this can be upgraded to vector search for smarter retrieval.

### monitor/resource_monitor.py

This file contains the GPU and memory monitor.

It does these things:

- opens a popup chart window
- checks usage every second
- shows the last 120 seconds
- draws GPU usage in red
- draws GPU memory usage in blue
- draws system RAM usage in green
- provides helper functions to start and stop the monitor process

You can also run the monitor by itself:

```bash
python monitor/resource_monitor.py
```

### requirements.txt

This file lists the Python packages used by the project:

```text
requests
psutil
nvidia-ml-py
```

`requests` talks to Ollama.

`psutil` reads system memory usage.

`nvidia-ml-py` reads NVIDIA GPU usage and GPU memory usage.

## Setup

Open a terminal in the outer project folder.

Install dependencies:

```bash
pip install -r requirements.txt
```

Download the Qwen3 14B model:

```bash
ollama pull qwen3:14b
```

Make sure Ollama is running.

## Add Local Files for the Assistant to Search

Put `.txt` or `.md` files into:

```text
knowledge_base/documents/
```

Then build the local index:

```bash
python knowledge_base/index_documents.py
```

After that, run the chat program normally:

```bash
python main.py
```

When you ask a question, the program searches the local index first and sends the most relevant text chunks to the model.

## Run

From the outer project folder, run:

```bash
python main.py
```

Then type your message after:

```text
You:
```

To stop, type one of these:

```text
exit
quit
q
```

The monitor window will close automatically when the chat program exits.

## How Chat Works

The program sends requests to:

```text
http://localhost:11434/api/generate
```

It uses streaming:

```python
"stream": True
```

This lets the terminal show text while the model is still generating.

## How Memory Works

Ollama's `/api/generate` endpoint does not automatically remember previous messages from this Python program.

This project keeps a simple list of recent conversation turns in `main.py`.

Before each request, `model/qwen_model.py` adds that history to the prompt so the model can answer follow-up questions.

This memory lasts only while the program is running. If you close the program, the chat history is cleared.

## How Local File Search Works

This project now has a simple local knowledge base.

The folder is:

```text
knowledge_base/documents/
```

The index file is:

```text
knowledge_base/index.json
```

The index file is generated by:

```bash
python knowledge_base/index_documents.py
```

The current search method is simple keyword search. It is fast and easy to debug, but it is not as smart as vector search yet.

If you add new files, edit files, or delete files, run the indexing command again.

You can also rebuild the index while chatting by typing:

```text
reindex
```

The assistant only knows files that are currently saved in `knowledge_base/index.json`.

If the assistant describes files that are not actually in the index, that is model guessing. The prompt now tells it not to invent file names, purposes, or contents.

## Common Problems

### Ollama is not running

Start Ollama and run the program again.

### The model is not installed

Run:

```bash
ollama pull qwen3:14b
```

### The monitor does not show GPU data

This monitor is designed for NVIDIA GPUs.

Install dependencies again:

```bash
pip install -r requirements.txt
```

### The first answer is slow

Large local models can take time to load the first time.

After the model is loaded, later responses are usually faster.
