import os
import shutil
import threading
import logging
import time
import gc
from dotenv import load_dotenv
import gradio as gr
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
import chromadb
from chromadb.config import Settings as ChromaSettings
from constant import CHROMA_SETTINGS

# -------------------- Logging Setup --------------------
logging.basicConfig(
    filename='chatbot.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# -------------------- Global Lock --------------------
rebuild_lock = threading.Lock()

# -------------------- Load Environment --------------------
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError("❌ GROQ_API_KEY not found in .env file")

# -------------------- Chroma Helper Functions --------------------
def create_chroma_client(persist_dir):
    return chromadb.PersistentClient(
        path=persist_dir,
        settings=ChromaSettings(anonymized_telemetry=False)
    )

def verify_db(persist_dir, embeddings, collection_name="company_docs"):
    client = create_chroma_client(persist_dir)
    db = Chroma(client=client, collection_name=collection_name, embedding_function=embeddings)
    count = db._collection.count()
    if count == 0:
        raise ValueError("Database exists but collection is empty")
    return db

def get_or_build_db():
    """Thread-safe DB retrieval or rebuild."""
    embeddings = HuggingFaceEmbeddings(
        model_name="BAAI/bge-base-en-v1.5",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True}
    )
    persist_dir = CHROMA_SETTINGS.persist_directory
    os.makedirs(persist_dir, exist_ok=True)

    with rebuild_lock:
        try:
            return verify_db(persist_dir, embeddings)
        except Exception as e:
            logging.warning(f"DB missing or corrupted: {e}. Rebuilding...")
            if os.path.exists(persist_dir):
                shutil.rmtree(persist_dir, ignore_errors=True)
                time.sleep(1)
            # Delayed import to avoid circular import
            from ingest import ingest_documents
            ingest_documents()
            gc.collect()
            time.sleep(1)
            return verify_db(persist_dir, embeddings)

# -------------------- Load LLM --------------------
def load_llm():
    return ChatGroq(
        groq_api_key=GROQ_API_KEY,
        model_name="llama-3.1-8b-instant",
        temperature=0.4
    )

# -------------------- Prompt Builder --------------------
def build_prompt(context, chat_history, question):
    template = """
You are Wasla's AI assistant — professional, friendly, and knowledgeable about our company.

Guidelines:
- Speak as Wasla, using "we" and "us". Never refer to yourself as a chatbot.
- Answer using ONLY the provided context.
- If the answer is not in the context, say: "I'm sorry, I couldn't find that information in our documents."
- Be natural, conversational, and concise.
- If the user asks a yes/no question, first answer clearly (yes/no), then provide relevant info.
- Do NOT mention internal processes like retrieval, vector databases, or "according to my training".
- Keep responses aligned with Wasla's tone: quietly powerful, precise, focused on long-term solutions.

Context:
{context}

Chat History:
{chat_history}

User Question:
{question}
"""
    return ChatPromptTemplate.from_template(template).format(
        context=context, chat_history=chat_history, question=question
    )

# -------------------- Document Retrieval --------------------
def retrieve_docs(db, query):
    retriever = db.as_retriever(
        search_type="mmr",
        search_kwargs={"k": 6, "fetch_k": 20, "lambda_mult": 0.5}
    )
    try:
        return retriever.invoke(query)
    except Exception as e:
        logging.error(f"Database query error '{query}': {e}")
        return []

def format_context(docs):
    context_parts = []
    for doc in docs:
        source = doc.metadata.get("source_file", "Unknown")
        content = doc.page_content[:1000]
        context_parts.append(f"[{source}]\n{content}")
    return "\n\n".join(context_parts)

def log_unanswered(question, answer):
    if "I couldn't find that information" in answer:
        logging.info(f"UNANSWERED: {question}")

# -------------------- Gradio Chat Function --------------------
# Keep a session chat history
chat_history_global = []

def chatbot_response(user_input, debug=False, feedback=None):
    """Main function called by Gradio for each user input."""
    global chat_history_global
    chat_history_global.append({"role": "user", "content": user_input})

    try:
        db = get_or_build_db()
        llm = load_llm()

        docs = retrieve_docs(db, user_input)
        if debug:
            retrieved_count = len(docs)
        else:
            retrieved_count = None

        context = format_context(docs)
        history_text = "\n".join(
            f"{'User' if m['role']=='user' else 'Assistant'}: {m['content']}"
            for m in chat_history_global[-6:]
        )

        final_prompt = build_prompt(context, history_text, user_input)

        try:
            response = llm.invoke(final_prompt)
            answer = response.content
        except Exception as e:
            answer = "😓 Sorry, the AI service is unavailable right now."
            logging.error(f"LLM invocation failed: {e}")

        log_unanswered(user_input, answer)
        chat_history_global.append({"role": "assistant", "content": answer})

        return chat_history_global, retrieved_count

    except Exception as e:
        logging.error(f"Unhandled exception: {e}", exc_info=True)
        return chat_history_global, None

# -------------------- Gradio Interface --------------------
with gr.Blocks() as demo:
    gr.Markdown("## 🤖 Wasla AI Assistant")

    with gr.Row():
        chatbox = gr.Chatbot(elem_id="chatbot")
        debug_checkbox = gr.Checkbox(label="Show debug info", value=False)

    user_input = gr.Textbox(label="Ask something about Wasla...", placeholder="Type your question here...")
    submit_btn = gr.Button("Send")

    submit_btn.click(
        chatbot_response,
        inputs=[user_input, debug_checkbox, None],
        outputs=[chatbox, gr.Number()],
    )

demo.launch()
