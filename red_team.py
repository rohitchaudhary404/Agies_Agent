"""Red Team Loop: simulate a leak, measure the cheat advantage, harden items.

Every metric here is estimated by an LLM stand-in, not real candidate behaviour.
"""

import json
import re
import random
from collections import Counter

import sympy as sp

from services.llm import chat, LLMUnavailable

DEFAULT_THRESHOLD = 0.20
COPY_RATE_LIMIT = 0.5
MAX_REGENERATION_ATTEMPTS = 2
QUANT_WORDS = ("quant", "math", "algebra", "ratio", "percent", "arithmetic", "numeric", "geometry")


def _call(prompt, temperature=0.7, json_mode=False, chat_fn=None):
    return (chat_fn or chat)(prompt, temperature=temperature, json_mode=json_mode)


def _options_text(item):
    return "\n".join(str(opt) for opt in item.get("options", []))


def _loads_json(raw):
    if not raw:
        return None
    text = raw.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()
    else:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end != -1:
            text = text[start:end + 1]
    try:
        return json.loads(text)
    except (TypeError, ValueError):
        return None


def _parse_letter(raw, n_options):
    if not raw or n_options <= 0:
        return None
    upper = str(raw).upper()
    patterns = (
        r"ANSWER\s*(?:IS|:)?\s*\(?([A-Z])\)?",
        r"OPTION\s*\(?([A-Z])\)?",
        r"\(([A-Z])\)",
        r"^\s*([A-Z])\b",
    )
    for pattern in patterns:
        match = re.search(pattern, upper)
        if match and 0 <= ord(match.group(1)) - 65 < n_options:
            return match.group(1)
    for match in re.finditer(r"\b([A-Z])\b", upper):
        if 0 <= ord(match.group(1)) - 65 < n_options:
            return match.group(1)
    return None


def _item_key(item):
    raw = item.get("key") or item.get("correct_answer")
    if raw is None:
        return None
    raw = str(raw).strip()
    if not raw or raw.upper() == "N/A":
        return None
    options = item.get("options", [])
    upper = raw.upper()
    match = re.match(r"^\(?([A-Z])\)?\b", upper)
    if match and 0 <= ord(match.group(1)) - 65 < len(options):
        return match.group(1)
    lowered = raw.lower()
    for index, option in enumerate(options):
        if lowered in str(option).lower():
            return chr(65 + index)
    return None


def _accuracy(answers, key):
    if not answers or not key:
        return 0.0
    return sum(1 for answer in answers if answer == key) / len(answers)


def _majority(letters):
    valid = [letter for letter in letters if letter]
    if not valid:
        return None
    return Counter(valid).most_common(1)[0][0]


def simulate_leak(item, chat_fn=None):
    """Write the noisy Telegram post a leaker would publish for this item."""
    key = _item_key(item)
    prompt = f"""
    You are a student who just left an exam and is leaking a question on Telegram.
    Question:
    {item.get('stem', '')}

    Options:
    {_options_text(item)}

    The answer key I saw was option {key or 'unknown'}.
    Write a 2-4 sentence noisy recollection of the question, the answer, and a one-line
    solving trick. Keep it informal and slightly inaccurate, like a real leak.
    """
    return _call(prompt, temperature=0.9, chat_fn=chat_fn).strip()


def solve(item, leak_text=None, n_samples=3, chat_fn=None):
    """Answer the item n times; return the chosen option letters ('' if unparsed)."""
    expected = len(item.get("options", []))
    prompt = f"""
    Answer this multiple-choice question.

    Question:
    {item.get('stem', '')}

    Options:
    {_options_text(item)}
    """
    if leak_text:
        prompt += f"""

    Material you found online (may be incomplete or wrong):
    {leak_text}
    """
    prompt += """

    Reply with ONLY the chosen option letter (for example: B).
    """
    answers = []
    for _ in range(max(1, int(n_samples))):
        raw = _call(prompt, temperature=0.7, chat_fn=chat_fn)
        answers.append(_parse_letter(raw, expected) or "")
    return answers


def measure_item(target_item, leaked_items, n_samples=3, chat_fn=None, leak_cache=None):
    """Measure how much a leak dump helps an LLM cheater on the target item."""
    cache = leak_cache if leak_cache is not None else {}
    leak_parts = []
    for leaked in leaked_items:
        cache_key = leaked.get("id") or id(leaked)
        if cache_key not in cache:
            cache[cache_key] = simulate_leak(leaked, chat_fn=chat_fn)
        leak_parts.append(cache[cache_key])
    leak_dump = "\n\n---\n\n".join(leak_parts)

    blind_answers = solve(target_item, None, n_samples=n_samples, chat_fn=chat_fn)
    armed_answers = solve(target_item, leak_dump, n_samples=n_samples, chat_fn=chat_fn)

    key = _item_key(target_item)
    key_source = "item"
    if key is None:
        key = _majority(blind_answers)
        key_source = "inferred"

    accuracy_blind = _accuracy(blind_answers, key)
    accuracy_armed = _accuracy(armed_answers, key)
    leaked_letters = {_item_key(leaked) for leaked in leaked_items}
    leaked_letters.discard(None)
    copies = sum(1 for answer in armed_answers if answer and answer in leaked_letters and answer != key)
    copy_rate = copies / len(armed_answers) if armed_answers else 0.0

    return {
        "accuracy_blind": accuracy_blind,
        "accuracy_armed": accuracy_armed,
        "leak_advantage": accuracy_armed - accuracy_blind,
        "copy_rate": copy_rate,
        "blind_answers": blind_answers,
        "armed_answers": armed_answers,
        "key": key,
        "key_source": key_source,
    }


def _normalize_options(options):
    normalized = []
    for index, option in enumerate(list(options)[:6]):
        text = re.sub(r"^\s*[\(\[]?[A-Za-z][\.\)\:\-]\s*", "", str(option)).strip()
        if text:
            normalized.append(f"{chr(65 + index)}) {text}")
    return normalized


def _key_from_value(value, options):
    if isinstance(value, int) and 0 <= value < len(options):
        return chr(65 + value)
    if value is None:
        return None
    raw = str(value).strip()
    if len(raw) == 1 and raw.isalpha():
        letter = raw.upper()
        return letter if 0 <= ord(letter) - 65 < len(options) else None
    lowered = raw.lower()
    for index, option in enumerate(options):
        text = re.sub(r"^\s*[\(\[]?[A-Za-z][\.\)\:\-]\s*", "", str(option)).strip().lower()
        if lowered == text:
            return chr(65 + index)
    return None


def _looks_quantitative(item):
    blob = f"{item.get('section', '')} {item.get('concept', '')}".lower()
    return any(word in blob for word in QUANT_WORDS)


def _parse_number(option):
    text = re.sub(r"^\s*[\(\[]?[A-Za-z][\.\)\:\-]\s*", "", str(option)).strip()
    text = text.replace(",", "").replace("%", "").replace("$", "").replace("₹", "")
    try:
        return sp.sympify(text)
    except Exception:
        return None


def _sympy_ok(options, key_index):
    """Best-effort math check: reject duplicate key/distractor values."""
    key_expr = _parse_number(options[key_index])
    if key_expr is None:
        return True
    for index, option in enumerate(options):
        if index == key_index:
            continue
        other = _parse_number(option)
        if other is None:
            continue
        try:
            if sp.simplify(other - key_expr) == 0:
                return False
        except Exception:
            continue
    return True


def regenerate_item(item, chat_fn=None):
    """Rewrite an item with a different structure; return None if no valid variant."""
    key = _item_key(item)
    section = item.get("section", "General")
    difficulty = item.get("difficulty", "Medium")
    prompt = f"""
    You are an item writer hardening a leaked aptitude question.
    Original question:
    {item.get('stem', '')}

    Options:
    {_options_text(item)}
    Correct answer: {key or 'unknown'}
    Section: {section}
    Target difficulty: {difficulty}

    Write a BRAND NEW question that tests the same skill but with a DIFFERENT structure:
    new numbers, a new setup, and new distractors. Do not paraphrase the original.

    Respond in pure JSON with this exact schema:
    {{
        "stem": "the new question text",
        "options": ["option one", "option two", "option three", "option four"],
        "key": "B"
    }}
    """
    for _ in range(MAX_REGENERATION_ATTEMPTS):
        raw = _call(prompt, temperature=0.8, json_mode=True, chat_fn=chat_fn)
        data = _loads_json(raw)
        if not isinstance(data, dict):
            continue
        stem = str(data.get("stem", "")).strip()
        options = _normalize_options(data.get("options") or [])
        if not stem or len(options) < 2:
            continue
        key_letter = _key_from_value(data.get("key"), options)
        if key_letter is None:
            continue
        key_index = ord(key_letter) - 65
        if _looks_quantitative(item) and not _sympy_ok(options, key_index):
            continue
        return {
            "id": f"Q_{random.randint(100000, 999999)}",
            "stem": stem,
            "options": options,
            "key": key_letter,
            "correct_answer": key_letter,
            "concept": item.get("concept", "General Aptitude"),
            "section": section,
            "difficulty": difficulty,
            "methodology": item.get("methodology", "Standard"),
            "approval_status": "DRAFT",
            "parent_item_id": item.get("id"),
        }
    return None


def _concept_key(item):
    return str(item.get("concept", "")).strip().lower()


def _family_of(item, concept_families):
    if not isinstance(concept_families, dict):
        return None
    concept = str(item.get("concept", "")).strip()
    return concept_families.get(concept) or concept_families.get(concept.lower())


def _leaked_for(item, previous_items, concept_families):
    concept = _concept_key(item)
    family = _family_of(item, concept_families)
    leaked = []
    for previous in previous_items:
        same_item = previous.get("id") == item.get("id")
        same_concept = _concept_key(previous) == concept and concept != ""
        same_family = family is not None and _family_of(previous, concept_families) == family
        if same_item or same_concept or same_family:
            leaked.append(previous)
    return leaked


def is_vulnerable(metrics, threshold=DEFAULT_THRESHOLD):
    return metrics["leak_advantage"] > threshold or metrics["copy_rate"] > COPY_RATE_LIMIT


def estimate_llm_calls(slot_items, previous_slot_items, concept_families=None,
                       n_samples=3, max_rounds=3):
    """Upper-bound estimate of model calls for one red-team run."""
    cached_leaks = 0
    per_measure = 2 * max(1, int(n_samples))
    total = 0
    for item in slot_items:
        leaked = _leaked_for(item, previous_slot_items, concept_families)
        if not leaked:
            continue
        cached_leaks += len(leaked)
        total += (max_rounds + 1) * per_measure + max_rounds
    return total + cached_leaks


def red_team_slot(slot_items, previous_slot_items, concept_families=None,
                  threshold=DEFAULT_THRESHOLD, max_rounds=3, n_samples=3,
                  chat_fn=None, progress_callback=None):
    """Attack every item in a slot and harden the vulnerable ones.

    Returns per-item before/after metrics, rounds used, still-vulnerable ids and
    slot-level means. All numbers are LLM stand-in estimates.
    """
    total = max(1, len(slot_items))
    leak_cache = {}
    report_items = []
    final_items = []
    before_values = []
    after_values = []
    still_vulnerable = []
    error = None

    for index, item in enumerate(slot_items):
        leaked = _leaked_for(item, previous_slot_items, concept_families)
        original_id = item.get("id")
        if not leaked:
            final = dict(item)
            final["red_team_status"] = "SKIPPED"
            final_items.append(final)
            report_items.append({
                "item_id": original_id,
                "final_item_id": original_id,
                "concept": item.get("concept", ""),
                "section": item.get("section", ""),
                "status": "SKIPPED",
                "rounds": 0,
                "vulnerable": False,
                "leaked_count": 0,
                "before": None,
                "after": None,
            })
            if progress_callback:
                progress_callback((index + 1) / total, f"Skipped {original_id} (no leaked overlap)")
            continue

        try:
            before = measure_item(item, leaked, n_samples=n_samples,
                                  chat_fn=chat_fn, leak_cache=leak_cache)
            current = dict(item)
            current_metrics = before
            rounds = 0
            while is_vulnerable(current_metrics, threshold) and rounds < max_rounds:
                variant = regenerate_item(current, chat_fn=chat_fn)
                if variant is None:
                    break
                rounds += 1
                current = variant
                current_metrics = measure_item(current, leaked, n_samples=n_samples,
                                               chat_fn=chat_fn, leak_cache=leak_cache)
        except LLMUnavailable as exc:
            error = str(exc)
            final = dict(item)
            final["red_team_status"] = "STILL_VULNERABLE"
            final_items.append(final)
            break

        final_vulnerable = is_vulnerable(current_metrics, threshold)
        if final_vulnerable:
            status = "STILL_VULNERABLE"
            still_vulnerable.append(current.get("id") or original_id)
        elif rounds:
            status = "REGENERATED"
        else:
            status = "PASSED"

        before_values.append(before["leak_advantage"])
        after_values.append(current_metrics["leak_advantage"])
        current["red_team_status"] = status
        final_items.append(current)
        report_items.append({
            "item_id": original_id,
            "final_item_id": current.get("id"),
            "concept": current.get("concept", item.get("concept", "")),
            "section": current.get("section", item.get("section", "")),
            "status": status,
            "rounds": rounds,
            "vulnerable": final_vulnerable,
            "leaked_count": len(leaked),
            "before": before,
            "after": current_metrics,
        })
        if progress_callback:
            progress_callback((index + 1) / total, f"{status}: {original_id} ({rounds} round(s))")

    mean_before = sum(before_values) / len(before_values) if before_values else 0.0
    mean_after = sum(after_values) / len(after_values) if after_values else 0.0
    worst = sorted(
        ((item["item_id"], max(item["before"]["leak_advantage"], item["after"]["leak_advantage"]))
         for item in report_items if item["before"]),
        key=lambda pair: pair[1],
        reverse=True,
    )[:3]

    return {
        "items": report_items,
        "final_items": final_items,
        "mean_advantage_before": mean_before,
        "mean_advantage_after": mean_after,
        "still_vulnerable": still_vulnerable,
        "worst_items": worst,
        "threshold": threshold,
        "samples": n_samples,
        "max_rounds": max_rounds,
        "estimated_by_llm_stand_in": True,
        "error": error,
    }
