# Knowledge Agent

AI-powered GitHub Repository Assistant using:

* FastAPI
* Streamlit
* LangChain
* Groq
* MCP (Model Context Protocol)
* GitHub MCP Server
* ChromaDB (RAG Memory)

---

# Project Overview

Knowledge Agent is a modern AI engineering project that can:

* Analyze GitHub repositories
* Understand project architecture
* Explain frontend/backend structure
* Use MCP tools to interact with GitHub
* Store previous conversations using ChromaDB
* Retrieve contextual memory using RAG

This project is designed for learning:

* AI Agents
* LangChain
* MCP
* RAG
* Vector Databases
* FastAPI
* Full-stack AI applications

---

# Architecture

```text
Frontend (Streamlit)
        ↓
FastAPI Backend
        ↓
LangChain Agent
        ↓
Groq LLM
        ↓
GitHub MCP Tools
        ↓
ChromaDB Memory
```

---

# Features

## AI Agent

* LangChain 1.x agent architecture
* Tool-calling support
* Async execution
* Prompt-based reasoning

## GitHub MCP Integration

* Repository analysis
* File exploration
* Code understanding
* Architecture explanation

## RAG Memory (ChromaDB)

* Stores previous questions and answers
* Semantic memory retrieval
* Persistent vector database
* Embedding-based search

## Frontend

* Streamlit UI
* Real-time interaction
* Backend API integration

## Backend

* FastAPI server
* Async API routes
* Agent orchestration
* Memory handling

---

# Project Structure

```text
KnowledgeAgent/
│
├── backend/
│   │
│   ├── app/
│   │   │
│   │   ├── main.py
│   │   │
│   │   ├── agent/
│   │   │   ├── agent.py
│   │   │   ├── config.py
│   │   │   ├── mcp_servers.py
│   │   │   ├── prompts.py
│   │   │   ├── rag_chain.py
│   │   │   └── vector_store.py
│   │   │
│   │   └── memory/
│   │       └── rag_memory.py
│   │
│   ├── chroma_db/
│   │
│   ├── .env
│   ├── requirements.txt
│   └── venv/
│
└── frontend/
    │
    ├── app.py
    ├── .env
    ├── requirements.txt
    └── venv/
```

---

# Backend Setup

## 1. Create Virtual Environment

```bash
python -m venv venv
```

## 2. Activate Environment

### Windows

```bash
venv\Scripts\activate
```

---

# Install Dependencies

```bash
pip install -r requirements.txt
```

---

# Backend .env

Create:

```text
backend/.env
```

Add:

```env
GROQ_API_KEY=your_groq_api_key

GITHUB_TOKEN=your_github_token

GITHUB_OWNER=your_github_username

GITHUB_REPO=your_repository_name
```

---

# Frontend Setup

## Install Dependencies

```bash
pip install -r requirements.txt
```

---

# Frontend .env

Create:

```text
frontend/.env
```

Add:

```env
BACKEND_URL=http://127.0.0.1:8000/chat
```

---

# Run Backend

Inside backend folder:

```bash
uvicorn app.main:app --reload
```

Backend runs on:

```text
http://127.0.0.1:8000
```

Swagger Docs:

```text
http://127.0.0.1:8000/docs
```

---

# Run Frontend

Inside frontend folder:

```bash
streamlit run app.py
```

---

# Example Questions

```text
Explain frontend and backend architecture
```

```text
What technologies are used in this repository?
```

```text
Analyze the authentication flow
```

```text
Explain the API structure
```

---

# MCP Integration

This project uses:

```text
@modelcontextprotocol/server-github
```

The agent uses GitHub MCP tools to:

* Read repositories
* Analyze files
* Search project structure
* Understand architecture

---

# ChromaDB Memory

The project stores:

* Previous questions
* AI responses
* Embeddings

This enables:

* Semantic retrieval
* Context-aware conversations
* Persistent memory

---

# Tech Stack

| Technology            | Purpose          |
| --------------------- | ---------------- |
| FastAPI               | Backend API      |
| Streamlit             | Frontend         |
| LangChain             | AI orchestration |
| Groq                  | LLM inference    |
| MCP                   | Tool integration |
| GitHub MCP Server     | Repository tools |
| ChromaDB              | Vector database  |
| Sentence Transformers | Embeddings       |

---

# Future Improvements

* Full RAG retrieval pipeline
* Notion MCP integration
* Multi-repository support
* Chat history UI
* Streaming responses
* File-level repository analysis
* Autonomous repository reasoning

---

# Learning Goals

This project helps understand:

* AI Agents
* LangChain
* MCP Architecture
* RAG Pipelines
* Vector Databases
* Embeddings
* Full-stack AI systems
* Tool Calling
* AI Memory Systems

---

# License

MIT License
