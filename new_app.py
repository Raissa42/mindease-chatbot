import streamlit as st
import google.generativeai as genai
import os

# ════════════════════════════════════════════════════════
# CONFIGURATION  (hidden from UI — black box)
# ════════════════════════════════════════════════════════
# API key is read from environment variable (set in Streamlit Cloud secrets)
# For local testing, you can temporarily hardcode: API_KEY = ""
API_KEY = os.environ.get("GEMINI_API_KEY", "")   # ← set this in deployment secrets

# Fixed model parameters — not exposed to users
TEMPERATURE   = 0.8
TOP_P         = 0.9
MAX_TOKENS    = 400
MODEL_NAME    = "gemini-2.5-flash"

# ════════════════════════════════════════════════════════
# PAGE CONFIG
# ════════════════════════════════════════════════════════
st.set_page_config(
    page_title="MindEase – Student Support",
    page_icon="🧠",
    layout="centered"
)

# ════════════════════════════════════════════════════════
# STYLING
# ════════════════════════════════════════════════════════
st.markdown("""
<style>
    /* ── Base ── */
    html, body, [class*="css"] {
        font-family: 'Segoe UI', Arial, sans-serif;
        background-color: #0f1117;
        color: #e8eaf0;
    }

    /* ── Header ── */
    .mindease-header {
        text-align: center;
        padding: 1.5rem 0 0.5rem 0;
    }
    .mindease-header h1 {
        font-size: 2.4rem;
        font-weight: 800;
        background: linear-gradient(135deg, #a78bfa, #60a5fa);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
    }
    .mindease-header p {
        color: #9ca3af;
        font-size: 0.95rem;
        margin-top: 0.3rem;
    }

    /* ── Disclaimer ── */
    .disclaimer {
        background: rgba(239,68,68,0.08);
        border: 1px solid rgba(239,68,68,0.3);
        border-radius: 10px;
        padding: 0.65rem 1rem;
        font-size: 0.82rem;
        color: #fca5a5;
        text-align: center;
        margin: 0.8rem 0 1rem 0;
    }

    /* ── Language bar ── */
    .lang-label {
        font-size: 0.82rem;
        color: #9ca3af;
        margin-bottom: 0.3rem;
    }

    /* ── Suggestion buttons ── */
    .stButton > button {
        background: rgba(99,102,241,0.12) !important;
        border: 1px solid rgba(99,102,241,0.35) !important;
        border-radius: 20px !important;
        color: #c4b5fd !important;
        font-size: 0.85rem !important;
        padding: 0.4rem 0.9rem !important;
        transition: all 0.2s !important;
        width: 100% !important;
    }
    .stButton > button:hover {
        background: rgba(99,102,241,0.28) !important;
        border-color: #818cf8 !important;
        color: white !important;
    }

    /* ── Chat messages ── */
    [data-testid="stChatMessage"] {
        border-radius: 14px !important;
        padding: 0.6rem 0.8rem !important;
    }

    /* ── Divider ── */
    hr { border-color: #2d3148; }

    /* ── Sidebar clean-up ── */
    section[data-testid="stSidebar"] { display: none !important; }
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════
# LANGUAGE CONFIGURATION
# ════════════════════════════════════════════════════════
LANGUAGES = {
    "🇬🇧  English":   "English",
    "🇮🇳  Hindi":     "Hindi",
    "🇲🇳  Mongolian": "Mongolian",
    "🇫🇷  Français":  "French",     # ✅ ADDED
    "🇲🇬  Malagasy":  "Malagasy"
}

LANGUAGE_PROMPTS = {
    "English":   "Always respond in English.",
    "Hindi":     "Always respond in Hindi (use Devanagari script). You may mix in simple English words when needed.",
    "Mongolian": "Always respond in Mongolian (use Cyrillic script). You may mix in simple English words when needed.",
    "French":   "Always respond in French. Use natural, conversational French.",
}

# Starter prompts per language
STARTERS = {
    "English": [
        "I failed my exam 😞",
        "I can't focus while studying",
        "I'm scared of placements",
        "I feel very lonely in hostel",
    ],
    "Hindi": [
        "मैं परीक्षा में फेल हो गया 😞",
        "मैं पढ़ाई में ध्यान नहीं लगा पा रहा",
        "प्लेसमेंट से बहुत डर लग रहा है",
        "हॉस्टल में बहुत अकेलापन महसूस होता है",
    ],
    "Mongolian": [
        "Би шалгалтандаа тэнцсэнгүй 😞",
        "Би суралцахдаа төвлөрч чадахгүй байна",
        "Би ажлын байрны ярилцлагаас айж байна",
        "Би дотуур байранд маш ганцаардаж байна",
    ],
    "French": [
        "J'ai échoué à mon examen 😞",
        "Je n'arrive pas à me concentrer en étudiant",
        "J'ai peur des placements",
        "Je me sens très seul à l'internat",
    ],
}

# ════════════════════════════════════════════════════════
# SYSTEM PROMPT BUILDER
# ════════════════════════════════════════════════════════
def build_system_prompt(language: str) -> str:
    lang_instruction = LANGUAGE_PROMPTS[language]
    return f"""
You are MindEase, a compassionate academic counselor for Indian BTech students.

Language rule (HIGHEST PRIORITY): {lang_instruction}

Your role:
- Support students dealing with exam stress, anxiety, backlogs, burnout, and loneliness
- Give practical study tips, time management strategies, and motivation
- Be warm, friendly, and encouraging — like a helpful senior student
- Keep responses short and clear (3–5 sentences)

Domain knowledge you have:
- Indian engineering education: semester exams, KTs/backlogs, CGPA, viva, lab submissions
- Placement pressure, internship anxiety, parental expectations
- Hostel life, peer pressure, financial stress

Hard rules:
- NEVER diagnose any mental or medical condition
- NEVER give harmful or dangerous advice
- If a student mentions self-harm or suicide: immediately and kindly share
  iCall helpline (9152987821) and Vandrevala Foundation (1860-2662-345)
  and gently encourage them to reach out
"""

# ════════════════════════════════════════════════════════
# GEMINI API CALL
# ════════════════════════════════════════════════════════
def get_response(user_message: str, history: list, language: str) -> str:
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel(
        model_name=MODEL_NAME,
        system_instruction=build_system_prompt(language),
        generation_config=genai.GenerationConfig(
            temperature=TEMPERATURE,
            top_p=TOP_P,
            max_output_tokens=MAX_TOKENS,
        )
    )
    chat = model.start_chat(history=history)
    response = chat.send_message(user_message)
    return response.text

# ════════════════════════════════════════════════════════
# SESSION STATE INIT
# ════════════════════════════════════════════════════════
if "messages"       not in st.session_state:
    st.session_state.messages       = []
if "language"       not in st.session_state:
    st.session_state.language       = "English"
if "pending_input"  not in st.session_state:
    st.session_state.pending_input  = None   # stores suggestion button clicks

# ════════════════════════════════════════════════════════
# HEADER
# ════════════════════════════════════════════════════════
st.markdown("""
<div class="mindease-header">
    <h1>🧠 MindEase</h1>
    <p>Your safe space for academic stress & student wellbeing support</p>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="disclaimer">
    ⚠️ For serious mental health concerns call
    <strong>iCall: 9152987821</strong> or
    <strong>Vandrevala Foundation: 1860-2662-345</strong>
</div>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════
# LANGUAGE SELECTOR  (top of page, visible to user)
# ════════════════════════════════════════════════════════
st.markdown('<p class="lang-label">🌐 Select Language / भाषा चुनें / Хэл сонгоно уу / Choisir la langue</p>', unsafe_allow_html=True)

lang_col, _ = st.columns([2, 3])
with lang_col:
    selected_label = st.selectbox(
        label="language_select",
        options=list(LANGUAGES.keys()),
        index=0,
        label_visibility="collapsed"
    )

new_language = LANGUAGES[selected_label]

# Reset chat when language changes
if new_language != st.session_state.language:
    st.session_state.language      = new_language
    st.session_state.messages      = []
    st.session_state.pending_input = None

language = st.session_state.language

st.divider()

# ════════════════════════════════════════════════════════
# DISPLAY CHAT HISTORY
# ════════════════════════════════════════════════════════
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# ════════════════════════════════════════════════════════
# SUGGESTION BUTTONS  (only when chat is empty)
# ════════════════════════════════════════════════════════
if len(st.session_state.messages) == 0 and st.session_state.pending_input is None:
    st.markdown("#### 💬 Try one of these:")
    col1, col2 = st.columns(2)
    starters = STARTERS[language]
    for i, prompt in enumerate(starters):
        col = col1 if i % 2 == 0 else col2
        with col:
            if st.button(prompt, key=f"starter_{i}"):
                # ✅ FIX: store as pending — will be processed below
                st.session_state.pending_input = prompt
                st.rerun()

# ════════════════════════════════════════════════════════
# PROCESS PENDING INPUT (from suggestion buttons)
# ════════════════════════════════════════════════════════
if st.session_state.pending_input is not None:
    user_msg = st.session_state.pending_input
    st.session_state.pending_input = None   # clear immediately

    # Display user message
    with st.chat_message("user"):
        st.write(user_msg)
    st.session_state.messages.append({"role": "user", "content": user_msg})

    # Build history
    history = [
        {"role": "user" if m["role"] == "user" else "model", "parts": [m["content"]]}
        for m in st.session_state.messages[:-1]
    ]

    # Get and display response
    try:
        with st.chat_message("assistant"):
            with st.spinner("MindEase is thinking..."):
                reply = get_response(user_msg, history, language)
            st.write(reply)
        st.session_state.messages.append({"role": "assistant", "content": reply})
    except Exception as e:
        st.error(f"❌ Error: {e}")

# ════════════════════════════════════════════════════════
# CHAT INPUT  (manual typing)
# ════════════════════════════════════════════════════════
placeholders = {
    "English":   "Talk to MindEase... e.g. 'I'm very stressed about exams'",
    "Hindi":     "MindEase से बात करें... जैसे 'मुझे परीक्षा की बहुत चिंता है'",
    "Mongolian": "MindEase-тэй ярилцана уу...",
    "French": "Parlez à MindEase... ex: 'Je suis très stressé par les examens'",
        
}

user_input = st.chat_input(placeholders[language])

if user_input:
    if not API_KEY:
        st.error("❌ API key not configured. Please contact the administrator.")
        st.stop()

    # Display user message
    with st.chat_message("user"):
        st.write(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})

    # Build history (exclude latest)
    history = [
        {"role": "user" if m["role"] == "user" else "model", "parts": [m["content"]]}
        for m in st.session_state.messages[:-1]
    ]

    # Get and display response
    try:
        with st.chat_message("assistant"):
            with st.spinner("MindEase is thinking..."):
                reply = get_response(user_input, history, language)
            st.write(reply)
        st.session_state.messages.append({"role": "assistant", "content": reply})

    except Exception as e:
        err = str(e)
        if "API_KEY_INVALID" in err or "invalid" in err.lower():
            st.error("❌ Invalid API Key. Please check configuration.")
        elif "quota" in err.lower() or "429" in err:
            st.error("❌ Rate limit reached. Please wait a moment and try again.")
        elif "not found" in err.lower() or "404" in err:
            st.error("❌ Model not found. Please check model name in configuration.")
        else:
            st.error(f"❌ Unexpected error: {err}")
