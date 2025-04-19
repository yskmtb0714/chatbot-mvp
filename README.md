# AI Chatbot MVP (Vue + Flask + Gemini)

## Overview

This is a Minimum Viable Product (MVP) of a web-based chatbot application built as a portfolio project. It demonstrates practical integration between a modern frontend (Vue.js 3 with Vite) and a Python/Flask backend powered by the Google Gemini Generative AI API (`gemini-1.5-flash-latest`).

The chatbot is designed to handle various user intents within a simulated e-commerce support context, including:
* Answering Frequently Asked Questions (FAQs) based on exact matches.
* Providing product information using a basic **Retrieval-Augmented Generation (RAG)** approach.
* Checking order status using **Function Calling** (interacting with dummy data).
* Engaging in general conversation for unhandled intents.

## Features

* **Conversational Interface:** Simple chat UI built with Vue.js, displaying conversation history with alternating user/AI messages. Includes basic loading and error indicators.
* **Intent Detection:** Backend logic (`detect_intent` function) classifies user input into predefined categories (FAQ, Product Info, Order Status, General Chat) using keywords and simple patterns.
* **FAQ Handling:** Provides predefined answers for exact-match FAQ queries stored in the backend.
* **Product Information (Basic RAG):**
    * Retrieves relevant product details (name, price, description) from an external JSON file (`products.json`) based on keywords or product names in the user query (`retrieve_product_info` function).
    * Augments a prompt with the retrieved context.
    * Uses the Gemini API to generate a natural language description based *only* on the provided context.
* **Order Status Check (Function Calling):**
    * Defines a function schema (`get_order_info`) for the Gemini API.
    * When order status intent is detected, sends the query and schema to Gemini.
    * If Gemini requests the `get_order_info` function call, the backend extracts the `order_id` argument identified by the AI.
    * Executes the *local* `get_order_info` function (querying dummy order data).
    * Sends the function execution result back to the Gemini API.
    * Gemini generates the final natural language response based on the order status retrieved.
* **General Conversation:** Falls back to the standard Gemini API generation for queries that don't match other intents.

## Tech Stack

* **Frontend:** Vue.js (v3), Vite, Axios, CSS
* **Backend:** Python (v3.11+ recommended), Flask, `google-generativeai` (v0.8.5 used), `python-dotenv`
* **AI Model:** Google Gemini API (`gemini-1.5-flash-latest` model)
* **Data Storage:** JSON (`products.json`), Python Dict/List (`faq_database`, `order_database` in `data_store.py` - Dummy Data)
* **Development:** Git, GitHub, Virtual Environment (`.venv`), pip, npm

## Key Implementations & Learnings

This project served as valuable practice in integrating a powerful LLM into a full-stack application and implementing modern AI interaction patterns.

### Basic RAG for Product Info

A simple RAG pipeline was implemented to provide grounded answers about products:
1.  Product data was externalized to `products.json`.
2.  A keyword/name matching function (`retrieve_product_info`) acts as the retriever, fetching relevant text snippets.
3.  The prompt sent to Gemini is dynamically augmented with this retrieved context, instructing the model to answer based solely on the provided information. This helps reduce hallucination and ensures answers are based on the available "knowledge base".

### Function Calling for Order Status

Basic Function Calling allows the AI to utilize "tools":
1.  An OpenAPI-like schema was defined for the `get_order_info` function (which accesses dummy data).
2.  This schema is passed to the Gemini API via the `tools` parameter when an order status intent is detected.
3.  The backend handles the multi-turn conversation:
    * Initial request potentially yields a `function_call` from the AI.
    * The backend parses the call, executes the corresponding local function (`get_order_info`).
    * The function's result is sent back to the AI using the expected `function_response` format within the conversation history.
    * The AI generates the final user-facing response based on the tool's output.
    This demonstrates how LLMs can be given agency to interact with external data sources or perform actions.

### Challenges & Learnings

* Setting up the development environment (Python venv, Node.js, dependencies, API keys).
* Handling CORS issues between the frontend and backend servers.
* Debugging Python (`NameError`, `IndentationError`, `ImportError`) and JavaScript errors.
* Implementing basic intent detection logic.
* Refactoring backend code for better structure (separating data access logic into `data_store.py`).
* Understanding and debugging the precise schema and data structures required for Gemini API's Function Calling feature.
* Iterative prompt engineering to improve AI response quality for product descriptions (RAG).

## Setup and Usage (Local)

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/yskmtb0714/chatbot-mvp.git](https://github.com/yskmtb0714/chatbot-mvp.git)
    cd chatbot-mvp
    ```
2.  **Backend Setup:**
    * Navigate to the backend directory: `cd backend`
    * Create a Python virtual environment: `python -m venv .venv`
    * Activate the virtual environment:
        * Windows (PowerShell): `.\.venv\Scripts\Activate.ps1`
        * macOS/Linux: `source .venv/bin/activate`
    * Install dependencies:
        ```bash
        pip install -r requirements.txt 
        ```
        *(If `requirements.txt` is missing, run `pip install Flask python-dotenv google-generativeai flask-cors`)*
    * Create a `.env` file in the `backend` directory.
    * Add your Google Gemini API key to the `.env` file:
        ```
        GEMINI_API_KEY='YOUR_API_KEY_HERE'
        ```
3.  **Frontend Setup:**
    * Navigate to the frontend directory: `cd ../frontend` (from backend) or `cd frontend` (from root)
    * Install dependencies:
        ```bash
        npm install
        ```
4.  **Run the Application:**
    * Open **two separate terminals**.
    * **Terminal 1 (Backend):** Navigate to `backend`, activate venv, run: `python app.py`
    * **Terminal 2 (Frontend):** Navigate to `frontend`, run: `npm run dev`
5.  **Access:**
    * Open the `Local:` URL provided by the frontend server (e.g., `http://localhost:5173/`) in your web browser.

## Future Work (Optional)

* Enhance RAG with vector search (using embeddings and a vector database like ChromaDB or FAISS) for more semantic product/FAQ retrieval.
* Implement actual database connections instead of dummy data/JSON.
* Expand Function Calling capabilities (e.g., allow searching products via function call).
* Improve frontend UI/UX further (message streaming, better error handling, etc.).
* Add user authentication.
* Deploy the application to a cloud platform (e.g., Google Cloud Run, Vercel, Netlify).