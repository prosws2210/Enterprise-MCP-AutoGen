# Enterprise-MCP-AutoGen: AI Personal Operating System (AI-POS)

An enterprise-grade Agentic AI platform that acts as a user's digital chief of staff. 

## What Has Been Built So Far (Current State)

### 1. Futuristic Frontend (Next.js)
A stunning, responsive web interface built using **Next.js 15** and **React**.
- **Glassmorphism UI:** Implemented a dark-mode first design utilizing deep blacks (`#0a0a0a`), sleek glassmorphic container cards with blurred backgrounds, and gradient glowing borders.
- **Micro-animations:** Integrated `framer-motion` for fluid page transitions, spring-animated chat bubbles, and dynamic typing indicators.
- **Modern Typography & Icons:** Utilizes the Inter font and dynamic SVG icons powered by `lucide-react`.
- **Development Server:** Currently running directly on the host using `npm run dev`.

### 2. Robust Backend (FastAPI)
A high-performance Python backend built with **FastAPI**.
- **REST APIs:** Exposes endpoints to communicate with the frontend and process Agent tasks.
- **SQLAlchemy ORM:** Integrated with a database schema ready for storing users, chat history, and vector embeddings.
- **CORS Configured:** Securely linked with the Next.js local development server for seamless API requests.

### 3. Database Infrastructure (PostgreSQL + pgvector)
A local, containerized database environment optimized for AI workflows.
- **Vector Search Ready:** Bootstrapped PostgreSQL with the `pgvector` extension dynamically enabled on startup to allow storing dense vectors (e.g., embeddings) up to 1536 dimensions.
- **Data Persistence:** Uses Docker volumes (`pgdata`) to ensure chat history and knowledge bases survive container restarts.

### 4. Container Orchestration (Docker Compose)
Fully dockerized backend architecture for easy deployment and scaling.
- **Unified Stack:** A central `docker-compose.yml` that seamlessly boots both the FastAPI backend and PostgreSQL database, connecting them through an internal Docker network.
- **Environment Isolation:** Python dependencies are tightly controlled and automatically installed during the image build process.

## Upcoming Implementations

- **AutoGen 0.4 Migration:** Integrating the modern `autogen-agentchat` and `autogen-ext` APIs into the backend.
- **MCP Integrations:** Hooking up the Model Context Protocol (MCP) servers (Notion, GitHub, Calendar) directly into the AutoGen Agents using `StdioServerParams`.
- **LLM Connectivity:** Attaching Groq API (Llama 3 models) and local LLMs to process the agentic workflows.
