# Local Qwen Chat Assistant

This is a beginner-friendly Python project for chatting with a local Qwen3 14B model through Ollama.

You type text in the terminal. The program sends your message to Ollama, streams the AI response back to the terminal, and opens a small GPU and memory monitor window.

## Project Structure

```text
Artificial_Interactive_Intelligence_MAY/
|-- main.py
|-- requirements.txt
|-- README.md
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
- exits when you type `exit`, `quit`, or `q`
- closes the monitor window when the chat program exits

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
