# Local Qwen Chat Assistant

This is a beginner-friendly Python project for chatting with a local AI model in the terminal.

You type a message with your keyboard, the program sends it to Ollama, and the AI response is printed back in the terminal.

The project uses the local Ollama model:

```text
qwen3:14b
```

## Project Files

```text
qwen_chat/
├── main.py
├── requirements.txt
└── README.md
```

### main.py

This is the main Python program.

It does these things:

- shows a welcome message
- asks you to type a message
- sends your message to Ollama
- uses the model `qwen3:14b`
- prints the AI response in the terminal
- keeps chatting until you type `exit`, `quit`, or `q`
- shows friendly error messages if Ollama is not running or the model is not available

The model name is stored near the top of the file:

```python
MODEL_NAME = "qwen3:14b"
```

If you want to use a different Ollama model later, change that value.

### requirements.txt

This file lists the Python package needed by the project.

The project uses:

```text
requests
```

The `requests` package lets Python call Ollama's local HTTP API.

### README.md

This file explains what the project does, how the files work, and how to run the program.

## Requirements

Before running this project, you need:

- Python installed
- Ollama installed
- the Qwen3 14B model downloaded in Ollama

## Setup

Open a terminal in the project folder.

Install the Python dependency:

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

You should see a welcome message.

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

## How It Works

The Python program sends a request to this local Ollama API endpoint:

```text
http://localhost:11434/api/generate
```

It sends data like this:

```python
{
    "model": "qwen3:14b",
    "prompt": "your message here",
    "stream": False
}
```

The setting `stream=False` keeps the code simple because Ollama returns one complete response.

## Common Problems

### Ollama is not running

If Ollama is not running, the program will show a connection error.

Start Ollama and try again.

### The model is not installed

If the model is missing, run:

```bash
ollama pull qwen3:14b
```

### The first response is slow

Large local models can take time to load, especially the first time.

If the request times out, wait a moment and try again.

## What This Project Does Not Include Yet

This project is intentionally simple.

It does not include:

- voice input
- text-to-speech
- a graphical interface
- screen capture
- computer control
- complicated project architecture

