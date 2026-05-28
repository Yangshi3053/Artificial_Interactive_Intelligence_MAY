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
|-- memory/
|   |-- __init__.py
|   |-- long_term_memory.py
|   `-- README.md
|-- system_context/
|   |-- __init__.py
|   `-- local_info.py
|-- online_search/
|   |-- __init__.py
|   `-- web_search.py
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
- stores searchable long-term memory in a local database
- searches the local knowledge base before answering
- searches the web when the question needs current information
- prints whether web search was used before the AI answer
- ranks web sources with a 1-5 source quality tier system
- searches in locally relevant languages when useful
- reads local date, time, timezone, region, and approximate location context
- exits when you type `exit`, `quit`, or `q`
- closes the monitor window when the chat program exits
- lets you type `reindex` to reread local knowledge files
- lets you type `memory` to see long-term memory status
- lets you type `system` to see local system context

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
- adds relevant long-term memory to the prompt
- adds relevant local knowledge base results to the prompt
- adds web search results to the prompt when needed
- tells the model the real local runtime status so it does not claim cloud API limits
- adds local system context for date, time, timezone, region, and approximate location
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

The local Ollama context setting is recorded as:

```python
OLLAMA_CONTEXT_TOKENS = 32768
```

This is project runtime information, not the Alibaba Cloud Qwen API limit.

### system_context/local_info.py

This file reads safe local computer context.

It does these things:

- reads the current local date
- reads the current local time
- reads the local timezone and UTC offset
- reads Windows region and culture settings
- reads basic computer and OS information
- optionally reads approximate network location from public IP

Important: the location is not true GPS. Most desktop/laptop computers do not expose a GPS chip to Python. The current location method is approximate IP-based location, which can be wrong if you use a VPN, school network, mobile hotspot, or proxy.

### memory/long_term_memory.py

This file contains the long-term memory system.

It does these things:

- creates a local SQLite database
- saves chat messages after successful answers
- extracts durable user preferences and instructions
- classifies durable memories by topic
- stores importance, confidence, and usage count for each durable memory
- searches old memories before each new answer
- ranks memories with topic matching, importance, confidence, use count, and age decay
- formats relevant memory for the model prompt

The memory database is stored locally:

```text
memory/memory.sqlite
```

This file is ignored by Git, so private memory is not uploaded to GitHub.

### knowledge_base/documents/

This folder is the local document library for the assistant.

Put files here when you want the model to search them later.

The current version supports:

```text
.txt
.md
.pdf
.docx
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

### online_search/web_search.py

This file contains the simple web search tool.

It does these things:

- decides whether a question probably needs live web information
- builds multilingual search queries for country-specific questions
- searches the web for current information
- ranks sources by quality tier before choosing excerpts
- reads text from the top pages
- sends source links and excerpts to the model

You can force web search by starting a question with:

```text
web:
```

Example:

```text
web: latest Ollama Qwen model news
```

### requirements.txt

This file lists the Python packages used by the project:

```text
requests
psutil
nvidia-ml-py
pypdf
python-docx
```

`requests` talks to Ollama.

`psutil` reads system memory usage.

`nvidia-ml-py` reads NVIDIA GPU usage and GPU memory usage.

`pypdf` reads text from PDF files in the local knowledge base.

`python-docx` reads text from Word `.docx` files in the local knowledge base.

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

Put `.txt`, `.md`, `.pdf`, or `.docx` files into:

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

PDF support works best when the PDF contains selectable text. If the PDF is scanned pages or images, you may need OCR before the assistant can read the words.

Word `.docx` support reads normal paragraphs and table text.

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

You can check memory status by typing:

```text
memory
```

The memory status includes topic groups, average importance, average confidence, and how often memories have been reused.

You can check local system context by typing:

```text
system
```

This shows date, time, timezone, Windows region settings, and approximate IP location if available.

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

## How Local System Context Works

Before each answer, the program reads local system context and sends it to the model.

This helps the assistant answer questions like:

```text
今天几号？
现在几点？
我现在大概在哪个时区？
```

The system context includes:

```text
local date
local time
timezone
UTC offset
Windows culture
Windows home location
basic OS information
approximate IP location when available
```

The approximate location is not exact GPS. It is based on public IP lookup and should be treated as approximate.

## How Web Search Works

The assistant usually answers directly from the local model and local knowledge base.

If your question looks like it needs current web information, the program searches the web first.

Before the answer, the terminal prints one of these:

```text
Web search: not used
Web search: used, 3 source(s)
```

When web search is used, the terminal also prints the source titles and URLs.

The terminal also prints the query plan. For example, if you ask in Chinese about Canadian gas prices, the program can search English and French queries because those are more likely to find official Canadian sources.

Examples that trigger web search:

```text
latest AI news
today's weather
search: Qwen3 14B Ollama
web: current NVIDIA driver
```

The model receives:

- source links
- source quality tiers
- multilingual query plan
- short webpage excerpts
- your original question

When it uses web information, it should mention source numbers like `[1]` or `[2]`.

Source quality tiers:

```text
Tier 1: official sources
Government websites, company websites, official docs, product manuals, official GitHub, official announcements

Tier 2: authoritative institutions and professional databases
EIA, IEA, Trading Economics, Bank of Canada, ST, NVIDIA, Raspberry Pi official docs

Tier 3: mainstream or professional media
Reuters, AP, BBC, CBC, CNBC, Bloomberg, The Verge, Tom's Hardware

Tier 4: blogs, forums, personal websites, tutorial sites
Useful as reference, but not as the only evidence

Tier 5: unclear sources or repost sites
Avoid when possible
```

The model is instructed not to invent data. If a number is not visible in the searched excerpts, it should say the excerpts do not provide that number.

For common oil-price questions, the search module also has fallback authoritative sources. For example, Iran, Russia, the United States, and Canada can fall back to EIA, GlobalPetrolPrices, or official government energy pages when the search result page returns too few useful sources.

If there is no internet connection or the web page blocks reading, the assistant will say live web information was not available.

The model is also told that web search is an external Python tool in this local project. It should not claim that it cannot search the web when sources have been provided by the program.

## How Memory Works

Ollama's `/api/generate` endpoint does not automatically remember previous messages from this Python program.

This project uses two kinds of memory.

Short-term memory is a simple list of recent conversation turns in `main.py`.

Before each request, `model/qwen_model.py` adds that history to the prompt so the model can answer follow-up questions.

Short-term memory lasts only while the program is running. If you close the program, this recent chat list is cleared.

Long-term memory is stored in:

```text
memory/memory.sqlite
```

The program saves successful chat turns and extracts durable facts, preferences, and instructions. Before each new answer, it searches this database for relevant memories and sends them to the model.

Durable memories are weighted. Each durable memory has:

```text
topic
importance
confidence
use_count
last_used_at
```

Memory ranking uses:

```text
keyword relevance
+ topic match
+ importance
+ confidence
+ use count bonus
- age decay
```

This helps the assistant prefer high-value memories and avoid stuffing unrelated old chat history into every answer.

Examples of things that can become long-term memory:

```text
Remember that I prefer optimal solutions.
以后不用太顾及难度，以最优解来。
My name is Alex.
```

This does not retrain Qwen's model weights. It is retrieval memory: the program saves useful information locally and provides relevant parts to Qwen when needed.

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
