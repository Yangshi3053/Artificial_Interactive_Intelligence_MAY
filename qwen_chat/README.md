# Local Qwen Chat Assistant

This is a beginner-friendly Python project for chatting with a local AI model in the terminal.

You type a message with your keyboard, the program sends it to Ollama, and the AI response is printed back in the terminal.

The project also includes a small popup monitor window that shows GPU and memory usage while the model is running.

The default local Ollama model is:

```text
qwen3:14b
```

## Project Files

```text
qwen_chat/
|-- main.py
|-- monitor.py
|-- requirements.txt
`-- README.md
```

### main.py

This is the main chat program.

It does these things:

- shows a welcome message
- opens the GPU and memory monitor popup
- asks you to type a message
- sends your message to Ollama
- uses the model `qwen3:14b`
- keeps recent conversation history so follow-up questions work better
- prints the AI response in the terminal while it is being generated
- keeps chatting until you type `exit`, `quit`, or `q`
- shows friendly error messages if Ollama is not running or the model is not available

The model name is stored near the top of the file:

```python
MODEL_NAME = "qwen3:14b"
```

If you want to use a different Ollama model later, change that value.

Long answers are controlled by this value:

```python
MAX_RESPONSE_TOKENS = 4096
```

Higher numbers allow longer answers. Lower numbers make answers stop sooner.

The amount of recent chat history is controlled by this value:

```python
MAX_HISTORY_CHARACTERS = 12000
```

This helps the assistant remember recent messages without making every request too large.

### monitor.py

This is the resource monitor popup program.

It opens a window and checks your computer once every second.

It draws three lines over time:

- red line: GPU usage
- blue line: GPU memory usage
- green line: normal system RAM usage

The monitor uses:

- `tkinter` to create the popup window
- `psutil` to read system RAM usage
- `nvidia-ml-py` to read NVIDIA GPU usage

You can run this monitor by itself:

```bash
python monitor.py
```

When you run `main.py`, the monitor opens automatically.

### requirements.txt

This file lists the Python packages needed by the project.

The project uses:

```text
requests
psutil
nvidia-ml-py
```

`requests` lets Python call Ollama's local HTTP API.

`psutil` reads your computer's memory usage.

`nvidia-ml-py` reads NVIDIA GPU usage and GPU memory usage.

### README.md

This file explains what the project does, how the files work, and how to run the program.

## Requirements

Before running this project, you need:

- Python installed
- Ollama installed
- an NVIDIA GPU if you want GPU usage monitoring
- the Qwen3 14B model downloaded in Ollama

## Setup

Open a terminal in the `qwen_chat` folder.

Install the Python dependencies:

```bash
pip install -r requirements.txt
```

Download the Qwen3 14B model with Ollama:

```bash
ollama pull qwen3:14b
```

Make sure Ollama is running.

You can test Ollama with:

```bash
ollama list
```

## Run the Chat Assistant

From inside the `qwen_chat` folder, run:

```bash
python main.py
```

You should see:

- a welcome message in the terminal
- a popup window showing GPU and memory usage

Then type a message, for example:

```text
Hello, who are you?
```

The assistant will send your message to Ollama and print the response.

## Exit the Program

To stop chatting, type one of these:

```text
exit
quit
q
```

You can close the monitor window by clicking the window close button.

When you exit the chat program by typing `exit`, `quit`, or `q`, the monitor window also closes automatically.

## How the Chat Works

The Python program sends a request to this local Ollama API endpoint:

```text
http://localhost:11434/api/generate
```

It sends data like this:

```python
{
    "model": "qwen3:14b",
    "prompt": "your message here",
    "stream": True,
    "options": {
        "num_predict": 4096
    }
}
```

The setting `stream=True` lets the program print text while the model is still generating.

This makes long answers feel much faster because you do not have to wait for the whole answer to finish before seeing anything.

The `num_predict` option allows longer answers. It does not force the model to write for an exact number of seconds, but it helps prevent long writing tasks from stopping too early.

## How Conversation Memory Works

The Ollama `/api/generate` endpoint does not automatically remember earlier messages from this Python program.

To make follow-up questions work, `main.py` stores recent messages in a simple Python list.

Before sending your new message to Ollama, the program adds the recent conversation history to the prompt.

This means you can ask things like:

```text
Summarize what you wrote before.
```

The assistant will have the recent text available.

Long histories can make the model slower, so the project keeps only the most recent part of the conversation.

## How the Monitor Works

The monitor checks your computer every second.

It stores the latest 120 seconds of data and redraws the chart.

The chart uses percentages from 0 to 100, so GPU usage, GPU memory, and system RAM can be shown together.

## Common Problems

### Ollama is not running

If Ollama is not running, the chat program will show a connection error.

Start Ollama and try again.

### The model is not installed

If the model is missing, run:

```bash
ollama pull qwen3:14b
```

### The monitor does not show GPU data

The GPU monitor needs an NVIDIA GPU and the `nvidia-ml-py` package.

Install the packages again:

```bash
pip install -r requirements.txt
```

### The first response is slow

Large local models can take time to load, especially the first time.

If the request times out, wait a moment and try again.

## What This Project Does Not Include Yet

This project is intentionally simple.

It does not include:

- voice input
- text-to-speech
- a graphical interface for chatting
- screen capture
- computer control
- complicated project architecture
