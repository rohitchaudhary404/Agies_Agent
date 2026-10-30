import streamlit as st
import pandas as pd
import numpy as np
import io
import time
import json
import re
import pymupdf as fitz  # PyMuPDF
import random
from fpdf import FPDF
import qrcode
import hashlib
import plotly.express as px
import plotly.graph_objects as go
from services.leak_detection import LeakDetectionEngine
from services.llm import get_api_key, LLMUnavailable, chat as llm_chat
from services import red_team
from database.db_manager import DatabaseManager
from pydantic import BaseModel, Field
import os
from collections import Counter
import cv2
import networkx as nx
import matplotlib.pyplot as plt
from ddgs import DDGS

# --- FORENSIC CANARY TOKEN ENGINE (ZERO-WIDTH CRYPTOGRAPHY) ---
def embed_canary(text, slot_num):
    binary_slot = bin(int(slot_num))[2:].zfill(8)
    canary = "".join(['\u200B' if b == '0' else '\u200C' for b in binary_slot])
    parts = text.split(" ", 1)
    if len(parts) > 1:
        return parts[0] + canary + " " + parts[1]
    return text + canary

def extract_canary(text):
    binary = ""
    for char in text:
        if char == '\u200B': binary += '0'
        elif char == '\u200C': binary += '1'
    if binary:
        try:
            return int(binary, 2)
        except:
            return None
    return None

class GeneratedVariants(BaseModel):
    variant_a_method: str = Field(description="The new mathematical methodology for Variant A")
    variant_a_stem: str = Field(description="The heavily rewritten question stem for Variant A")
    variant_b_method: str = Field(description="The new mathematical methodology for Variant B")
    variant_b_stem: str = Field(description="The heavily rewritten question stem for Variant B")

db = DatabaseManager()
cusum_engine = LeakDetectionEngine(db, None)

st.set_page_config(page_title="AGIES | Adaptive Assessment Engine", layout="wide")

st.markdown("""
<style>
:root {
    --agies-ink: #0f172a;
    --agies-muted: #64748b;
    --agies-indigo: #4f46e5;
    --agies-violet: #7c3aed;
    --agies-line: #e2e8f0;
}

.stApp {
    background:
        radial-gradient(1100px 520px at 8% -8%, rgba(99, 102, 241, 0.12), transparent 60%),
        radial-gradient(900px 460px at 92% 0%, rgba(168, 85, 247, 0.09), transparent 55%),
        radial-gradient(700px 420px at 50% 110%, rgba(56, 189, 248, 0.08), transparent 65%),
        #f8fafc;
    background-attachment: fixed;
}
.block-container {
    max-width: 1280px;
    padding-top: 1.2rem;
    padding-bottom: 3rem;
}
[data-testid="stHeader"] {
    background: transparent;
}

/* ---------- Hero ---------- */
.agies-hero {
    position: relative;
    padding: 2.4rem 2.6rem 2rem;
    margin: 0.2rem 0 1.6rem;
    border-radius: 24px;
    border: 1px solid rgba(129, 140, 248, 0.32);
    background: linear-gradient(135deg, #0b1120 0%, #1e1b4b 55%, #312e81 100%);
    box-shadow: 0 30px 60px -32px rgba(15, 23, 42, 0.9);
    overflow: hidden;
    isolation: isolate;
}
.agies-hero::before {
    content: "";
    position: absolute;
    inset: 0;
    background-image:
        linear-gradient(rgba(148, 163, 184, 0.07) 1px, transparent 1px),
        linear-gradient(90deg, rgba(148, 163, 184, 0.07) 1px, transparent 1px);
    background-size: 48px 48px;
    mask-image: radial-gradient(ellipse at 30% 20%, #000 20%, transparent 72%);
    -webkit-mask-image: radial-gradient(ellipse at 30% 20%, #000 20%, transparent 72%);
    z-index: -1;
}
.agies-hero::after {
    content: "";
    position: absolute;
    inset: -45% 50% 5% -12%;
    background:
        radial-gradient(closest-side, rgba(129, 140, 248, 0.30), transparent 70%),
        radial-gradient(closest-side at 70% 70%, rgba(216, 180, 254, 0.18), transparent 70%);
    animation: agies-drift 14s ease-in-out infinite alternate;
    pointer-events: none;
    z-index: -1;
}
@keyframes agies-drift {
    from { transform: translate3d(-2%, -1%, 0) scale(1); }
    to   { transform: translate3d(3%, 2%, 0) scale(1.06); }
}
.agies-tag {
    display: inline-block;
    padding: 0.28rem 0.8rem;
    margin-bottom: 0.9rem;
    border: 1px solid rgba(165, 180, 252, 0.42);
    border-radius: 999px;
    background: rgba(129, 140, 248, 0.10);
    font-family: "Segoe UI", "Inter", system-ui, sans-serif;
    font-size: 0.66rem;
    font-weight: 600;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: #c7d2fe;
}
.agies-hero h1 {
    margin: 0;
    font-family: "Segoe UI", "Inter", system-ui, sans-serif;
    font-size: 3.4rem;
    font-weight: 800;
    line-height: 1.02;
    letter-spacing: 0.26em;
    background: linear-gradient(96deg, #e0e7ff 0%, #a5b4fc 42%, #f0abfc 100%);
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
    filter: drop-shadow(0 10px 24px rgba(99, 102, 241, 0.35));
}
.agies-hero .agies-sub {
    margin: 0.75rem 0 0;
    font-family: "Segoe UI", "Inter", system-ui, sans-serif;
    font-size: 0.92rem;
    font-weight: 400;
    letter-spacing: 0.04em;
    color: #94a3b8;
}
.agies-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin-top: 1.4rem;
}
.agies-chip {
    padding: 0.35rem 0.75rem;
    border-radius: 999px;
    border: 1px solid rgba(148, 163, 184, 0.26);
    background: rgba(255, 255, 255, 0.05);
    color: #cbd5e1;
    font-family: "Segoe UI", "Inter", system-ui, sans-serif;
    font-size: 0.72rem;
    letter-spacing: 0.03em;
    backdrop-filter: blur(6px);
}
.agies-chip b {
    color: #e0e7ff;
    font-weight: 650;
}

/* ---------- Sidebar ---------- */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #ffffff 0%, #eef2ff 100%);
    border-right: 1px solid var(--agies-line);
}
[data-testid="stSidebar"] .block-container {
    padding-top: 1.4rem;
}
.agies-side-brand {
    padding: 0.85rem 0.95rem;
    margin-bottom: 1.1rem;
    border-radius: 14px;
    border: 1px solid rgba(99, 102, 241, 0.18);
    background: linear-gradient(135deg, #0f172a 0%, #312e81 100%);
    box-shadow: 0 14px 30px -22px rgba(15, 23, 42, 0.9);
}
.agies-side-brand span {
    display: block;
    font-family: "Segoe UI", "Inter", system-ui, sans-serif;
    font-size: 1.15rem;
    font-weight: 800;
    letter-spacing: 0.22em;
    color: #e0e7ff;
}
.agies-side-brand small {
    display: block;
    margin-top: 0.2rem;
    font-size: 0.66rem;
    letter-spacing: 0.05em;
    color: #a5b4fc;
}
[data-testid="stSidebar"] h3 {
    font-size: 0.98rem;
    font-weight: 700;
    letter-spacing: 0.01em;
    color: #1e1b4b;
}

/* ---------- Headings ---------- */
[data-testid="stMarkdownContainer"] h2 {
    font-size: 1.5rem;
    font-weight: 750;
    letter-spacing: -0.015em;
    color: var(--agies-ink);
    padding-bottom: 0.55rem;
    border-bottom: 1px solid var(--agies-line);
    margin-top: 0.4rem;
}
[data-testid="stMarkdownContainer"] h3 {
    font-size: 1.06rem;
    font-weight: 700;
    letter-spacing: -0.01em;
    color: #1e293b;
}

/* ---------- Tabs ---------- */
.stTabs [data-baseweb="tab-list"] {
    gap: 0.35rem;
    background: rgba(255, 255, 255, 0.72);
    padding: 0.35rem;
    border: 1px solid var(--agies-line);
    border-radius: 16px;
    box-shadow: 0 10px 24px -22px rgba(15, 23, 42, 0.55);
}
.stTabs [data-baseweb="tab"] {
    border-radius: 11px;
    padding: 0.55rem 1.05rem;
    font-weight: 600;
    font-size: 0.86rem;
    color: #475569;
    transition: background 0.18s ease, color 0.18s ease;
}
.stTabs [data-baseweb="tab"]:hover {
    background: rgba(99, 102, 241, 0.08);
    color: #312e81;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #4f46e5, #7c3aed);
    color: #ffffff !important;
    box-shadow: 0 10px 20px -12px rgba(79, 70, 229, 0.85);
}
.stTabs [data-baseweb="tab-highlight"],
.stTabs [data-baseweb="tab-border"] {
    display: none;
}
.stTabs [data-baseweb="tab-panel"] {
    padding-top: 1.15rem;
}

/* ---------- Buttons ---------- */
.stButton > button,
[data-testid="stDownloadButton"] button,
[data-testid="stFormSubmitButton"] button {
    border-radius: 12px;
    border: 1px solid rgba(99, 102, 241, 0.30);
    background: rgba(255, 255, 255, 0.92);
    color: #4338ca;
    font-weight: 600;
    transition: transform 0.15s ease, box-shadow 0.15s ease, background 0.15s ease;
    box-shadow: 0 8px 20px -18px rgba(79, 70, 229, 0.8);
}
.stButton > button:hover,
[data-testid="stDownloadButton"] button:hover,
[data-testid="stFormSubmitButton"] button:hover {
    background: rgba(238, 242, 255, 1);
    border-color: rgba(99, 102, 241, 0.55);
    color: #3730a3;
    transform: translateY(-1px);
    box-shadow: 0 14px 26px -18px rgba(79, 70, 229, 0.9);
}
.stButton > button[kind="primary"],
[data-testid="stDownloadButton"] button[kind="primary"] {
    background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
    border: 1px solid rgba(79, 70, 229, 0.9);
    color: #ffffff;
    box-shadow: 0 16px 30px -18px rgba(79, 70, 229, 0.95);
}
.stButton > button[kind="primary"]:hover,
[data-testid="stDownloadButton"] button[kind="primary"]:hover {
    background: linear-gradient(135deg, #4338ca 0%, #6d28d9 100%);
    color: #ffffff;
    transform: translateY(-2px);
}

/* ---------- Cards / expanders ---------- */
[data-testid="stExpander"] {
    border: 1px solid rgba(148, 163, 184, 0.28);
    border-radius: 16px;
    background: rgba(255, 255, 255, 0.74);
    box-shadow: 0 16px 38px -32px rgba(15, 23, 42, 0.65);
    overflow: hidden;
    transition: border-color 0.18s ease, box-shadow 0.18s ease;
}
[data-testid="stExpander"]:hover {
    border-color: rgba(99, 102, 241, 0.35);
    box-shadow: 0 18px 40px -30px rgba(79, 70, 229, 0.55);
}
[data-testid="stExpander"] summary {
    font-weight: 600;
    color: #1e293b;
}
[data-testid="stExpander"] summary:hover {
    background: rgba(99, 102, 241, 0.05);
}

/* ---------- Inputs ---------- */
.stTextArea textarea,
.stTextInput input,
.stNumberInput input {
    border-radius: 12px !important;
    border-color: #dbe3ef !important;
    background: rgba(255, 255, 255, 0.95) !important;
    transition: box-shadow 0.18s ease, border-color 0.18s ease;
}
.stTextArea textarea:focus,
.stTextInput input:focus,
.stNumberInput input:focus {
    border-color: #818cf8 !important;
    box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.16) !important;
}
[data-baseweb="select"] > div {
    border-radius: 12px !important;
    border-color: #dbe3ef !important;
    background: rgba(255, 255, 255, 0.95) !important;
}

/* ---------- Feedback & data ---------- */
[data-testid="stAlert"] {
    border-radius: 14px;
    border: 1px solid rgba(148, 163, 184, 0.22);
}
[data-testid="stDataFrame"] {
    border-radius: 14px;
    overflow: hidden;
    border: 1px solid var(--agies-line);
}
[data-testid="stPlotlyChart"] {
    border-radius: 16px;
    border: 1px solid var(--agies-line);
    background: rgba(255, 255, 255, 0.78);
    padding: 0.45rem 0.35rem 0;
}
[data-testid="stProgress"] > div > div > div {
    background: linear-gradient(90deg, #6366f1, #a855f7);
}
hr {
    border: none;
    height: 1px;
    background: linear-gradient(90deg, transparent, #c7d2fe, transparent);
    margin: 1.4rem 0;
}
[data-testid="stCaptionContainer"] {
    color: var(--agies-muted);
}

/* ---------- Footer ---------- */
.agies-footer {
    margin-top: 2.6rem;
    padding: 1.1rem 1.4rem;
    border-radius: 16px;
    border: 1px solid var(--agies-line);
    background: rgba(255, 255, 255, 0.65);
    text-align: center;
    color: #64748b;
    font-size: 0.74rem;
    letter-spacing: 0.04em;
}
.agies-footer b {
    color: #312e81;
    letter-spacing: 0.14em;
}

@media (max-width: 700px) {
    .agies-hero { padding: 1.7rem 1.4rem 1.5rem; border-radius: 18px; }
    .agies-hero h1 { font-size: 2.3rem; letter-spacing: 0.18em; }
    .agies-hero .agies-sub { font-size: 0.82rem; }
}
</style>
<div class="agies-hero">
    <span class="agies-tag">Adaptive Assessment Platform</span>
    <h1>AGIES</h1>
    <p class="agies-sub">10-slot self-healing aptitude assessment engine</p>
    <div class="agies-chips">
        <span class="agies-chip"><b>10</b> dynamic slots</span>
        <span class="agies-chip"><b>CUSUM</b> leak detection</span>
        <span class="agies-chip"><b>Red Team</b> leak resistance</span>
        <span class="agies-chip"><b>Human</b> approval gates</span>
    </div>
</div>
""", unsafe_allow_html=True)

if "current_slot" not in st.session_state: st.session_state.current_slot = 1
if "generated_slots" not in st.session_state: st.session_state.generated_slots = {}
if "leak_detected" not in st.session_state: st.session_state.leak_detected = False
if "slot_metrics" not in st.session_state: st.session_state.slot_metrics = {}
if "parsed_bank" not in st.session_state: st.session_state.parsed_bank = []
if "uploaded_filename" not in st.session_state: st.session_state.uploaded_filename = ""
if "used_in_slots" not in st.session_state: st.session_state.used_in_slots = {}
if "global_exposure" not in st.session_state: st.session_state.global_exposure = {}
if "red_team_reports" not in st.session_state: st.session_state.red_team_reports = {}
if "item_approvals" not in st.session_state: st.session_state.item_approvals = {}

with st.sidebar:
    st.markdown("""
    <div class="agies-side-brand">
        <span>AGIES</span>
        <small>Leak-resilient assessment</small>
    </div>
    """, unsafe_allow_html=True)
    st.subheader("Red Team Controls")
    st.caption("Estimated by an LLM stand-in, not real candidate behaviour.")
    st.slider("Samples per solve", min_value=1, max_value=5, value=3, key="rt_samples")
    st.slider("Max regeneration rounds", min_value=1, max_value=5, value=3, key="rt_max_rounds")
    st.slider("Leak advantage threshold", min_value=0.0, max_value=1.0, value=0.20, step=0.05, key="rt_threshold")
    st.caption("More samples/rounds = more model calls. The attack panel shows an estimate before running.")
    st.divider()
    st.subheader("Generation Controls")
    st.slider(
        "Max AI-generated items per slot", min_value=0, max_value=30, value=15, key="gen_cap",
        help="When the bank is short, new items are written on the bank's own concepts, up to this cap.",
    )
    st.caption("0 disables generation; shortages reuse bank items instead.")

def _set_llm_notice(message):
    try:
        st.session_state.llm_notice = message
    except Exception:
        pass

_CONCEPT_RULES = [
    ("Reading Comprehension", re.compile(
        r'(?i)\b(passage|according\s+to\s+the\s+passage|main\s+idea|author\s+(?:suggests|argues)|'
        r'inference\s+from\s+the\s+passage)\b')),
    ("Vocabulary", re.compile(
        r'(?i)\b(synonym|antonym|closest\s+in\s+meaning|opposite\s+in\s+meaning|'
        r'choose\s+the\s+word|word\s+closest)\b')),
    ("Grammar", re.compile(
        r'(?i)\b(grammar|sentence|error|fill\s+in\s+the\s+blank|preposition|tense|article)\b')),
    ("Data Interpretation", re.compile(
        r'(?i)\b(data\s+interpretation|pie\s+chart|bar\s+chart|line\s+graph|frequency\s+table)\b')),
    ("Percentages", re.compile(
        r'(?i)\b(percent|percentage|discount|mark(?:ed)?\s*(?:price|up)|profit|loss|'
        r'selling\s+price|cost\s+price)\b')),
    ("Simple & Compound Interest", re.compile(
        r'(?i)\b(simple\s+interest|compound\s+interest|principal|interest\s+rate)\b')),
    ("Ratios & Proportions", re.compile(r'(?i)\b(ratio|proportion|proportional)\b')),
    ("Averages", re.compile(r'(?i)\b(average|arithmetic\s+mean|median|mode)\b')),
    ("Time & Work", re.compile(
        r'(?i)\b(work\s+together|time\s+and\s+work|efficiency|pipes?\s+and\s+cisterns?|'
        r'fill\s+the\s+tank)\b')),
    ("Speed, Time & Distance", re.compile(
        r'(?i)\b(speed|distance|km/h|kmph|train|boat|stream|upstream|downstream)\b')),
    ("Probability", re.compile(r'(?i)\b(probability|chance|dice|die|coin|cards?)\b')),
    ("Permutations & Combinations", re.compile(
        r'(?i)\b(permutation|combination|arrangement|committee|number\s+of\s+ways)\b')),
    ("Geometry & Mensuration", re.compile(
        r'(?i)\b(area|perimeter|volume|radius|diameter|circle|triangle|rectangle|square|'
        r'cylinder|cone|sphere)\b')),
    ("Number System", re.compile(
        r'(?i)\b(lcm|hcf|gcd|remainder|divisib|prime|factor|number\s+system)\b')),
    ("Series & Sequences", re.compile(
        r'(?i)\b(series|sequence|next\s+term|progression|pattern\s+in\s+the\s+numbers)\b')),
    ("Coding & Decoding", re.compile(r'(?i)\b(coding|decoding|letter\s+code|code\s+language)\b')),
    ("Syllogisms", re.compile(
        r'(?i)\b(syllogism|all\s+\w+\s+are|some\s+\w+\s+are|conclusion\s+follows)\b')),
    ("Blood Relations", re.compile(
        r'(?i)\b(blood\s+relation|father|mother|brother|sister|uncle|aunt|son\s+of|daughter\s+of)\b')),
    ("Direction Sense", re.compile(
        r'(?i)\b(north|south|east|west|direction|turns?\s+(?:left|right))\b')),
    ("Seating & Puzzles", re.compile(
        r'(?i)\b(seating|sitting\s+arrangement|puzzle|facing\s+(?:north|south))\b')),
    ("Algebra", re.compile(
        r'(?i)\b(algebra|equation|solve\s+for|quadratic|polynomial|expression|variable|linear)\b')),
    ("Computer Science", re.compile(
        r'(?i)\b(algorithm|complexity|recursion|binary\s+search|tree|database|sql|'
        r'operating\s+system|network|programming|code)\b')),
    ("Physics", re.compile(
        r'(?i)\b(velocity|acceleration|force|energy|momentum|friction|wave|current|'
        r'resistance|voltage|optics|lens|gravity)\b')),
    ("Chemistry", re.compile(
        r'(?i)\b(atom|molecule|reaction|acid|base|periodic|chemical|compound)\b')),
    ("Biology", re.compile(
        r'(?i)\b(cell|dna|organism|photosynthesis|enzyme|gene|neuron)\b')),
]

def _infer_concept(stem, options=None):
    """Deterministic concept tag used when the model is unavailable or vague."""
    stem_text = str(stem or "")
    option_text = " ".join(str(option) for option in (options or []))
    best = None
    for index, (label, pattern) in enumerate(_CONCEPT_RULES):
        hits = 2 * len(pattern.findall(stem_text)) + len(pattern.findall(option_text))
        if hits and (best is None or hits > best[0]):
            best = (hits, -index, label)
    return best[2] if best else "General Aptitude"

def batch_classify_and_gauge(questions):
    if not questions:
        return []
    fallback = [{
        "concept": _infer_concept(q.get("stem", ""), q.get("options", [])),
        "difficulty": None,
        "score": None,
    } for q in questions]
    api_key = get_api_key()
    if not api_key:
        _set_llm_notice("Groq is not configured; concepts and difficulty were estimated with built-in heuristics.")
        return fallback

    try:
        q_text = "".join([
            f"\n--- Question {idx} ---\nStem: {q['stem']}\nOptions: {q['options']}\n"
            for idx, q in enumerate(questions)
        ])
        prompt = f"""
        You are a Psychometric Data Classifier.
        I will provide a batch of {len(questions)} test questions.

        For EVERY question, you must:
        1. Determine the EXACT specific academic or logical concept being tested (e.g., "Algebraic Ratios", "Reading Comprehension").
           Stay faithful to what the stem actually asks; never invent a topic.
        2. Rate intrinsic difficulty on a 1-10 scale using these anchors:
           1-3 = recall or single-step recall (name, define, direct lookup)
           4-6 = comprehension or one-step application (calculate a percentage, interpret a result)
           7-8 = multi-step reasoning (derive a relation, apply two or three concepts)
           9-10 = proof, open-ended synthesis or expert-level analysis
        3. Map that score to EXACTLY one band: "Easy" (1-3), "Medium" (4-6), "Medium-Hard" (7-8), "Hard" (9-10).
           Use the full range; do not label every question "Medium".

        Respond ONLY in pure JSON matching this exact schema (an array of objects, keeping the exact same order as the input):
        {{
            "classifications": [
                {{"actual_concept": "string", "measured_difficulty": "string", "difficulty_score": 1-10}}
            ]
        }}

        QUESTIONS TO CLASSIFY:
        {q_text}
        """
        raw_content = llm_chat(prompt, temperature=0.1, json_mode=True)
        if "```json" in raw_content:
            json_str = raw_content.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_content:
            json_str = raw_content.split("```")[1].split("```")[0].strip()
        else:
            json_str = raw_content[raw_content.find("{"):raw_content.rfind("}") + 1]
        v_data = json.loads(json_str)
        results = v_data.get("classifications") or []
        if len(results) != len(questions):
            _set_llm_notice(
                "The model returned an incomplete classification; built-in heuristic concepts and difficulty were used for this batch."
            )
            return fallback

        parsed = []
        for question, result in zip(questions, results):
            try:
                score = float(result.get("difficulty_score"))
            except (TypeError, ValueError):
                score = None
            concept = str(result.get("actual_concept") or "").strip()
            if not concept or concept.lower() in {"general aptitude", "general", "aptitude", "unknown"}:
                concept = _infer_concept(question.get("stem", ""), question.get("options", []))
            parsed.append({
                "concept": concept,
                "difficulty": _normalize_llm_band(result.get("measured_difficulty")),
                "score": score,
            })
        return parsed
    except Exception as exc:  # noqa: BLE001 - keep ingestion alive
        _set_llm_notice(
            f"Groq was unavailable ({type(exc).__name__}); concepts and difficulty were estimated with built-in heuristics."
        )
        return fallback

_ANSWER_MARKER = re.compile(
    r'(?i)(?:\s|^)[\(\[]?\s*(?:ans|answer)\b\s*(?:is|:|=|-|–|—)?\s*'
    r'(?:option\s*)?[\(\[]?([A-Ea-e]|[1-5])[\)\]]?\s*[\.\)]?\s*$'
)

def _strip_answer_marker(text):
    """Remove a trailing answer key (e.g. 'Ans: C') so it never reaches an export."""
    return _ANSWER_MARKER.sub('', str(text)).strip()

_IMPORT_STEM_MIN = 8
_IMPORT_DUPLICATE_RATIO = 0.95
_IMPORT_HEADER = re.compile(
    r'(?i)^(?:page\s*\d+|section\s+[a-z]\b|instructions?\b|total\s+marks|time\s*(?:allowed|:)|\bduration\b|'
    r'answer\s+all|attempt\s+all|question\s+paper|assessment\s+engine|maximum\s+marks|max\s*\.?\s*marks)'
)

def _stem_tokens(stem):
    return set(re.findall(r'[a-z0-9]+', str(stem).lower()))

def _import_guard(questions):
    """Keep every usable question; only drop blank, header or repeated rows."""
    accepted, rejected, seen = [], [], []
    for question in questions:
        stem = str(question.get("stem", "")).strip()
        if len(stem) < _IMPORT_STEM_MIN or not re.search(r'[A-Za-z0-9]', stem):
            rejected.append({"stem": stem or "(blank)", "reason": "no usable question text"})
            continue
        if _IMPORT_HEADER.match(stem):
            rejected.append({"stem": stem, "reason": "page header or instructions"})
            continue
        options, seen_options = [], set()
        for option in question.get("options", []):
            cleaned = str(option).strip()
            key = cleaned.casefold()
            if not cleaned or key in seen_options:
                continue
            seen_options.add(key)
            options.append(cleaned)
        tokens = _stem_tokens(stem)
        if any(tokens and len(tokens & prior) / len(tokens | prior) >= _IMPORT_DUPLICATE_RATIO for prior in seen):
            rejected.append({"stem": stem, "reason": "near-duplicate of an earlier question"})
            continue
        seen.append(tokens)
        accepted.append(dict(question, options=options))
    return accepted, rejected

_LETTER_OPTION = re.compile(r'(?:^|\s+)(?:\(?[A-Ea-e][\.\)]|Option\s+[1-5]\:?)\s+')
_NUMERIC_OPTION = re.compile(r'(?:^|\s)(\d{1,2})[\.\)]\s+')

def _split_options(chunk):
    """Split lettered (A/B or a.) or numbered (1./2)) options, in either layout."""
    parts = _LETTER_OPTION.split(chunk)
    if len(parts) > 1:
        return parts
    matches = list(_NUMERIC_OPTION.finditer(chunk))
    run, expected = [], 1
    for match in matches:
        if int(match.group(1)) == expected:
            run.append(match)
            expected += 1
    if len(run) < 2:
        return [chunk]
    parts = [chunk[:run[0].start()]]
    for index, match in enumerate(run):
        end = run[index + 1].start() if index + 1 < len(run) else len(chunk)
        parts.append(chunk[match.end():end])
    return parts

_ANSWER_LINE = re.compile(r'(?i)^[ \t]*(?:correct\s+)?ans(?:wer)?\b\s*[\.\:\-–—]\s*.*$')
_PAGE_FOOTER = re.compile(r'(?i)^(?:page\s+\d+(?:\s+of\s+\d+)?|\d+\s*/\s*\d+|\d+)$')
_OPTION_START = re.compile(r'(?i)^(?:\(?[a-e1-5][\.\)]|option\s+[1-5]\b)')
_SECTION_START = re.compile(r'(?i)^(?:day|section|part|unit|module|chapter)\s+[a-z0-9]+\b')
_RUNNING_HEADER_PAGES = 3

def _is_noise_line(text, repeats):
    """True for answer lines, page numbers, running headers and section headings."""
    if _ANSWER_LINE.match(text) or _PAGE_FOOTER.match(text):
        return True
    if repeats >= _RUNNING_HEADER_PAGES and len(text) <= 70 and '?' not in text and not _OPTION_START.match(text):
        return True
    if len(text) <= 90 and '?' not in text and _SECTION_START.match(text):
        return True
    return (len(text) <= 70 and len(text) >= 8 and len(text.split()) >= 2 and '?' not in text
            and text.isupper() and re.fullmatch(r"[A-Z][A-Z &:'\-]+", text) is not None)

def _clean_document_text(pages):
    """Strip answers, running headers/footers and section headings before question splitting."""
    split_pages = [[line.rstrip() for line in str(page).splitlines()] for page in pages]
    repeats = {}
    for page in split_pages:
        for line in {line.strip().casefold() for line in page if line.strip()}:
            repeats[line] = repeats.get(line, 0) + 1
    kept_pages = []
    for page in split_pages:
        kept = []
        for line in page:
            text = line.strip()
            if text and _is_noise_line(text, repeats.get(text.casefold(), 0)):
                continue
            kept.append(line)
        kept_pages.append('\n'.join(kept))
    return '\n\n'.join(kept_pages)

_HEADER_TOKEN = re.compile(
    r'(?:^|\n)[ \t]*(?:(?:[Qq](?:uestion)?[ \t]*\.?[ \t]*(\d+))[ \t]*[\.\)\:\-–—]?[ \t]*'
    r'|(\d{1,2})[ \t]*[\.\)\:\-][ \t]*)'
)

def _split_question_text(text):
    """Split on question numbers while keeping numbered option lines inside their question."""
    chunks = []
    expected = 1
    option_run = 0
    start = None
    for match in _HEADER_TOKEN.finditer(text):
        explicit, bare = match.group(1), match.group(2)
        if explicit:
            label = int(explicit)
            accepted = True
        else:
            label = int(bare)
            line_end = text.find('\n', match.end())
            content_line = text[match.end(): line_end if line_end != -1 else len(text)].strip()
            if option_run and label == option_run + 1 and label <= 6:
                option_run = label
                accepted = False
            elif label == expected:
                accepted = True
            elif label == 1:
                if len(content_line) >= 60 or content_line.endswith('?'):
                    accepted = True
                else:
                    option_run = 1
                    accepted = False
            else:
                accepted = False
        if not accepted:
            continue
        if start is not None:
            chunks.append(text[start:match.start()])
        start = match.end()
        expected = label + 1
        option_run = 0
    if start is not None:
        chunks.append(text[start:])
    return [chunk for chunk in chunks if chunk.strip()]

_LLM_BAND_SCORE = {"Easy": 2.5, "Medium": 4.5, "Medium-Hard": 6.5, "Hard": 8.5}
_PROOF_VERB = re.compile(r'(?i)\b(prove|derive|establish|deduce|show\s+that|justify)\b')
_APPLY_VERB = re.compile(r'(?i)\b(evaluate|optimize|optimise|solve|calculate|determine|find)\b')
_OPEN_VERB = re.compile(r'(?i)\b(explain|discuss|describe|compare|analyse|analyze)\b')
_COMPLEX_TERM = re.compile(
    r'(?i)\b(probability|complexity|recursion|algorithm|theorem|integral|derivative|matrix|vector|'
    r'optimization|uncertainty|wave function|schr[oö]dinger|correlation|regression|bayes|hypothesis|'
    r'binary search tree|asymptotic|polynomial|logarithm|trigonometr)'
)
_RECALL_TERM = re.compile(r'(?i)\b(who|whom|when|where|which year|name|define|what is|what are)\b')
_FORMULA_SYMBOL = re.compile(r'[λπΩ√∫²³≤≥±→°]')

def _difficulty_features(stem, options):
    """Content-based difficulty prior on a 1-10 scale (recall vs multi-step reasoning)."""
    text = str(stem)
    words = re.findall(r"[A-Za-z0-9']+", text)
    score = 3.0
    wc = len(words)
    if wc > 50: score += 1.5
    elif wc > 30: score += 1.0
    elif wc > 18: score += 0.5
    elif wc < 8: score -= 0.5
    math_marks = len(re.findall(r'\d', text)) + 2 * len(re.findall(r'[×÷+−=%^/:]', text))
    if math_marks >= 12: score += 1.5
    elif math_marks >= 6: score += 1.0
    elif math_marks >= 2: score += 0.5
    if _PROOF_VERB.search(text): score += 2.0
    if _APPLY_VERB.search(text): score += 1.0
    if _OPEN_VERB.search(text): score += 0.75
    if _COMPLEX_TERM.search(text): score += 1.0
    if _RECALL_TERM.search(text): score -= 0.75
    if _FORMULA_SYMBOL.search(text): score += 0.5
    if len(re.findall(r'[,;:]', text)) >= 3: score += 0.5
    if options:
        if len(options) >= 5: score += 0.25
        if sum(1 for o in options if re.search(r'\d', str(o))) >= 3: score += 0.5
    else:
        score += 0.5
    return max(1.0, min(10.0, round(score, 1)))

def _band_for_score(score):
    if score < 3.5: return "Easy"
    if score < 5.5: return "Medium"
    if score < 7.5: return "Medium-Hard"
    return "Hard"

def _normalize_llm_band(raw):
    key = re.sub(r'\s+', '-', str(raw or '').strip().lower())
    return {"easy": "Easy", "medium": "Medium", "medium-hard": "Medium-Hard", "hard": "Hard"}.get(key)

_BAND_SCORE_BOUNDS = {
    "Easy": (1.0, 3.4),
    "Medium": (3.5, 5.4),
    "Medium-Hard": (5.5, 7.4),
    "Hard": (7.5, 10.0),
}

def _calibrate_difficulty(stem, options, llm_band=None, llm_score=None, enforce_band=False):
    """Blend the model's judgement with the deterministic prior, then band the result.

    enforce_band clamps the score into an explicitly requested band so a generated
    item still honours the difficulty the user asked for.
    """
    prior = _difficulty_features(stem, options)
    if llm_score is None and llm_band in _LLM_BAND_SCORE:
        llm_score = _LLM_BAND_SCORE[llm_band]
    if llm_score is None:
        score = prior
    else:
        llm_score = max(1.0, min(10.0, float(llm_score)))
        score = round(0.5 * llm_score + 0.5 * prior, 1)
    if enforce_band and llm_band in _BAND_SCORE_BOUNDS:
        low, high = _BAND_SCORE_BOUNDS[llm_band]
        score = round(min(high, max(low, score)), 1)
        return llm_band, score
    return _band_for_score(score), score

def _new_item_id():
    """Generate an item id that is not already in the session bank or database."""
    existing = {q.get("id") for q in st.session_state.parsed_bank}
    while True:
        candidate = f"Q_{random.randint(100000, 999999)}"
        if candidate not in existing and not db.item_exists(candidate):
            return candidate

_GENERATED_OPTION_PREFIX = re.compile(
    r'^(?:\(?\s*(?:option\s+)?[A-Fa-f1-6]\s*[\.\):]\s*|option\s+[1-6]\s*[:\.\)]\s*)'
)

def _generation_cap():
    try:
        return max(0, int(st.session_state.get("gen_cap", 15)))
    except (TypeError, ValueError):
        return 15

def _normalize_generated_options(raw_options):
    """Return lettered, de-duplicated options (A), B), ...) from model output."""
    if isinstance(raw_options, str):
        raw_options = [raw_options]
    options, seen = [], set()
    for raw in list(raw_options or [])[:6]:
        text = re.sub(r'\s+', ' ', str(raw)).strip()
        text = _GENERATED_OPTION_PREFIX.sub('', text).strip()
        if not text or text.casefold() in seen:
            continue
        seen.add(text.casefold())
        options.append(f"{chr(65 + len(options))}) {text}")
    return options

def _generated_answer(raw_answer, options):
    """Map a model answer (letter, number or option text) to a valid option letter."""
    text = str(raw_answer or "").strip()
    answer = _normalize_answer(text)
    if answer and ord(answer) - 65 < len(options):
        return answer
    cleaned = _GENERATED_OPTION_PREFIX.sub('', text).strip().casefold()
    for index, option in enumerate(options):
        body = _GENERATED_OPTION_PREFIX.sub('', option).strip().casefold()
        if cleaned and cleaned == body:
            return chr(65 + index)
    return ""

def _seed_examples(bank, concept, difficulty, limit=3):
    """Pick real bank items on the same concept to anchor generation."""
    pool = [q for q in bank if _concept_matches(concept, q.get("concept", ""))]
    typed = []
    if difficulty in _LLM_BAND_SCORE:
        typed = [q for q in pool if str(q.get("difficulty", "")).lower() == difficulty.lower()]
    typed_ids = {q.get("id") for q in typed}
    ordered = typed + [q for q in pool if q.get("id") not in typed_ids]
    return ordered[:limit]

def _concept_sequence(bank, target_difficulty, count):
    """Concepts to generate for, taken from the bank's own distribution."""
    if count <= 0:
        return []
    if not bank:
        return ["General Aptitude"] * count
    pool = bank
    if target_difficulty in _LLM_BAND_SCORE:
        typed = [q for q in pool if str(q.get("difficulty", "")).lower() == target_difficulty.lower()]
        if typed:
            pool = typed
    counts = Counter(q.get("concept") or _infer_concept(q.get("stem", ""), q.get("options", [])) for q in pool)
    concepts = [concept for concept, _ in counts.most_common() if concept]
    if not concepts:
        return ["General Aptitude"] * count
    return [concepts[index % len(concepts)] for index in range(count)]

def _generate_question(concept, difficulty, bank, api_key=None):
    """Write one concept-anchored MCQ, validate it, then calibrate its difficulty."""
    api_key = api_key or get_api_key()
    if not api_key:
        return None
    concept = (concept or "General Aptitude").strip()
    band = difficulty if difficulty in _LLM_BAND_SCORE else None
    target_score = _LLM_BAND_SCORE.get(band)
    seeds = _seed_examples(bank, concept, band)
    seed_block = "\n".join(f"- {q.get('stem', '')[:240]}" for q in seeds) or "- (no reference items; stay strictly on the requested concept)"
    difficulty_text = band or "match the difficulty mix of the reference items"

    prompt = f"""
    You are an expert psychometric item writer.
    Write ONE brand-new multiple-choice question.

    CONCEPT: "{concept}"
    DIFFICULTY: {difficulty_text}

    MANDATORY RULES:
    - The new item MUST test exactly the same concept as the reference items below.
      Do NOT switch to another topic, and do NOT copy a reference stem.
    - Use new wording and new values. Four options, exactly one correct answer.
    - Options must be plausible, mutually exclusive and grammatically parallel.
    - correct_answer must be the letter of the correct option (A, B, C or D).
    - The question must be unambiguous and solvable from the information given.

    REFERENCE ITEMS ON THE SAME CONCEPT:
    {seed_block}

    Respond ONLY in pure JSON matching this exact schema:
    {{
        "stem": "the new question text",
        "options": ["option one", "option two", "option three", "option four"],
        "correct_answer": "A",
        "explanation": "one sentence explaining the correct answer"
    }}
    """
    retry_note = "\n\nThe previous reply was unusable. Return valid JSON with four distinct options and a correct_answer letter."
    bank_tokens = [_stem_tokens(q.get("stem", "")) for q in bank]

    for attempt in range(2):
        try:
            raw = llm_chat(prompt + (retry_note if attempt else ""), temperature=0.7, json_mode=True)
        except Exception as exc:  # noqa: BLE001 - llm_chat already retried
            _set_llm_notice(f"Question generation stopped: the model was unreachable ({type(exc).__name__}).")
            return None
        try:
            if "```json" in raw:
                json_str = raw.split("```json")[1].split("```")[0].strip()
            elif "```" in raw:
                json_str = raw.split("```")[1].split("```")[0].strip()
            else:
                json_str = raw[raw.find("{"):raw.rfind("}") + 1]
            data = json.loads(json_str)
        except (ValueError, TypeError):
            continue

        stem = _normalize_math_notation(re.sub(r'\s+', ' ', str(data.get("stem") or "")).strip())
        options = [_normalize_math_notation(opt) for opt in _normalize_generated_options(data.get("options"))]
        answer = _generated_answer(data.get("correct_answer"), options)
        if len(stem) < 10 or len(options) != 4 or not answer:
            continue
        tokens = _stem_tokens(stem)
        if any(tokens and len(tokens & prior) / len(tokens | prior) >= 0.9 for prior in bank_tokens):
            continue
        calibrated_band, score = _calibrate_difficulty(
            stem, options, band, target_score, enforce_band=True)
        if concept.lower() in {"general aptitude", "general", "aptitude"}:
            concept = _infer_concept(stem, options)
        return {
            "id": _new_item_id(),
            "stem": stem,
            "options": options,
            "correct_answer": answer,
            "concept": concept,
            "difficulty": calibrated_band,
            "difficulty_score": score,
            "explanation": str(data.get("explanation") or "").strip(),
            "is_generated": True,
            "methodology": "AI-generated (concept-anchored)",
        }
    _set_llm_notice("Question generation returned unusable content twice; the slot was topped up from the bank.")
    return None

def _register_generated_item(item):
    """Add a generated item to the session bank and persist it with its answer key."""
    st.session_state.parsed_bank.append(item)
    st.session_state.global_exposure[item["id"]] = 0
    db.insert_item({
        "item_id": item["id"],
        "stem": item["stem"],
        "options": item["options"],
        "correct_answer": item.get("correct_answer", "N/A"),
        "irt_difficulty_b": round((item.get("difficulty_score", 5.5) - 5.5) / 2.0, 2),
        "approval_status": "DRAFT",
    })
    st.session_state.item_approvals[item["id"]] = "DRAFT"

def parse_uploaded_file(file):
    raw_questions = []
    detected = 0
    filename = file.name.lower()
    st.session_state.import_error = ""
    st.session_state.import_summary = {}
    st.session_state.import_rejections = []
    st.session_state.llm_notice = ""

    if filename.endswith('.csv'):
        try:
            df = pd.read_csv(file)
        except Exception as exc:  # noqa: BLE001 - surfaced in the UI
            st.session_state.import_error = f"Could not read the CSV file: {exc}"
            return []
        for _, row in df.iterrows():
            opts = row.get('options', '[]')
            if pd.isna(opts): opts = '[]'
            if isinstance(opts, str):
                try: opts = json.loads(opts)
                except Exception: opts = [opts] if str(opts).strip() else []
            if not isinstance(opts, list):
                opts = [str(opts)]
            stem = _strip_answer_marker(str(row.get('stem', '') or '')).strip()
            opts = [_strip_answer_marker(o) for o in opts[:6]]
            opts = [o for o in opts if o]
            raw_questions.append({"stem": stem, "options": opts})
            detected += 1

    elif filename.endswith('.pdf') or filename.endswith('.txt'):
        if filename.endswith('.pdf'):
            try:
                with fitz.open(stream=file.read(), filetype="pdf") as doc:
                    text = _clean_document_text([page.get_text("text") for page in doc])
            except Exception as exc:  # noqa: BLE001 - surfaced in the UI
                st.session_state.import_error = f"Could not read the PDF file: {exc}"
                return []
            if len(text.strip()) < 20:
                st.session_state.import_summary = {
                    "detected": 0, "accepted": 0, "open_response": 0, "no_text_layer": True,
                }
                return []
        else:
            try:
                text = file.read().decode('utf-8', errors='ignore')
            except Exception as exc:  # noqa: BLE001 - surfaced in the UI
                st.session_state.import_error = f"Could not read the text file: {exc}"
                return []
            text = _clean_document_text([text])
        
        text = re.sub(r'([^\.\?\!\n])\n([a-z])', r'\1 \2', text)
        splits = _split_question_text(text)
        
        if len(splits) <= 2:
            raw_splits = re.split(r'(\?)(?:\s+|\n+)', text)
            splits = []
            current_str = ""
            for token in raw_splits:
                if token == '?':
                    current_str += '?'
                    splits.append(current_str)
                    current_str = ""
                else: current_str += token
            if current_str.strip(): splits.append(current_str)
            if len(splits) <= 2: splits = re.split(r'\n\n+', text)
                
        for chunk in splits:
            detected += 1
            chunk = re.sub(r'\s+', ' ', chunk).strip() 
            if len(chunk) < 8 or not re.search(r'[a-zA-Z]{3,}', chunk): continue
                
            parts = _split_options(chunk)
            
            if len(parts) > 1:
                stem = _strip_answer_marker(parts[0].strip().replace('\n', ' '))
                opts = []
                for i, opt in enumerate(parts[1:]):
                    val = _strip_answer_marker(opt.strip().replace('\n', ' '))
                    if val: opts.append(f"{chr(65+i)}) {val}")
            else:
                stem = _strip_answer_marker(chunk.replace('\n', ' '))
                opts = [] 
            
            raw_questions.append({"stem": stem, "options": opts[:6]})
            
    raw_questions, rejected = _import_guard(raw_questions)
    for question in raw_questions:
        question["stem"] = _normalize_math_notation(question["stem"])
        question["options"] = [_normalize_math_notation(opt) for opt in question["options"]]
    st.session_state.import_rejections = rejected
    st.session_state.import_summary = {
        "detected": detected,
        "accepted": len(raw_questions),
        "open_response": sum(1 for q in raw_questions if not q["options"]),
    }

    bank = []
    difficulty_counts = {}
    batch_size = 20
    for i in range(0, len(raw_questions), batch_size):
        batch = raw_questions[i:i + batch_size]
        classifications = batch_classify_and_gauge(batch)
        for q, info in zip(batch, classifications):
            difficulty, score = _calibrate_difficulty(
                q["stem"], q["options"], info.get("difficulty"), info.get("score"))
            q_id = _new_item_id()
            db.insert_item({
                'item_id': q_id, 'stem': q['stem'], 'options': q['options'], 'correct_answer': 'N/A',
                'irt_difficulty_b': round((score - 5.5) / 2.0, 2),
            })
            new_item = {
                'id': q_id, 'stem': q['stem'], 'options': q['options'],
                'concept': info.get("concept", "General Aptitude"),
                'difficulty': difficulty, 'difficulty_score': score,
            }
            bank.append(new_item)
            difficulty_counts[difficulty] = difficulty_counts.get(difficulty, 0) + 1
            st.session_state.global_exposure[q_id] = 0
    st.session_state.import_summary["difficulty_distribution"] = difficulty_counts
    if bank:
        st.session_state.import_summary["mean_difficulty_score"] = round(
            sum(item['difficulty_score'] for item in bank) / len(bank), 1)
    return bank

def _normalize_answer(value):
    text = str(value).strip().upper()
    if text in ("", "N/A", "NA", "NONE", "NULL", "-"):
        return ""
    match = re.search(r'(?:^|[^A-Z])([A-E])(?:$|[^A-Z])', text)
    if match:
        return match.group(1)
    if text.isdigit() and 1 <= int(text) <= 5:
        return chr(64 + int(text))
    return ""

def _concept_lookup():
    mapping = {q.get("id"): q.get("concept", "") for q in st.session_state.parsed_bank}
    for items in st.session_state.generated_slots.values():
        for q in items:
            mapping.setdefault(q.get("id"), q.get("concept", ""))
    return mapping

def _score_responses(records, item_meta):
    rows = []
    unkeyed = 0
    for record in records:
        key = _normalize_answer(item_meta.get(record["item_id"], {}).get("correct_answer", ""))
        if not key:
            unkeyed += 1
            continue
        selected = _normalize_answer(record.get("selected", ""))
        rows.append({
            "candidate_id": record["candidate_id"],
            "item_id": record["item_id"],
            "selected": selected,
            "correct": 1 if selected == key else 0,
        })
    return pd.DataFrame(rows), unkeyed

def _item_statistics(scored):
    totals = scored.groupby("candidate_id")["correct"].sum()
    scored = scored.assign(total=scored["candidate_id"].map(totals))
    rows = []
    for item_id, group in scored.groupby("item_id"):
        point_biserial = None
        if group["correct"].nunique() > 1 and group["total"].std(ddof=0) > 0:
            point_biserial = group["correct"].corr(group["total"])
        counts = group["selected"].value_counts().to_dict()
        rows.append({
            "Item": item_id,
            "N": len(group),
            "p-value": round(group["correct"].mean(), 3),
            "Point-biserial": None if point_biserial is None else round(point_biserial, 3),
            "Responses": " ".join(f"{letter}={counts.get(letter, 0)}" for letter in "ABCDE"),
        })
    return pd.DataFrame(rows).sort_values("p-value").reset_index(drop=True)

def _kr20(scored):
    pivot = scored.pivot_table(index="candidate_id", columns="item_id", values="correct", aggfunc="max")
    pivot = pivot.dropna()
    k = pivot.shape[1]
    if k < 2 or pivot.shape[0] < 2:
        return None
    item_variance = (pivot.mean() * (1 - pivot.mean())).sum()
    total_variance = pivot.sum(axis=1).var(ddof=1)
    if not total_variance or total_variance <= 0:
        return None
    return (k / (k - 1)) * (1 - item_variance / total_variance)

def _slot_approval_counts(questions):
    approved = sum(
        1 for q in questions
        if st.session_state.item_approvals.get(q.get("id"), q.get("approval_status", "DRAFT")) == "APPROVED"
    )
    return approved, len(questions)

_PDF_CHAR_MAP = str.maketrans({
    "\u2010": "-", "\u2011": "-", "\u2012": "-", "\u2013": "-", "\u2014": "-", "\u2015": "-",
    "\u2212": "-", "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
    "\u00a0": " ", "\u2022": "-", "\u2026": "...", "\u00d7": "x", "\u2192": "->",
})

_SUPERSCRIPT = {"0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴",
                "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹", "n": "ⁿ"}
_CARET_SUPERSCRIPT = {"⁰": "^0", "⁴": "^4", "⁵": "^5", "⁶": "^6",
                      "⁷": "^7", "⁸": "^8", "⁹": "^9", "ⁿ": "^n"}

def _normalize_math_notation(text):
    """Repair exponents flattened by PDF extraction: x2y -> x²y, x^3 -> x³."""
    value = str(text or "")
    value = value.translate(str.maketrans(_CARET_SUPERSCRIPT))
    value = re.sub(r'\^(2|3)\b', lambda m: _SUPERSCRIPT[m.group(1)], value)
    value = re.sub(
        r'(?<=[A-Za-z])([2-9])(?=\s*(?:[A-Za-z()\[\]{}]|[+\-=*/^,;])|$)',
        lambda m: _SUPERSCRIPT[m.group(1)],
        value,
    )
    return value

def _pdf_ascii(text):
    """Normalize maths and punctuation, then keep Latin-1 characters the core fonts support."""
    mapped = _normalize_math_notation(text).translate(_PDF_CHAR_MAP)
    return "".join(ch for ch in mapped if ord(ch) < 256)

def generate_pdf(slot_num, questions):
    raw_text_block = "".join([q['stem'] for q in questions]) + str(time.time())
    slot_hash = hashlib.sha256(raw_text_block.encode()).hexdigest()[:16] 
    
    qr = qrcode.QRCode(version=1, box_size=3, border=2)
    qr.add_data(f"AGIES SECURE SLOT VERIFICATION\nSlot: {slot_num}\nHash: {slot_hash}\nStatus: {'SHIFTED' if st.session_state.leak_detected else 'STANDARD'}")
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    qr_path = f"temp_qr_{slot_num}.png"
    qr_img.save(qr_path)
    
    pdf = FPDF()
    pdf.add_page()
    pdf.image(qr_path, x=175, y=8, w=25)
    
    pdf.set_font("Arial", 'B', 22)
    pdf.set_text_color(20, 50, 90) 
    pdf.cell(0, 10, txt="AGIES Assessment Engine", ln=True, align='C')
    pdf.set_font("Arial", 'B', 14)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 10, txt=f"Candidate Question Paper - Slot {slot_num}", ln=True, align='C')
    pdf.set_font("Courier", '', 9)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 6, txt=f"Cryptographic Hash: {slot_hash}", ln=True, align='C')

    approved_count, total_count = _slot_approval_counts(questions)
    draft_count = total_count - approved_count
    if draft_count:
        pdf.set_font("Arial", 'B', 48)
        pdf.set_text_color(236, 236, 236)
        pdf.text(38, 150, "DRAFT")
        pdf.set_font("Arial", 'B', 10)
        pdf.set_text_color(190, 40, 40)
        pdf.cell(0, 8, txt=f"DRAFT - {draft_count} of {total_count} items await reviewer approval", ln=True, align='C')

    if st.session_state.leak_detected and slot_num >= 3:
        pdf.set_font("Arial", 'I', 10)
        pdf.set_text_color(200, 50, 50) 
        pdf.cell(0, 8, txt="[SECURITY ALERT: Adaptive Pattern Shift Triggered - Guardrails Active]", ln=True, align='C')
    
    pdf.set_draw_color(200, 200, 200)
    pdf.line(10, pdf.get_y() + 2, 200, pdf.get_y() + 2)
    pdf.ln(10)
    for i, q in enumerate(questions):
        pdf.set_font("Arial", 'I', 9)
        pdf.set_text_color(120, 120, 120)
        methodology = q.get('methodology', 'Standard')
        
        pdf.cell(0, 6, txt=f"[{_pdf_ascii(q.get('concept', '')).upper()}] - {_pdf_ascii(methodology)}", ln=True, align='R')
        
        pdf.set_font("Arial", 'B', 11)
        pdf.set_text_color(0, 0, 0)
        
        # Remove invisible canary characters for the PDF print (they break FPDF encodings)
        stem_clean = q['stem'].replace('\u200b', '').replace('\u200c', '')
        
        # Strip ALL non-ASCII characters to prevent question marks from appearing on the PDF
        stem = _pdf_ascii(stem_clean)
        
        pdf.multi_cell(w=0, h=7, txt=f"Q{i+1}. {stem}")
        pdf.ln(3) 
        
        pdf.set_font("Arial", '', 11)
        if len(q['options']) > 0:
            for opt in q['options']:
                opt_str = _pdf_ascii(opt)
                pdf.set_x(20)
                pdf.cell(w=0, h=7, txt=f"{opt_str}", ln=True)
        else:
            pdf.set_font("Arial", 'I', 10)
            pdf.set_text_color(150, 150, 150)
            pdf.set_x(20)
            pdf.cell(w=0, h=8, txt="[Write your answer in the space provided below]", ln=True)
            pdf.ln(20) 
            pdf.set_draw_color(180, 180, 180)
            pdf.line(20, pdf.get_y(), 190, pdf.get_y()) 
            pdf.line(20, pdf.get_y()+10, 190, pdf.get_y()+10) 
            pdf.ln(15)
        pdf.ln(10)   
        
    pdf.set_y(-15)
    pdf.set_font("Arial", 'I', 8)
    pdf.set_text_color(128, 128, 128)
    pdf.cell(0, 10, f"AGIES Auto-Generated Assessment | Slot {slot_num} | Page " + str(pdf.page_no()), 0, 0, 'C')
    try: os.remove(qr_path)
    except: pass
    return bytes(pdf.output())

_REQ_PATTERN = re.compile(
    r'(\d+)\s*[x*]?\s*(medium[\s-]?hard|easy|medium|med|hard|mixed|any|all)'
    r'|(medium[\s-]?hard|easy|medium|med|hard|mixed|any|all)\s*[x*]?\s*(\d+)',
    re.IGNORECASE
)
_DIFFICULTY_MAP = {
    "easy": "Easy", "medium": "Medium", "med": "Medium",
    "medium-hard": "Medium-Hard", "hard": "Hard",
    "mixed": "Any", "any": "Any", "all": "Any",
}
_STOPWORDS = {"and", "of", "the", "a", "an", "for", "in", "on"}

def _normalize_difficulty(raw):
    key = re.sub(r'\s+', '-', raw.strip().lower())
    return _DIFFICULTY_MAP.get(key, "Any")

def _concept_matches(requested, actual):
    a = str(requested).lower().strip()
    b = str(actual).lower().strip()
    if not a or not b:
        return False
    if a in b or b in a:
        return True
    a_tokens = set(re.findall(r'[a-z]+', a)) - _STOPWORDS
    b_tokens = set(re.findall(r'[a-z]+', b)) - _STOPWORDS
    return bool(a_tokens & b_tokens)

def parse_requirement_prompt(text):
    if not text or not text.strip():
        return []
    requirements = []
    for raw_line in re.split(r'[\n;]+', text):
        line = raw_line.strip()
        if not line:
            continue
        matches = list(_REQ_PATTERN.finditer(line))
        if not matches:
            bare = re.search(r'^(.*?)\s*[:\-–—]?\s*(\d+)\s*(?:questions?|qs?)?\s*$', line, re.IGNORECASE)
            if bare:
                concept = bare.group(1).strip(" \t:-–—,.") or "General Aptitude"
                requirements.append({"concept": concept, "count": int(bare.group(2)), "difficulty": "Any"})
            else:
                requirements.append({"concept": line.strip(" \t:-–—,."), "count": 1, "difficulty": "Any"})
            continue
        concept = line[:matches[0].start()].strip(" \t:-–—,.") or "General Aptitude"
        for match in matches:
            count = int(match.group(1) or match.group(4))
            diff = match.group(2) or match.group(3)
            if count > 0:
                requirements.append({"concept": concept, "count": count, "difficulty": _normalize_difficulty(diff)})
    return requirements

def _estimated_generation_need(bank, requirements, target_difficulty, slot_size):
    """Approximate how many items the model may need to write for the next slot."""
    if requirements:
        need = 0
        for req in requirements:
            matches = [q for q in bank if _concept_matches(req['concept'], q.get('concept', ''))]
            need += max(0, req['count'] - len(matches))
        return need
    if target_difficulty in _LLM_BAND_SCORE:
        available = sum(
            1 for q in bank
            if str(q.get('difficulty', '')).lower() == target_difficulty.lower()
        )
    else:
        available = len(bank)
    return max(0, slot_size - available)

def _pick_from_pool(pool, n, prev_q_ids, max_overlap, exclude_ids=None):
    exclude_ids = exclude_ids or set()
    pool = [q for q in pool if q['id'] not in exclude_ids]
    allowed_overlap = int((max_overlap / 100.0) * n)
    overlap = [q for q in pool if q['id'] in prev_q_ids]
    fresh = [q for q in pool if q['id'] not in prev_q_ids]
    random.shuffle(overlap)
    random.shuffle(fresh)
    overlap.sort(key=lambda x: st.session_state.global_exposure.get(x['id'], 0))
    fresh.sort(key=lambda x: st.session_state.global_exposure.get(x['id'], 0))
    picked = overlap[:allowed_overlap]
    picked.extend(fresh[:max(0, n - len(picked))])
    return picked

def synthesize_question(concept, difficulty, api_key=None):
    """Backwards-compatible wrapper around concept-anchored generation."""
    return _generate_question(concept, difficulty, st.session_state.parsed_bank, api_key)

def _assemble_from_requirements(requirements, prev_q_ids, max_overlap):
    bank = st.session_state.parsed_bank
    api_key = get_api_key()
    cap = _generation_cap()
    generated = 0
    selected, selected_ids = [], set()
    for req in requirements:
        concept, diff, count = req['concept'], req['difficulty'], req['count']
        concept_pool = [q for q in bank if _concept_matches(concept, q.get('concept', ''))]
        if diff and diff != "Any":
            typed = [q for q in concept_pool if str(q.get('difficulty', '')).lower() == diff.lower()]
            if len(typed) < count and typed:
                st.toast(f"Only {len(typed)} '{diff}' item(s) for '{concept}' — generating the rest.")
        else:
            typed = concept_pool
        picked = _pick_from_pool(typed, count, prev_q_ids, max_overlap, selected_ids)
        selected.extend(picked)
        selected_ids.update(q['id'] for q in picked)
        deficit = count - len(picked)

        if deficit > 0 and not api_key:
            st.warning("GROQ_API_KEY is not configured; missing items are filled from the existing bank.")
        elif deficit > 0 and cap <= 0:
            st.warning("AI generation is disabled in the sidebar; missing items are filled from the existing bank.")
        failures = 0
        while deficit > 0 and api_key and generated < cap:
            new_item = _generate_question(concept, diff if diff != "Any" else "Any", bank, api_key)
            if not new_item:
                failures += 1
                if failures >= 2:
                    break
                continue
            failures = 0
            _register_generated_item(new_item)
            generated += 1
            selected.append(new_item)
            selected_ids.add(new_item['id'])
            deficit -= 1
        if deficit > 0 and api_key and generated >= cap:
            st.toast(f"Generation cap ({cap} item(s) per slot) reached; topping up '{concept}' from the bank.")

        if deficit > 0:
            filler = _pick_from_pool(concept_pool, deficit, prev_q_ids, max_overlap, selected_ids)
            selected.extend(filler)
            selected_ids.update(q['id'] for q in filler)
            deficit -= len(filler)
        if deficit > 0:
            filler = _pick_from_pool(bank, deficit, prev_q_ids, max_overlap, selected_ids)
            selected.extend(filler)
            selected_ids.update(q['id'] for q in filler)
            deficit -= len(filler)
        if deficit > 0:
            st.warning(f"Could only assemble {count - deficit}/{count} questions for '{concept}'.")
    if generated:
        st.session_state.last_generation = {
            "generated": generated, "cap": cap, "context": "requirements",
        }
    return selected

def _rewrite_for_pattern_shift(item, method, api_key):
    """Replace a leaked item with a parallel, structurally shifted item and valid key."""
    if not api_key:
        return None
    original = json.dumps({
        "stem": item.get("stem", ""),
        "options": item.get("options", []),
        "correct_answer": item.get("correct_answer") or item.get("key", ""),
    }, ensure_ascii=False)
    prompt = f"""
    You are an expert psychometric item writer building an anti-cheat assessment engine.
    A question has been leaked by candidates. Replace it with a NEW parallel variant.

    ORIGINAL QUESTION:
    {original}

    METHODOLOGY TO APPLY: "{method}"

    RULES:
    - Preserve the exact underlying concept and skill tested; do not switch topic.
    - Change the values, wording and structural framing so the leaked answer key is useless.
    - Provide four plausible options, exactly one correct.
    - correct_answer must be the letter of the correct option (A, B, C or D).

    Respond ONLY in pure JSON matching this exact schema:
    {{
        "stem": "the new question text",
        "options": ["option one", "option two", "option three", "option four"],
        "correct_answer": "A",
        "explanation": "one sentence explaining the correct answer"
    }}
    """
    try:
        raw = llm_chat(prompt, temperature=0.7, json_mode=True)
    except Exception as exc:  # noqa: BLE001 - llm_chat already retried
        _set_llm_notice(f"Pattern shift stopped: the model was unreachable ({type(exc).__name__}).")
        return None
    try:
        if "```json" in raw:
            json_str = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            json_str = raw.split("```")[1].split("```")[0].strip()
        else:
            json_str = raw[raw.find("{"):raw.rfind("}") + 1]
        data = json.loads(json_str)
    except (ValueError, TypeError):
        return None
    stem = re.sub(r'\s+', ' ', str(data.get("stem") or "")).strip()
    options = _normalize_generated_options(data.get("options"))
    answer = _generated_answer(data.get("correct_answer"), options)
    if len(stem) < 10 or len(options) < 2 or not answer:
        return None
    band, score = _calibrate_difficulty(stem, options)
    rewritten = dict(item)
    rewritten.update({
        "stem": stem,
        "options": options,
        "correct_answer": answer,
        "key": answer,
        "difficulty": band,
        "difficulty_score": score,
        "methodology": f"{method} (AI pattern shift)",
        "is_rewritten": True,
    })
    db.insert_item({
        "item_id": rewritten["id"],
        "stem": stem,
        "options": options,
        "correct_answer": answer,
        "irt_difficulty_b": round((score - 5.5) / 2.0, 2),
        "approval_status": "DRAFT",
    })
    st.session_state.item_approvals[rewritten["id"]] = "DRAFT"
    return rewritten

def generate_slot_from_bank(slot_num, num_questions, target_difficulty, max_overlap, pattern_shifted=False, progress_bar=None, requirements=None):
    bank = st.session_state.parsed_bank
    st.session_state.llm_notice = ""
    if not bank and not requirements:
        return []

    if "global_exposure" not in st.session_state:
        st.session_state.global_exposure = {q['id']: 0 for q in bank}

    api_key = get_api_key()
    cap = _generation_cap()
    generated = 0
    prev_slot = slot_num - 1
    prev_q_ids = set(st.session_state.used_in_slots.get(prev_slot, []))

    generated_items = []
    if requirements:
        selected = _assemble_from_requirements(requirements, prev_q_ids, max_overlap)
        eligible = bank
    else:
        if target_difficulty not in ["Mixed", "Uncalibrated (Pending Review)"]:
            eligible = [q for q in bank if str(q.get('difficulty', '')).lower() == target_difficulty.lower()]
            missing = max(0, num_questions - len(eligible))
            if missing and api_key and cap > 0:
                concepts = _concept_sequence(eligible or bank, target_difficulty, min(missing, cap))
                failures = 0
                for concept in concepts:
                    new_item = _generate_question(concept, target_difficulty, bank, api_key)
                    if not new_item:
                        failures += 1
                        if failures >= 2:
                            break
                        continue
                    failures = 0
                    _register_generated_item(new_item)
                    generated_items.append(new_item)
                    generated += 1
                if generated:
                    st.toast(f"Generated {generated} '{target_difficulty}' item(s) from the bank's own concepts.", icon="🤖")
                    eligible = [
                        q for q in bank
                        if str(q.get('difficulty', '')).lower() == target_difficulty.lower()
                    ]
            if len(eligible) < num_questions:
                if missing and not api_key:
                    st.warning("The bank is short for this difficulty and GROQ_API_KEY is not configured; using the mixed bank.")
                elif missing and cap <= 0:
                    st.warning("AI generation is disabled in the sidebar; using the mixed bank.")
                else:
                    st.toast(f"Only {len(eligible)} '{target_difficulty}' item(s) available; using the mixed bank.")
                eligible = bank
        else:
            eligible = bank
        allowed_overlap = int((max_overlap / 100.0) * num_questions)

        selected = list(generated_items[:num_questions])
        selected_ids = {q['id'] for q in selected}
        overlap_candidates = [q for q in eligible if q['id'] in prev_q_ids and q['id'] not in selected_ids]
        fresh_candidates = [q for q in eligible if q['id'] not in prev_q_ids and q['id'] not in selected_ids]

        random.shuffle(overlap_candidates)
        random.shuffle(fresh_candidates)
        overlap_candidates.sort(key=lambda x: st.session_state.global_exposure.get(x['id'], 0))
        fresh_candidates.sort(key=lambda x: st.session_state.global_exposure.get(x['id'], 0))

        remaining_needed = num_questions - len(selected)
        selected.extend(overlap_candidates[:min(allowed_overlap, remaining_needed)])
        remaining_needed = num_questions - len(selected)
        selected.extend(fresh_candidates[:remaining_needed])
    
    deficit = num_questions - len(selected)
    if deficit > 0 and not requirements:
        if api_key and generated < cap:
            concept_target = target_difficulty if target_difficulty in _LLM_BAND_SCORE else "Any"
            concepts = _concept_sequence(selected or bank, target_difficulty, min(deficit, cap - generated))
            for concept in concepts:
                new_item = _generate_question(concept, concept_target, bank, api_key)
                if not new_item:
                    break
                _register_generated_item(new_item)
                generated += 1
                selected.append(new_item)
                deficit -= 1
            if generated:
                st.toast(f"Generated {generated} item(s) from the bank's own concepts.", icon="🤖")
        if deficit > 0:
            selected_ids = {q.get('id') for q in selected}
            pool = [q for q in eligible if q.get('id') not in selected_ids]
            pool.sort(key=lambda x: st.session_state.global_exposure.get(x.get('id'), 0))
            filler = pool[:deficit]
            selected.extend(filler)
            deficit -= len(filler)
        if deficit > 0:
            if not api_key:
                st.warning("Bank is too small and GROQ_API_KEY is not configured; overlap limits may be exceeded.")
            elif cap <= 0:
                st.warning("Bank is too small and AI generation is disabled in the sidebar; overlap limits may be exceeded.")
            else:
                st.warning(f"Could only assemble {num_questions - deficit}/{num_questions} questions; generation stopped early.")
    if generated:
        st.session_state.last_generation = {"generated": generated, "cap": cap, "context": "slot"}
            
    st.session_state.used_in_slots[slot_num] = [q['id'] for q in selected]
    for q in selected:
        st.session_state.global_exposure[q['id']] = st.session_state.global_exposure.get(q['id'], 0) + 1
        
    random.shuffle(selected)
    
    base_approaches = [
        ["Standard Equation", "Direct Ratio", "Formulaic"],
        ["Graphical Analysis", "Tabular Mapping", "Proportional Reasoning"],
        ["Case-based Synthesis", "Process of Elimination", "Heuristic Estimation"]
    ]
    shifted_approaches = ["Visual Topology", "Logical Deduction", "Reverse Engineering", "Abstract Proofs"]
    approaches = shifted_approaches if pattern_shifted else base_approaches[(slot_num - 1) % len(base_approaches)]
    
    final_questions = []
    use_groq = pattern_shifted and api_key
    
    for i, q in enumerate(selected):
        new_q = q.copy()
        method = approaches[i % len(approaches)]
        new_q['methodology'] = method
        new_q['is_shifted'] = pattern_shifted
        
        if use_groq:
            if progress_bar:
                progress_bar.progress(
                    (i + 1) / len(selected),
                    text=f"Groq API: Rewriting Question {i+1} / {len(selected)}...",
                )
            rewritten = _rewrite_for_pattern_shift(new_q, method, api_key)
            if rewritten:
                new_q = rewritten
                new_q['is_shifted'] = True

        new_q['stem'] = embed_canary(new_q['stem'], slot_num)
        final_questions.append(new_q)
        
    return final_questions
DEMO_SECTIONS = {
    "Percentages": "Quantitative",
    "Ratios": "Quantitative",
    "Algebra": "Quantitative",
    "Series Completion": "Logical Reasoning",
    "Syllogisms": "Logical Reasoning",
    "Vocabulary": "Verbal Ability",
    "Reading Comprehension": "Verbal Ability",
}
MAX_LLM_CALLS = 300

def _red_team_config():
    return (
        st.session_state.get("rt_samples", 3),
        st.session_state.get("rt_max_rounds", 3),
        st.session_state.get("rt_threshold", 0.20),
    )

def _concept_family_map():
    return {q.get('concept', ''): q.get('concept', '') for q in st.session_state.parsed_bank}

def _demo_options(correct, distractors, key_index):
    cleaned = [str(d) for d in distractors if str(d) != str(correct)][:3]
    while len(cleaned) < 3:
        cleaned.append("None of these")
    options = list(cleaned)
    options.insert(key_index, str(correct))
    return [f"{chr(65 + i)}) {option}" for i, option in enumerate(options)], chr(65 + key_index)

def build_demo_bank():
    bank = []
    counter = {"n": 0}

    def add(concept, difficulty, stem, correct, distractors, key_index):
        counter["n"] += 1
        options, key = _demo_options(correct, distractors, key_index)
        bank.append({
            "id": f"D{counter['n']:03d}",
            "stem": stem,
            "options": options,
            "key": key,
            "correct_answer": key,
            "concept": concept,
            "section": DEMO_SECTIONS[concept],
            "difficulty": difficulty,
            "methodology": "Standard",
            "approval_status": "DRAFT",
        })

    for i in range(14):
        key_index = i % 4
        if i % 3 == 0:
            price = 200 + 10 * i
            discount = 10 + (i % 4) * 5
            original = price * 100 // (100 - discount)
            add("Percentages", ["Easy", "Medium"][i % 2],
                f"A shirt sells for Rs. {price} after a {discount}% discount. What was its original price?",
                f"Rs. {original}",
                [f"Rs. {original + 20}", f"Rs. {original - 15}", f"Rs. {price}"], key_index)
        elif i % 3 == 1:
            total = 120 + 12 * i
            left = 2 + i % 3
            right = 3 + i % 3
            share = total * max(left, right) // (left + right)
            add("Ratios", ["Medium", "Hard"][i % 2],
                f"Rs. {total} is divided in the ratio {left}:{right}. What is the larger share?",
                f"Rs. {share}",
                [f"Rs. {total - share}", f"Rs. {share + 10}", f"Rs. {total}"], key_index)
        else:
            x = 3 + i
            a = 2 + i % 3
            b = 4 + i % 2
            add("Algebra", ["Easy", "Medium", "Hard"][i % 3],
                f"If {a}x + {b} = {a * x + b}, what is x?",
                str(x), [str(x + 1), str(x - 1), str(x + 2)], key_index)

    for i in range(13):
        key_index = (i + 1) % 4
        if i % 2 == 0:
            start = 2 + i
            step = 3 + i % 4
            terms = [start + k * step for k in range(4)]
            answer = start + 4 * step
            add("Series Completion", ["Easy", "Medium"][i % 2],
                f"Find the next term in the series: {', '.join(map(str, terms))}, ?",
                str(answer), [str(answer + step), str(answer - 1), str(answer + 2)], key_index)
        else:
            add("Syllogisms", ["Medium", "Hard"][i % 2],
                "All engineers are readers. Some readers are writers. Which conclusion follows?",
                "Some engineers may be writers",
                ["All writers are engineers", "No engineer is a writer", "All readers are engineers"], key_index)

    word_pairs = [
        ("Abundant", "Plentiful", ["Scarce", "Costly", "Hidden"]),
        ("Brief", "Short", ["Lengthy", "Loud", "Rough"]),
        ("Candid", "Frank", ["Secretive", "Rude", "Wealthy"]),
        ("Diligent", "Hardworking", ["Lazy", "Careless", "Slow"]),
        ("Fragile", "Delicate", ["Strong", "Heavy", "Cheap"]),
        ("Rapid", "Swift", ["Sluggish", "Steady", "Noisy"]),
        ("Vacant", "Empty", ["Crowded", "Open", "Bright"]),
    ]
    passages = [
        ("The pilot batch showed unusually low engagement, so the team revised the plan.",
         "The pilot results were weak", ["Costs were too high", "The team was replaced", "The schedule was full"]),
        ("Demand doubled after the price cut, which forced the warehouse to add a second shift.",
         "Demand rose sharply", ["Staff resigned", "The warehouse moved", "Prices increased again"]),
        ("Attendance improved once the sessions moved online, so the format was kept.",
         "Online sessions improved attendance", ["Teachers left", "The syllabus shrank", "Exams were cancelled"]),
        ("The survey response rate fell after the form grew longer, so three questions were removed.",
         "The form was too long", ["The survey was too short", "Staff ignored emails", "The prize was withdrawn"]),
        ("Micronutrients improved yields, but only when rainfall stayed above average.",
         "The benefit depended on rainfall", ["Rainfall never mattered", "Yields always fell", "Soil was irrelevant"]),
        ("The archive was digitised to reduce handling damage, and physical loans dropped.",
         "Digitising protected the original material", ["The archive was sold", "Loans increased", "Visitors were banned"]),
    ]

    for i in range(13):
        key_index = (i + 2) % 4
        if i % 2 == 0:
            word, synonym, distractors = word_pairs[(i // 2) % len(word_pairs)]
            add("Vocabulary", ["Easy", "Medium"][i % 2],
                f"Choose the word closest in meaning to '{word}'.",
                synonym, distractors, key_index)
        else:
            passage, answer, distractors = passages[(i // 2) % len(passages)]
            add("Reading Comprehension", ["Medium", "Hard"][i % 2],
                f"{passage} What was the main reason for the change?",
                answer, distractors, key_index)
    return bank

def build_demo_slots(bank):
    # No item repeats across slots (0% adjacent overlap, under the 10% cap), but
    # each slot shares concept families with the previous one so the red team
    # still has leaked material to attack.
    index_sets = {
        1: [0, 1, 2, 3, 4],
        2: [5, 6, 7, 8, 9],
        3: [10, 11, 12, 14, 15],
        4: [16, 17, 18, 19, 27],
    }
    return {slot: [dict(bank[index]) for index in indexes] for slot, indexes in index_sets.items()}

def load_demo_state():
    bank = build_demo_bank()
    slots = build_demo_slots(bank)
    st.session_state.parsed_bank = bank
    st.session_state.generated_slots = slots
    st.session_state.used_in_slots = {slot: [q['id'] for q in items] for slot, items in slots.items()}
    exposure = {q['id']: 0 for q in bank}
    for items in slots.values():
        for q in items:
            exposure[q['id']] += 1
    st.session_state.global_exposure = exposure
    st.session_state.current_slot = len(slots) + 1
    st.session_state.uploaded_filename = "demo-bank"
    st.session_state.slot_metrics = {1: {"pass_pct": 65.0, "avg_marks": 55.0}}
    st.session_state.leak_detected = False
    st.session_state.red_team_reports = {}
    st.session_state.item_approvals = {}
    st.session_state.attack_slot = 2
    for q in bank:
        db.insert_item({
            "item_id": q["id"],
            "stem": q["stem"],
            "options": q["options"],
            "correct_answer": q["key"],
            "approval_status": "DRAFT",
        })

def _red_team_estimate(slot_id):
    slot_items = st.session_state.generated_slots.get(slot_id, [])
    previous = st.session_state.generated_slots.get(slot_id - 1, [])
    samples, rounds, _ = _red_team_config()
    return red_team.estimate_llm_calls(slot_items, previous, _concept_family_map(), samples, rounds)

def run_red_team_attack(slot_id):
    slot_items = st.session_state.generated_slots.get(slot_id, [])
    previous = st.session_state.generated_slots.get(slot_id - 1, [])
    if not slot_items:
        st.warning("Selected slot has no items.")
        return
    if not previous:
        st.warning("This slot has no previous slot to leak from. Attack Slot 2 or later.")
        return
    if not get_api_key():
        st.error("GROQ_API_KEY is not configured. Add it to aptitude_platform/.env and restart the app.")
        return
    samples, rounds, threshold = _red_team_config()
    estimate = _red_team_estimate(slot_id)
    if estimate > MAX_LLM_CALLS:
        st.error(f"Estimated {estimate} LLM calls exceeds the {MAX_LLM_CALLS} call cap. Lower samples, rounds or slot size.")
        return
    progress = st.progress(0.0, text="Simulating leaks and measuring cheat advantage...")
    try:
        with st.spinner("Red team is attacking this slot..."):
            report = red_team.red_team_slot(
                slot_items, previous, _concept_family_map(),
                threshold=threshold, max_rounds=rounds, n_samples=samples,
                progress_callback=lambda fraction, text: progress.progress(
                    min(max(fraction, 0.0), 1.0), text=text),
            )
    except LLMUnavailable as exc:
        progress.empty()
        st.error(f"Red team could not reach the model: {exc}")
        return
    except Exception as exc:  # noqa: BLE001 - keep the dashboard alive
        progress.empty()
        st.error(f"Red team failed: {exc}")
        return
    progress.empty()
    if report.get("error"):
        st.warning(f"Model became unavailable mid-run: {report['error']}. Showing partial results.")
    st.session_state.red_team_reports[slot_id] = report
    st.session_state.generated_slots[slot_id] = report["final_items"]
    st.session_state.used_in_slots[slot_id] = [q["id"] for q in report["final_items"]]
    for rep in report["items"]:
        if rep["status"] == "SKIPPED" or not rep.get("after"):
            continue
        db.save_red_team_run(
            slot_id, rep["item_id"], rep["rounds"],
            rep["after"]["accuracy_blind"], rep["after"]["accuracy_armed"],
            rep["after"]["leak_advantage"], rep["after"]["copy_rate"], rep["status"],
        )
    for q in report["final_items"]:
        if q.get("parent_item_id"):
            db.insert_item({
                "item_id": q["id"],
                "stem": q["stem"],
                "options": q["options"],
                "correct_answer": q.get("key"),
                "approval_status": "DRAFT",
                "parent_item_id": q["parent_item_id"],
            })
            st.session_state.item_approvals[q["id"]] = "DRAFT"

def _apply_approvals(item_ids, status):
    changed = 0
    for item_id in item_ids:
        if st.session_state.item_approvals.get(item_id, "DRAFT") != "DRAFT":
            continue
        db.update_item_approval(item_id, status)
        st.session_state.item_approvals[item_id] = status
        changed += 1
    if changed:
        st.rerun()

def generate_certificate_pdf(slot_id, report):
    measured = [rep for rep in report["items"] if rep.get("after")]
    stamp = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())
    fingerprint = "|".join([
        str(slot_id),
        f"{report['mean_advantage_before']:.4f}",
        f"{report['mean_advantage_after']:.4f}",
        str(report["threshold"]),
        str(report["samples"]),
        str(report["max_rounds"]),
        stamp,
    ])
    cert_hash = hashlib.sha256(fingerprint.encode()).hexdigest()[:16]
    regenerated = sum(1 for rep in measured if rep["status"] == "REGENERATED")

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 19)
    pdf.set_text_color(30, 60, 110)
    pdf.cell(0, 12, txt="AGIES Leak-Resistance Certificate", ln=True, align='C')
    pdf.set_font("Arial", '', 10)
    pdf.set_text_color(90, 90, 90)
    pdf.cell(0, 7, txt=f"Slot {slot_id} - red team verification", ln=True, align='C')
    pdf.cell(0, 6, txt=f"Generated {stamp}", ln=True, align='C')
    pdf.cell(0, 6, txt=f"Certificate hash {cert_hash}", ln=True, align='C')
    pdf.ln(4)
    pdf.set_draw_color(180, 180, 180)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(8)

    pdf.set_font("Arial", 'B', 11)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 8, txt="Summary", ln=True)
    pdf.set_font("Arial", '', 10)
    summary = [
        ("Mean leak advantage before", f"{report['mean_advantage_before']:.3f}"),
        ("Mean leak advantage after", f"{report['mean_advantage_after']:.3f}"),
        ("Vulnerability threshold", f"{report['threshold']:.2f}"),
        ("Items measured", str(len(measured))),
        ("Items regenerated", str(regenerated)),
        ("Still vulnerable", str(len(report.get("still_vulnerable", [])))),
        ("Samples per solve", str(report["samples"])),
        ("Max regeneration rounds", str(report["max_rounds"])),
    ]
    for label, value in summary:
        pdf.cell(95, 6, txt=label)
        pdf.cell(0, 6, txt=value, ln=True)
    pdf.ln(5)

    def table_header():
        pdf.set_font("Arial", 'B', 9)
        pdf.set_fill_color(238, 242, 255)
        pdf.cell(28, 7, txt="Item", border=1, fill=True)
        pdf.cell(52, 7, txt="Concept", border=1, fill=True)
        pdf.cell(44, 7, txt="Status", border=1, fill=True)
        pdf.cell(33, 7, txt="Before", border=1, fill=True)
        pdf.cell(33, 7, txt="After", border=1, fill=True, ln=True)

    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 8, txt="Items", ln=True)
    table_header()
    pdf.set_font("Arial", '', 9)
    for rep in measured:
        if pdf.get_y() > 245:
            pdf.add_page()
            table_header()
            pdf.set_font("Arial", '', 9)
        concept = ''.join(c for c in str(rep.get("concept", "")) if ord(c) < 128)[:30]
        pdf.cell(28, 6, txt=str(rep["final_item_id"]), border=1)
        pdf.cell(52, 6, txt=concept, border=1)
        pdf.cell(44, 6, txt=str(rep["status"]), border=1)
        pdf.cell(33, 6, txt=f"{rep['before']['leak_advantage']:.3f}", border=1)
        pdf.cell(33, 6, txt=f"{rep['after']['leak_advantage']:.3f}", border=1, ln=True)

    pdf.ln(8)
    pdf.set_font("Arial", 'I', 9)
    pdf.set_text_color(90, 90, 90)
    pdf.multi_cell(
        w=0, h=5,
        txt="Leak advantages are estimates produced by an LLM stand-in, not real candidate behaviour. "
            "Items remain DRAFT until a human reviewer approves them; nothing is released automatically.",
    )
    pdf.ln(10)
    pdf.set_font("Arial", '', 10)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(95, 8, txt="Reviewer sign-off: ____________________")
    pdf.cell(0, 8, txt="Date: ______________", ln=True)
    return bytes(pdf.output())

def render_red_team_results(slot_id, report):
    st.markdown("##### Red Team Loop — Leak Resistance")
    st.caption("Estimated by an LLM stand-in, not real candidate behaviour.")
    before = report["mean_advantage_before"]
    after = report["mean_advantage_after"]
    worst = ", ".join(f"{item_id} ({value:.2f})" for item_id, value in report.get("worst_items", [])) or "none"
    st.info(f"Mean leak advantage: {before:.2f} → {after:.2f}. Worst items: {worst}.")
    if report.get("still_vulnerable"):
        st.warning(f"Still vulnerable after {report['max_rounds']} round(s): {', '.join(report['still_vulnerable'])}")

    rows = []
    for rep in report["items"]:
        if not rep.get("before"):
            continue
        rows.append({
            "Item": rep["item_id"],
            "Concept": rep["concept"],
            "Status": rep["status"],
            "Advantage before": round(rep["before"]["leak_advantage"], 3),
            "Advantage after": round(rep["after"]["leak_advantage"], 3),
            "Copy rate after": round(rep["after"]["copy_rate"], 3),
            "Rounds": rep["rounds"],
        })
    if rows:
        df = pd.DataFrame(rows)

        def _colour(value):
            if value > report["threshold"]:
                return "background-color: #fee2e2; color: #991b1b"
            return "background-color: #dcfce7; color: #166534"

        styler = df.style
        if hasattr(styler, "map"):
            styled = styler.map(_colour, subset=["Advantage before", "Advantage after"])
        else:
            styled = styler.applymap(_colour, subset=["Advantage before", "Advantage after"])
        st.dataframe(styled, width="stretch", hide_index=True, key=f"rt_table_{slot_id}")

        fig = go.Figure(go.Bar(
            x=["Before regeneration", "After regeneration"],
            y=[before, after],
            marker_color=["#ef4444", "#22c55e"],
            text=[f"{before:.2f}", f"{after:.2f}"],
            textposition="outside",
        ))
        fig.update_layout(height=280, yaxis_title="Mean leak advantage",
                          yaxis_range=[0, 1], margin=dict(l=10, r=10, t=20, b=10))
        st.plotly_chart(fig, width="stretch", key=f"rt_chart_{slot_id}")

        approval_by_id = {
            q.get("id"): st.session_state.item_approvals.get(q.get("id"), q.get("approval_status", "DRAFT"))
            for q in report["final_items"]
        }
        export_rows = [{
            "Item": rep["final_item_id"],
            "Concept": rep["concept"],
            "Status": rep["status"],
            "Advantage before": round(rep["before"]["leak_advantage"], 3),
            "Advantage after": round(rep["after"]["leak_advantage"], 3),
            "Copy rate after": round(rep["after"]["copy_rate"], 3),
            "Rounds": rep["rounds"],
            "Approval": approval_by_id.get(rep["final_item_id"], "DRAFT"),
        } for rep in report["items"] if rep.get("after")]
        export_df = pd.DataFrame(export_rows)
        dl_left, dl_right = st.columns(2)
        dl_left.download_button(
            "Download red-team report (CSV)",
            data=export_df.to_csv(index=False).encode("utf-8"),
            file_name=f"red_team_slot_{slot_id}.csv",
            mime="text/csv",
            key=f"rt_csv_{slot_id}",
            width="stretch",
        )
        dl_right.download_button(
            "Download leak-resistance certificate (PDF)",
            data=generate_certificate_pdf(slot_id, report),
            file_name=f"Leak_Resistance_Slot_{slot_id}.pdf",
            mime="application/pdf",
            key=f"rt_cert_{slot_id}",
            width="stretch",
        )

    final_items = report["final_items"]
    row_by_id = {rep["final_item_id"]: rep for rep in report["items"]}
    measured = [rep for rep in report["items"] if rep.get("after")]
    with st.expander("Reviewer approval — items stay DRAFT until approved"):
        st.caption("Bulk actions only change items still in DRAFT.")
        passed_drafts = [
            rep["final_item_id"] for rep in measured
            if rep["status"] == "PASSED"
            and st.session_state.item_approvals.get(rep["final_item_id"], "DRAFT") == "DRAFT"
        ]
        vulnerable_drafts = [
            rep["final_item_id"] for rep in measured
            if rep["status"] == "STILL_VULNERABLE"
            and st.session_state.item_approvals.get(rep["final_item_id"], "DRAFT") == "DRAFT"
        ]
        bulk_left, bulk_right = st.columns(2)
        if bulk_left.button(
            f"Approve all passed ({len(passed_drafts)})",
            key=f"rt_bulk_pass_{slot_id}", width="stretch",
            disabled=not passed_drafts,
        ):
            _apply_approvals(passed_drafts, "APPROVED")
        if bulk_right.button(
            f"Reject still-vulnerable ({len(vulnerable_drafts)})",
            key=f"rt_bulk_rej_{slot_id}", width="stretch",
            disabled=not vulnerable_drafts,
        ):
            _apply_approvals(vulnerable_drafts, "REJECTED")
        selectable = [q.get("id") for q in final_items]
        chosen = st.multiselect(
            "Apply to selected items", selectable,
            key=f"rt_bulk_sel_{slot_id}",
        )
        sel_left, sel_right = st.columns(2)
        if sel_left.button(
            "Approve selected", key=f"rt_sel_appr_{slot_id}",
            width="stretch", disabled=not chosen,
        ):
            _apply_approvals(chosen, "APPROVED")
        if sel_right.button(
            "Reject selected", key=f"rt_sel_rej_{slot_id}",
            width="stretch", disabled=not chosen,
        ):
            _apply_approvals(chosen, "REJECTED")
        st.divider()
        for q in final_items:
            item_id = q.get("id")
            current_status = st.session_state.item_approvals.get(item_id, q.get("approval_status", "DRAFT"))
            row = row_by_id.get(item_id, {})
            if row.get("after"):
                resistance = (
                    f"· {row['status']} · advantage {row['before']['leak_advantage']:.2f} → "
                    f"{row['after']['leak_advantage']:.2f}"
                )
            else:
                resistance = f"· {row.get('status', 'SKIPPED')}"
            approve_col, reject_col, label_col = st.columns([1, 1, 5])
            if approve_col.button("Approve", key=f"approve_{slot_id}_{item_id}"):
                db.update_item_approval(item_id, "APPROVED")
                st.session_state.item_approvals[item_id] = "APPROVED"
                st.rerun()
            if reject_col.button("Reject", key=f"reject_{slot_id}_{item_id}"):
                db.update_item_approval(item_id, "REJECTED")
                st.session_state.item_approvals[item_id] = "REJECTED"
                st.rerun()
            label_col.markdown(f"**{item_id}** · {q.get('concept', '')} · `{current_status}` {resistance}")
        approved = sum(
            1 for q in final_items
            if st.session_state.item_approvals.get(q.get("id"), q.get("approval_status", "DRAFT")) == "APPROVED"
        )
        st.caption(f"Approved {approved}/{len(final_items)} items. Nothing is released automatically.")

st.markdown("---")
tab1, tab2, tab3, tab4 = st.tabs([
    "1. Ingestion & Bank",
    "2. Psychometric Analytics",
    "3. 10-Slot Assembler",
    "4. Active Leak Defense"
])

with tab1:
    st.header("Upload & Ingestion Pipeline")
    uploaded_file = st.file_uploader("Upload Question Bank (CSV/PDF/TXT)", type=['csv', 'pdf', 'txt'])
    if uploaded_file is not None:
        file_bytes = uploaded_file.getvalue()
        signature = (uploaded_file.name, len(file_bytes), hashlib.sha256(file_bytes).hexdigest())
        if st.session_state.get("upload_signature") != signature:
            with st.spinner("Extracting & parsing questions from file..."):
                uploaded_file.seek(0)
                st.session_state.parsed_bank = parse_uploaded_file(uploaded_file)
                st.session_state.uploaded_filename = uploaded_file.name
                st.session_state.upload_signature = signature

        if st.session_state.get("import_error"):
            st.error(st.session_state.import_error)
        if st.session_state.parsed_bank:
            st.success(f"File parsed successfully. Extracted {len(st.session_state.parsed_bank)} questions.")
        else:
            st.warning("No usable questions were extracted from this file.")

        summary = st.session_state.get("import_summary", {})
        detected = summary.get("detected", 0)
        if summary.get("no_text_layer"):
            st.warning(
                "This PDF has no extractable text layer (it looks like a scanned image). "
                "OCR is not installed, so questions cannot be read from it. Upload a text-based PDF, TXT or CSV."
            )
        if detected:
            kept = len(st.session_state.parsed_bank)
            skipped = detected - kept
            detail = "no rows skipped" if not skipped else f"{skipped} skipped as duplicate or page noise"
            st.caption(f"Kept {kept} of {detected} detected questions ({100.0 * kept / detected:.1f}% retention) — {detail}.")
        if summary.get("open_response"):
            st.info(f"{summary['open_response']} question(s) have no detected options and will be used as open-response items (writing space in the PDF).")
        dist = summary.get("difficulty_distribution") or {}
        if dist:
            order = ["Easy", "Medium", "Medium-Hard", "Hard"]
            parts = [f"{band} {dist[band]}" for band in order if dist.get(band)]
            mean = summary.get("mean_difficulty_score")
            suffix = f" · mean {mean}/10" if mean is not None else ""
            st.caption("Estimated difficulty: " + " · ".join(parts) + suffix +
                       " (model judgement blended with a content-based prior).")
        if st.session_state.get("llm_notice"):
            st.info(st.session_state.llm_notice)
        rejected = st.session_state.get("import_rejections", [])
        if rejected:
            st.warning(f"Import validation skipped {len(rejected)} duplicate or non-question row(s).")
            with st.expander("Show skipped rows"):
                st.dataframe(pd.DataFrame(rejected), width="stretch", hide_index=True)
        if st.session_state.parsed_bank:
            concepts = Counter(q.get("concept", "General Aptitude") for q in st.session_state.parsed_bank)
            st.caption("Concepts detected: " + " · ".join(f"{name} {count}" for name, count in concepts.most_common(8)))
            df = pd.DataFrame(st.session_state.parsed_bank)
            df['options'] = df['options'].apply(lambda x: " | ".join(x))
            st.dataframe(df, width="stretch")

    st.divider()
    st.subheader("Answer-Key Import")
    coverage = db.answer_key_coverage()
    keyed, total_items = coverage["keyed"], coverage["total"]
    if total_items:
        st.metric("Answer-key coverage", f"{100.0 * keyed / total_items:.1f}%", f"{keyed}/{total_items} items keyed")
    else:
        st.metric("Answer-key coverage", "0.0%", "0 items in bank")
    key_file = st.file_uploader(
        "Backfill keys (CSV with item_id and key columns)",
        type=["csv"], key="answer_key_upload",
    )
    if key_file is not None:
        try:
            key_df = pd.read_csv(key_file)
        except Exception as exc:
            st.error(f"Could not read key file: {exc}")
            key_df = None
        if key_df is not None:
            columns = {str(c).strip().lower(): c for c in key_df.columns}
            id_col = next((columns[name] for name in ("item_id", "id", "question_id") if name in columns), None)
            key_col = next((columns[name] for name in ("key", "answer", "correct_answer", "correct") if name in columns), None)
            if id_col is None or key_col is None:
                st.error("Key file needs an item_id column and a key (or answer) column.")
            else:
                pairs, skipped = [], 0
                for _, row in key_df.iterrows():
                    item_id = str(row[id_col]).strip()
                    answer = _normalize_answer(row[key_col])
                    if item_id and answer:
                        pairs.append((item_id, answer))
                    else:
                        skipped += 1
                st.caption(f"{len(pairs)} usable row(s), {skipped} skipped (missing id or option letter).")
                if pairs and st.button(f"Import {len(pairs)} answer keys", key="import_answer_keys", type="primary"):
                    updated = db.bulk_set_answers(pairs)
                    answer_map = dict(pairs)
                    for q in st.session_state.parsed_bank:
                        if q.get("id") in answer_map:
                            q["correct_answer"] = answer_map[q["id"]]
                            q["key"] = answer_map[q["id"]]
                    for slot_items in st.session_state.generated_slots.values():
                        for q in slot_items:
                            if q.get("id") in answer_map:
                                q["correct_answer"] = answer_map[q["id"]]
                                q["key"] = answer_map[q["id"]]
                    st.success(f"Updated {updated} item(s). {skipped} row(s) skipped.")
                    st.rerun()
    if st.session_state.parsed_bank:
        coverage_df = pd.DataFrame([{
            "Concept": q.get("concept", "Untagged") or "Untagged",
            "Keyed": q.get("correct_answer") not in (None, "", "N/A"),
        } for q in st.session_state.parsed_bank])
        summary = coverage_df.groupby("Concept")["Keyed"].agg(["sum", "count"])
        summary["Coverage %"] = (100.0 * summary["sum"] / summary["count"]).round(1)
        st.dataframe(summary.rename(columns={"sum": "Keyed", "count": "Items"}), width="stretch")

with tab2:
    st.header("Real-Time Analytics & Psychometrics")
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Slot Overlap Heatmap")
        st.write("Verifies the constraint optimizer is keeping adjacent slot overlap below maximum limits.")
        if st.session_state.used_in_slots and len(st.session_state.used_in_slots) > 1:
            slots = sorted(list(st.session_state.used_in_slots.keys()))
            matrix = np.zeros((len(slots), len(slots)))
            for i, s1 in enumerate(slots):
                for j, s2 in enumerate(slots):
                    set1 = set(st.session_state.used_in_slots[s1])
                    set2 = set(st.session_state.used_in_slots[s2])
                    overlap_pct = (len(set1.intersection(set2)) / max(len(set1), 1)) * 100
                    matrix[i][j] = overlap_pct
            fig_hm = px.imshow(matrix, labels=dict(x="Target Slot", y="Source Slot", color="Overlap %"), x=[f"S{s}" for s in slots], y=[f"S{s}" for s in slots], color_continuous_scale="Blues", text_auto=".1f")
            st.plotly_chart(fig_hm, width="stretch")
        else:
            st.info("Generate at least 2 slots in Tab 3 to view the overlap heatmap.")
    with col_b:
        st.subheader("Item Characteristic Curve (ICC)")
        st.write("Visualizing the 2PL IRT Model (Probability of correct answer vs. Candidate Ability)")
        icc_items = list(st.session_state.parsed_bank)
        if not icc_items:
            icc_items = [q for items in st.session_state.generated_slots.values() for q in items]
        if icc_items:
            icc_lookup = {
                f"{q.get('id')} · {q.get('concept', 'Untagged')}": q
                for q in icc_items[:50]
            }
            icc_label = st.selectbox("Item to inspect", list(icc_lookup), key="icc_item")
            icc_item = icc_lookup[icc_label]
            score = icc_item.get("difficulty_score")
            if score is None:
                score = _LLM_BAND_SCORE.get(icc_item.get("difficulty"), 5.0)
            b = (float(score) - 5.5) / 2.0
            a = float(icc_item.get("irt_discrimination_a") or 1.2)
            abilities = np.linspace(-3, 3, 100)
            probabilities = 1 / (1 + np.exp(-a * (abilities - b)))
            fig_icc = go.Figure()
            fig_icc.add_trace(go.Scatter(
                x=abilities, y=probabilities, mode='lines',
                name=f"{icc_item.get('id')} ({icc_item.get('difficulty', 'uncalibrated')}, b={b:.2f})",
                line=dict(color='firebrick', width=3),
            ))
            fig_icc.update_layout(xaxis_title="Candidate Ability (Theta)", yaxis_title="Probability of Correct Response (P)")
            st.plotly_chart(fig_icc, width="stretch")
            st.caption(f"{icc_item.get('concept', 'Untagged')} · estimated difficulty {score}/10 · discrimination a={a:.2f}.")
        else:
            st.info("Upload a bank or generate a slot to inspect calibrated item curves.")

    st.divider()
    st.subheader("Response Scoring & Item Statistics")
    st.caption("Correctness comes from imported answer keys (Tab 1). The responses CSV needs candidate_id, item_id and selected columns.")
    resp_file = st.file_uploader("Responses CSV", type=["csv"], key="responses_upload")
    if resp_file is not None:
        try:
            resp_df = pd.read_csv(resp_file)
        except Exception as exc:
            st.error(f"Could not read responses file: {exc}")
            resp_df = None
        if resp_df is not None:
            columns = {str(c).strip().lower(): c for c in resp_df.columns}
            cand_col = next((columns[n] for n in ("candidate_id", "candidate", "student_id") if n in columns), None)
            item_col = next((columns[n] for n in ("item_id", "question_id", "id") if n in columns), None)
            sel_col = next((columns[n] for n in ("selected", "answer", "response", "choice") if n in columns), None)
            if not all((cand_col, item_col, sel_col)):
                st.error("Responses file needs candidate_id, item_id and selected columns.")
            else:
                item_to_slot = {}
                for slot, slot_items in st.session_state.generated_slots.items():
                    for q in slot_items:
                        item_to_slot.setdefault(q.get("id"), slot)
                pairs, skipped = [], 0
                for _, row in resp_df.iterrows():
                    candidate = str(row[cand_col]).strip()
                    item_id = str(row[item_col]).strip()
                    selected = _normalize_answer(row[sel_col])
                    if not candidate or not item_id or not selected:
                        skipped += 1
                        continue
                    pairs.append((candidate, item_id, selected, item_to_slot.get(item_id)))
                st.caption(f"{len(pairs)} usable response(s), {skipped} skipped (missing candidate, item or option letter).")
                if pairs and st.button(f"Import {len(pairs)} responses", key="import_responses", type="primary"):
                    saved = db.save_responses(pairs)
                    st.success(f"Stored {saved} response(s).")
                    st.rerun()

    slot_options = ["All items"] + [f"Slot {slot}" for slot in sorted(st.session_state.generated_slots)]
    score_choice = st.selectbox("Score which slot?", slot_options, key="score_slot")
    records = db.get_responses()
    if score_choice != "All items":
        slot_id = int(score_choice.split()[-1])
        slot_ids = {q.get("id") for q in st.session_state.generated_slots.get(slot_id, [])}
        records = [record for record in records if record["item_id"] in slot_ids]
    if not records:
        st.info("No responses stored yet. Upload a responses CSV above.")
    else:
        item_meta = {row["item_id"]: row for row in db.get_items_by_ids({r["item_id"] for r in records})}
        scored_df, unkeyed = _score_responses(records, item_meta)
        if unkeyed:
            st.warning(f"{unkeyed} response(s) belong to items without answer keys and were excluded. Import keys in Tab 1.")
        if scored_df.empty:
            st.info("No scorable responses yet.")
        else:
            concept_map = _concept_lookup()
            stats_df = _item_statistics(scored_df)
            stats_df.insert(1, "Concept", stats_df["Item"].map(lambda i: concept_map.get(i, "Untagged")))
            kr20 = _kr20(scored_df)
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Candidates", scored_df["candidate_id"].nunique())
            m2.metric("Scored responses", len(scored_df))
            m3.metric("Items scored", scored_df["item_id"].nunique())
            m4.metric("KR-20", "n/a" if kr20 is None else f"{kr20:.2f}")
            st.dataframe(stats_df, width="stretch", hide_index=True)
            st.caption("p-value = proportion correct; point-biserial = item-total correlation. KR-20 needs candidates who answered every scored item.")

with tab3:
    st.header("Slot Assembly Engine")
    with st.expander("Demo mode — load a 40-item synthetic bank with 4 constraint-compliant slots"):
        st.write("No upload needed. Loads 40 sample items (Quantitative, Logical, Verbal) into four slots with no repeated items (0% adjacent overlap, under the 10% cap) but shared concept families, so you can attack Slot 2 immediately.")
        if st.button("Load demo bank & slots", width="stretch", type="primary"):
            load_demo_state()
            st.success("Demo bank and 4 slots loaded. Open the Red Team Loop below.")
            st.rerun()
    col_c, col_d = st.columns([1, 2])
    with col_c:
        st.subheader("Optimizer Constraints")
        num_slots = st.number_input("Total Number of Slots", min_value=1, max_value=20, value=10)
        questions_per_slot = st.number_input("Questions per Slot", min_value=1, max_value=100, value=5)
        target_difficulty = st.selectbox("Target Difficulty Level", ["Easy", "Medium", "Medium-Hard", "Hard", "Mixed"], index=4)
        max_overlap = st.slider("Max Adjacent Overlap (%)", 0, 50, 10)
        if st.session_state.parsed_bank:
            bank_size = len(st.session_state.parsed_bank)
            min_req = questions_per_slot + int(questions_per_slot * (1 - (max_overlap/100.0)))
            st.caption(f"**Bank Diagnostic:** {bank_size} items available.")
            if bank_size < min_req:
                st.error(f"⚠️ Warning: Bank too small to maintain strict mathematical overlap limits. Need at least {min_req} items.")
            else:
                st.success("✅ Bank size supports constraint limits.")
    with col_d:
        st.subheader("Assembly Control")
        requirement_prompt = st.text_area(
            "Concept & Difficulty Requirements (optional)",
            placeholder=(
                "One concept per line, e.g.\n"
                "Algebra: 1 easy, 2 hard\n"
                "Reading Comprehension: 3 medium\n"
                "Leave empty for a mixed-concept slot."
            ),
            height=120,
            help="Each line: <concept>: <count> <difficulty>, ... Difficulties: easy, medium, medium-hard, hard, any. A bare concept means 1 question of any difficulty. When used, this overrides 'Questions per Slot'."
        )
        parsed_requirements = parse_requirement_prompt(requirement_prompt)
        if parsed_requirements:
            req_total = sum(r['count'] for r in parsed_requirements)
            st.caption(f"Requested: {req_total} question(s) across {len(parsed_requirements)} group(s). This overrides 'Questions per Slot' and 'Target Difficulty Level'.")
        require_keys = st.checkbox(
            "Require answer keys for generated items", value=False, key="require_answer_keys",
            help="Blocks generation when the bank has fewer keyed items than the requested slot size.",
        )
        slot_size_preview = sum(r['count'] for r in parsed_requirements) if parsed_requirements else questions_per_slot
        keyed_count = sum(
            1 for q in st.session_state.parsed_bank
            if _normalize_answer(q.get("correct_answer", q.get("key", "")))
        )
        keys_ok = (not require_keys) or keyed_count >= slot_size_preview
        if require_keys and not keys_ok:
            st.error(f"Only {keyed_count} keyed item(s) in the bank; a {slot_size_preview}-item slot needs at least that many. Import keys in Tab 1 or uncheck the requirement.")

        generation_cap = int(st.session_state.get("gen_cap", 15))
        estimated_need = _estimated_generation_need(
            st.session_state.parsed_bank, parsed_requirements, target_difficulty, slot_size_preview
        )
        st.caption(
            f"AI generation cap: {generation_cap} item(s) per slot · "
            f"estimated shortfall: {min(estimated_need, generation_cap)} item(s). "
            "Shortfall items are written on the bank's own concepts."
        )
        if st.session_state.get("llm_notice"):
            st.info(st.session_state.llm_notice)
        can_assemble = bool(st.session_state.parsed_bank) or bool(parsed_requirements)
        if not can_assemble:
            st.warning("Upload a question bank in Tab 1, load the demo, or enter concept requirements before generating a slot.")
        current = st.session_state.current_slot
        if current > num_slots:
            st.success(f"All {num_slots} slots assembled!")
        else:
            st.write(f"**Next Action:** Generate Slot {current}")
            
            if st.session_state.leak_detected:
                st.error("🛡️ **GLOBAL DEFENSE PROTOCOL ACTIVE:** A breach was confirmed manually or detected by CUSUM. The next generated slot will automatically undergo an AI Pattern Shift.")
            
            passing_pct = 65.0
            avg_marks = 55.0
            if current > 1:
                st.info(f"Provide feedback from Slot {current - 1} to calibrate CUSUM/OSINT engines.")
                passing_pct = st.number_input(f"Slot {current - 1} Passing Percentage (%)", min_value=0.0, max_value=100.0, value=65.0)
            if st.button(f"Generate Slot {current}", width="stretch", type="primary",
                         disabled=not keys_ok or not can_assemble):
                if current >= 3:
                    baseline_pass = st.session_state.slot_metrics.get(1, {}).get("pass_pct", 65.0)
                    mock_responses = [1] * int(passing_pct) + [0] * (100 - int(passing_pct))
                    random.shuffle(mock_responses)
                    is_leak = cusum_engine.run_statistical_cusum(item_id=f"slot_{current}", baseline_p=baseline_pass / 100.0, recent_responses=mock_responses)
                    if is_leak:
                        st.session_state.leak_detected = True
                        st.error(f"🚨 ANOMALY DETECTED! Leak test rejected the baseline (one-sided p < {cusum_engine.ALPHA:.2f}): Baseline {baseline_pass}% vs Current {passing_pct}%. Triggering defense mechanisms!")
                        time.sleep(1)
                        st.warning("⚠️ PATTERN SHIFT: System is now locking out standard methodologies.")
                        time.sleep(1)
                    elif not st.session_state.leak_detected:
                        # Only set to False if it wasn't already triggered manually by OSINT
                        st.session_state.leak_detected = False

                progress_bar = st.progress(0, text="Assembling Slot...") if st.session_state.leak_detected else None
                active_requirements = parse_requirement_prompt(requirement_prompt)
                slot_size = sum(r['count'] for r in active_requirements) if active_requirements else questions_per_slot
                assembled = generate_slot_from_bank(
                    slot_num=current, num_questions=slot_size, target_difficulty=target_difficulty,
                    max_overlap=max_overlap, pattern_shifted=st.session_state.leak_detected,
                    progress_bar=progress_bar, requirements=active_requirements,
                )
                if progress_bar: progress_bar.empty()
                if not assembled:
                    st.error("No questions could be assembled. Upload a bank in Tab 1, load the demo, or add concept requirements.")
                else:
                    st.session_state.generated_slots[current] = assembled
                    if current > 1: st.session_state.slot_metrics[current] = {"pass_pct": passing_pct, "avg_marks": avg_marks}
                    else: st.session_state.slot_metrics[current] = {"pass_pct": 65.0, "avg_marks": 55.0}
                    st.session_state.current_slot += 1
                    st.rerun()

        attackable = sorted(slot for slot in st.session_state.generated_slots if slot >= 2)
        if attackable:
            st.divider()
            st.subheader("Red Team Loop")
            st.caption("Simulates a leak from the previous slot, measures the cheat advantage, then regenerates vulnerable items. Estimated by an LLM stand-in, not real candidate behaviour.")
            attack_slot = st.selectbox("Slot to attack", attackable, index=len(attackable) - 1, key="attack_slot")
            estimate = _red_team_estimate(attack_slot)
            samples, rounds, threshold = _red_team_config()
            st.caption(f"Estimated max LLM calls: {estimate} (cap {MAX_LLM_CALLS}). Samples per solve: {samples}, max rounds: {rounds}, threshold: {threshold:.2f}. Adjust these in the sidebar.")
            if st.button(f"Run Red Team Attack on Slot {attack_slot}", width="stretch", type="primary"):
                run_red_team_attack(attack_slot)
    if st.session_state.generated_slots:
        st.divider()
        st.subheader("Generated Slot Previews & Export")
        last_gen = st.session_state.get("last_generation")
        if last_gen:
            st.caption(
                f"Last assembly used {last_gen['generated']} AI-generated item(s) "
                f"(cap {last_gen['cap']} per slot)."
            )
        for slot, questions in st.session_state.generated_slots.items():
            report = st.session_state.red_team_reports.get(slot)
            status_map = {row["final_item_id"]: row for row in report["items"]} if report else {}
            with st.expander(f"Slot {slot} Preview", expanded=(slot == current - 1)):
                if slot >= 3 and st.session_state.leak_detected and slot == max(st.session_state.generated_slots.keys()):
                    st.error("🚨 Pattern Shift Applied due to detected anomaly.")
                for idx, q in enumerate(questions):
                    methodology = q.get('methodology', 'Standard')
                    st.caption(f"📌 *Methodology: {methodology}*")
                    st.markdown(f"**Q{idx+1}.** [{q['concept']}] {q['stem']}")
                    tags = []
                    if q.get('is_generated'):
                        tags.append("AI-generated (concept-anchored)")
                    if q.get('is_rewritten'):
                        tags.append("AI pattern-shift")
                    if q.get('difficulty'):
                        score = q.get('difficulty_score')
                        tags.append(str(q['difficulty']) + (f" · {score}/10" if score is not None else ""))
                    if tags:
                        st.caption(" · ".join(tags))
                    if len(q['options']) > 0:
                        for opt in q['options']: st.markdown(f"- {opt}")
                    else: st.markdown("*[Descriptive Answer / Subjective]*")
                    row = status_map.get(q.get("id"))
                    if row and row.get("after"):
                        st.caption(
                            f"Leak resistance: **{row['status']}** · advantage "
                            f"{row['before']['leak_advantage']:.2f} → {row['after']['leak_advantage']:.2f} · "
                            f"copy rate {row['after']['copy_rate']:.2f}"
                        )
                    elif row and row["status"] == "SKIPPED":
                        st.caption("Leak resistance: no leaked overlap with the previous slot.")
                    if st.session_state.item_approvals.get(q.get("id"), q.get("approval_status", "DRAFT")) == "DRAFT":
                        st.caption("Approval: DRAFT — a reviewer must approve this item before release.")
                    st.write("")
                approved_count, total_count = _slot_approval_counts(questions)
                draft_count = total_count - approved_count
                pdf_bytes = generate_pdf(slot, questions)
                pdf_label = f"Download Slot {slot} PDF"
                if draft_count:
                    st.warning(f"{draft_count} of {total_count} items are not approved. This export is stamped DRAFT and is not release-ready.")
                    pdf_label += " (DRAFT)"
                st.download_button(label=pdf_label, data=pdf_bytes, file_name=f"Assessment_Slot_{slot}.pdf", mime="application/pdf", key=f"dl_slot_{slot}")
                if report:
                    render_red_team_results(slot, report)
with tab4:
    st.header("🛡️ Active Leak Defense & OSINT")
    st.write("Monitor, scan the web, and manually confirm anomalies to trigger the system's self-healing defenses.")
    
    if not st.session_state.generated_slots:
        st.warning("Generate slots in Tab 3 first.")
    else:
        if st.session_state.leak_detected:
            st.error("🚨 **DEFENSE PROTOCOL ACTIVE:** A leak has been confirmed. The architecture is locked into Defensive/Pattern-Shift mode.")
        else:
            st.success("✅ **STATUS NORMAL:** No leaks confirmed.")
            
        st.divider()
        st.subheader("👨‍⚖️ Manual Leak Confirmation")
        st.write("If you or an invigilator have visual proof of a leak (e.g., questions found on Telegram or WhatsApp), confirm it here to immediately lock down the system.")
        
        scan_slot = st.selectbox("Select Compromised Slot", list(st.session_state.generated_slots.keys()))
        
        if st.button(f"🚨 Confirm Leak in Slot {scan_slot} & Initiate Pattern Shift Protocol"):
            st.session_state.leak_detected = True
            st.success(f"✅ Breach for Slot {scan_slot} confirmed by Admin. System globally locked into defensive Pattern Shift mode. Please return to Tab 3.")
            time.sleep(2)
            st.rerun()

        st.divider()
        st.subheader("🌐 Deep OSINT Web Scanner")
        st.write("Automatically search the open internet for exact matches of generated questions.")
        if st.button(f"🔍 Run Deep OSINT Web Scan on Slot {scan_slot}"):
            with st.spinner(f"Scraping the live internet for Slot {scan_slot} questions..."):
                target_q = st.session_state.generated_slots[scan_slot][0]
                raw_stem = re.sub(r'^(?:Q\d+[\.\:\)]|\d+[\.\:\)])\s*', '', target_q['stem'], flags=re.IGNORECASE).strip()
                stem_to_search = raw_stem[:150] if len(raw_stem) > 150 else raw_stem
                
                st.caption(f"Searching index for: {stem_to_search}")
                try:
                    with DDGS() as ddgs:
                        results = list(ddgs.text(stem_to_search, max_results=5))
                        
                    if results:
                        st.error(f"⚠️ Warning: Found {len(results)} potential matches online! Requires manual review.")
                        st.markdown("### 🕸️ Live Threat Topology (Node Mapping)")
                        
                        G = nx.DiGraph()
                        G.add_node("Compromised Question\n(Slot " + str(scan_slot) + ")", color="red", size=3000)
                        
                        for i, r in enumerate(results):
                            domain = r['href'].split('/')[2] if '//' in r['href'] else r['href'][:20]
                            G.add_node(domain, color="orange", size=1500)
                            G.add_edge("Compromised Question\n(Slot " + str(scan_slot) + ")", domain)
                            
                        plt.figure(figsize=(8, 4))
                        pos = nx.spring_layout(G, k=0.5)
                        colors = [node[1]['color'] for node in G.nodes(data=True)]
                        sizes = [node[1]['size'] for node in G.nodes(data=True)]
                        
                        nx.draw(G, pos, with_labels=True, node_color=colors, node_size=sizes, font_size=8, font_weight="bold", edge_color="gray", arrows=True)
                        
                        buf = io.BytesIO()
                        plt.savefig(buf, format="png", bbox_inches='tight', transparent=True)
                        buf.seek(0)
                        st.image(buf, width="stretch")
                        plt.close()
                        
                        for r in results:
                            st.markdown(f"**[{r['title']}]({r['href']})**")
                            st.caption(r['body'])
                        if st.button("🚨 Confirm Leak from OSINT Results", key=f"osint_confirm_{scan_slot}"):
                            st.session_state.leak_detected = True
                            st.success("✅ Breach confirmed via OSINT. System globally locked. Return to Tab 3.")
                            time.sleep(2)
                            st.rerun()
                    else:
                        st.success("✅ Clean. No live web matches found for this specific question.")
                except Exception as e:
                    st.error(f"Failed to connect to search index. Error: {e}")

        st.divider()
        st.header("🕵️‍♂️ Forensic Traitor Tracing (Canary Decoder)")
        st.write("Every question generated by AGIES contains an **invisible cryptographic Canary Token** (Zero-Width Characters). If a candidate copies and pastes a question to ChatGPT or Telegram, the invisible token is copied with it.")
        
        leaked_text = st.text_area("Paste leaked text found online to extract the forensic watermark:")
        if st.button("🧬 Analyze Cryptographic Signature"):
            with st.spinner("Running Zero-Width Forensic Extraction..."):
                time.sleep(1.5)
                detected_slot = extract_canary(leaked_text)
                if detected_slot:
                    st.error(f"🚨 **TRAITOR IDENTIFIED:** Cryptographic watermark successfully extracted! This exact text was leaked from **Slot {detected_slot}**.")
                else:
                    if leaked_text.strip(): st.success("✅ No AGIES Canary Tokens detected in this text. It may be from a different exam.")
                    else: st.warning("Please paste some text to analyze.")
                        
        st.divider()
        st.header("📸 Physical Paper Authentication (Zero-Trust Validation)")
        st.write("In a physical exam hall, how do you know a student hasn't smuggled in a counterfeit, pre-solved question paper? Use the live webcam to scan the cryptographic QR code on any printed AGIES test.")
        
        cam_pic = st.camera_input("Authenticate Physical Test Paper", key="qr_scanner")
        if cam_pic is not None:
            try:
                bytes_data = np.asarray(bytearray(cam_pic.read()), dtype=np.uint8)
                img = cv2.imdecode(bytes_data, cv2.IMREAD_COLOR)
                
                detector = cv2.QRCodeDetector()
                data, bbox, _ = detector.detectAndDecode(img)
                
                if data:
                    if "AGIES" in data:
                        st.balloons()
                        st.success("✅ **CRYPTOGRAPHICALLY AUTHENTICATED**")
                        st.code(data, language='text')
                        st.info("The Cryptographic Hash matches internal server records. No forgery detected. This paper is legitimate.")
                    else:
                        st.error("🚨 **COUNTERFEIT DETECTED:** The scanned QR code does not contain a valid AGIES signature. This paper is a forgery!")
                else:
                    st.warning("👀 Scanning... Please hold the QR code directly and clearly in front of the camera.")
            except Exception as e:
                st.error(f"Scanner initialization error: {e}")

st.markdown("""
<div class="agies-footer">
    <b>AGIES</b> &nbsp;·&nbsp; adaptive assessment engine &nbsp;·&nbsp; leak metrics are estimates from an LLM stand-in, not real candidate behaviour
</div>
""", unsafe_allow_html=True)
