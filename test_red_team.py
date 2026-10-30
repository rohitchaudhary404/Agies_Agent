from services import red_team as rt


def make_item(item_id, concept="Algebra", key="B", section="Quantitative",
              options=None, difficulty="Medium"):
    return {
        "id": item_id,
        "stem": f"Question {item_id}",
        "options": options or ["A) 11", "B) 12", "C) 13", "D) 14"],
        "concept": concept,
        "section": section,
        "difficulty": difficulty,
        "key": key,
    }


def test_leak_advantage_is_armed_minus_blind(monkeypatch):
    target = make_item("T1", key="B")
    leaked = [make_item("L1", key="C")]

    monkeypatch.setattr(rt, "simulate_leak", lambda item, chat_fn=None: "leak dump")
    monkeypatch.setattr(
        rt, "solve",
        lambda item, leak_text=None, n_samples=3, chat_fn=None:
        ["A"] * n_samples if leak_text is None else ["B"] * n_samples,
    )

    metrics = rt.measure_item(target, leaked, n_samples=3)

    assert metrics["accuracy_blind"] == 0.0
    assert metrics["accuracy_armed"] == 1.0
    assert metrics["leak_advantage"] == 1.0


def test_copy_rate_counts_other_leaked_keys_not_target_key(monkeypatch):
    target = make_item("T2", key="A")
    leaked = [make_item("L2", key="B")]

    monkeypatch.setattr(rt, "simulate_leak", lambda item, chat_fn=None: "leak dump")
    monkeypatch.setattr(
        rt, "solve",
        lambda item, leak_text=None, n_samples=3, chat_fn=None:
        ["A", "A", "A"] if leak_text is None else ["B", "B", "A"],
    )

    metrics = rt.measure_item(target, leaked, n_samples=3)

    assert metrics["copy_rate"] == 2 / 3
    assert metrics["key"] == "A"
    assert metrics["key_source"] == "item"


def test_vulnerable_item_is_regenerated_and_remeasured(monkeypatch):
    slot_item = make_item("S1")
    previous = [make_item("P1")]
    safe = make_item("S1-new", key="C")
    vulnerable = {"leak_advantage": 0.6, "copy_rate": 0.7}
    hardened = {"leak_advantage": 0.05, "copy_rate": 0.0}
    measurements = iter([vulnerable, hardened])

    monkeypatch.setattr(rt, "measure_item", lambda *args, **kwargs: dict(next(measurements)))
    monkeypatch.setattr(rt, "regenerate_item", lambda item, chat_fn=None: dict(safe))

    report = rt.red_team_slot(
        [slot_item], previous, concept_families={"Algebra": "Quant"},
        threshold=0.20, max_rounds=3, n_samples=2,
    )

    item_report = report["items"][0]
    assert item_report["status"] == "REGENERATED"
    assert item_report["rounds"] == 1
    assert item_report["final_item_id"] == "S1-new"
    assert report["final_items"][0]["id"] == "S1-new"
    assert report["mean_advantage_before"] == 0.6
    assert report["mean_advantage_after"] == 0.05
    assert report["still_vulnerable"] == []


def test_regeneration_loop_stops_at_max_rounds(monkeypatch):
    slot_item = make_item("S2")
    previous = [make_item("P2")]
    calls = {"regenerate": 0, "measure": 0}

    def always_vulnerable(*args, **kwargs):
        calls["measure"] += 1
        return {"leak_advantage": 0.9, "copy_rate": 0.8}

    def regenerate(item, chat_fn=None):
        calls["regenerate"] += 1
        return make_item(f"S2-r{calls['regenerate']}")

    monkeypatch.setattr(rt, "measure_item", always_vulnerable)
    monkeypatch.setattr(rt, "regenerate_item", regenerate)

    report = rt.red_team_slot(
        [slot_item], previous, threshold=0.2, max_rounds=3, n_samples=2,
    )

    assert calls["regenerate"] == 3
    assert report["items"][0]["rounds"] == 3
    assert report["items"][0]["status"] == "STILL_VULNERABLE"
    assert report["still_vulnerable"] == ["S2-r3"]


def test_regenerate_rejects_variant_whose_key_is_not_an_option(monkeypatch):
    bad = '{"stem": "new", "options": ["5", "6", "7", "8"], "key": "Z"}'

    monkeypatch.setattr(
        rt, "chat",
        lambda prompt, temperature=0.7, json_mode=False, model=None, retries=3: bad,
    )

    assert rt.regenerate_item(make_item("S3")) is None
