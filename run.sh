#!/usr/bin/env bash
# Start backend + UI (needs: pip install -r requirements.txt, ollama running with llama3:8b)
export LLM_BACKEND=${LLM_BACKEND:-ollama}
uvicorn app.api:app --port 8000 &
sleep 2
streamlit run ui/streamlit_app.py
