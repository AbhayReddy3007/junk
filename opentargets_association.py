"""
OpenTargets Association Score Enrichment Script
================================================
Reads an Excel file with 'indication' and 'moa' columns,
maps MoA entries and indications to OpenTargets equivalents using Gemini + Google Search,
fetches association scores from OpenTargets GraphQL API,
and writes the highest association score per indication back to the Excel file.

Features
--------
- Cache: resolved MoAs and indications are saved to a JSON file next to the
  input file (<stem>_cache.json) and reused on subsequent runs.
- Batching: each Gemini call resolves 3 indications at once.
- Parallelism: 3 concurrent workers for both resolution and scoring.
- Retry: each LLM call retries once on failure.

Usage:
    pip install -r requirements.txt
    python opentargets_association.py

Environment variables (in .env):
    GEMINI_API_KEY   - Google Gemini API key
    GEMINI_MODEL     - Model name (default: gemini-2.5-flash)
    INPUT_FILE       - Path to the input Excel file
    OUTPUT_FILE      - (Optional) output path; defaults to <input>_scored.xlsx
    SHEET_NAME       - (Optional) sheet name; defaults to first sheet
    CACHE_FILE       - (Optional) path to cache JSON; defaults to <input>_cache.json
    WORKERS          - (Optional) parallel workers (default: 3)
"""

import os
import re
import sys
import time
import json
import logging
import threading
import requests
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed

# ── Load .env ──────────────────────────────────────────────────────────────────
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL   = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
INPUT_FILE     = os.getenv("INPUT_FILE", "").strip()
OUTPUT_FILE    = os.getenv("OUTPUT_FILE", "").strip()
SHEET_NAME     = os.getenv("SHEET_NAME", "").strip() or None
CACHE_FILE     = os.getenv("CACHE_FILE", "").strip()
WORKERS        = int(os.getenv("WORKERS", "3"))

if not GEMINI_API_KEY:
    sys.exit("❌  GEMINI_API_KEY is missing from .env")
if not INPUT_FILE:
    sys.exit("❌  INPUT_FILE is missing from .env")
if not Path(INPUT_FILE).exists():
    sys.exit(f"❌  File not found: {INPUT_FILE}")

_inp = Path(INPUT_FILE)
if not OUTPUT_FILE:
    OUTPUT_FILE = str(_inp.parent / f"{_inp.stem}_scored{_inp.suffix}")
if not CACHE_FILE:
    CACHE_FILE = str(_inp.parent / f"{_inp.stem}_cache.json")

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  [%(threadName)s]  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────
GEMINI_URL   = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
)
OT_GRAPHQL   = "https://api.platform.opentargets.org/api/v4/graphql"
HEADERS_JSON = {"Content-Type": "application/json"}
BATCH_SIZE   = 3          # indications per Gemini call
_cache_lock  = threading.Lock()   # protects cache writes

# ── Cache helpers ──────────────────────────────────────────────────────────────

def load_cache() -> dict:
    """Load cache from disk, returning empty structure on first run."""
    if Path(CACHE_FILE).exists():
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                cache = json.load(f)
            log.info("📦 Loaded cache from %s  (moas=%d, indications=%d)",
                     CACHE_FILE,
                     len(cache.get("moa_targets", {})),
                     len(cache.get("indications", {})))
            return cache
        except Exception as exc:
            log.warning("⚠️  Cache read failed (%s), starting fresh.", exc)
    return {"moa_targets": {}, "indications": {}}


def save_cache(cache: dict) -> None:
    """Persist cache to disk (thread-safe)."""
    with _cache_lock:
        try:
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(cache, f, indent=2, ensure_ascii=False)
        except Exception as exc:
            log.warning("⚠️  Cache write failed: %s", exc)


# ── Gemini helper ──────────────────────────────────────────────────────────────

def gemini_search(prompt: str, max_retries: int = 2) -> str:
    """
    Call Gemini with Google Search grounding.
    Retries once on failure (max_retries=2 means 1 retry).
    """
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "tools": [{"google_search": {}}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 1024},
    }
    for attempt in range(1, max_retries + 1):
        try:
            r = requests.post(GEMINI_URL, json=payload, headers=HEADERS_JSON, timeout=45)
            r.raise_for_status()
            data  = r.json()
            parts = (
                data.get("candidates", [{}])[0]
                    .get("content", {})
                    .get("parts", [])
            )
            return " ".join(p.get("text", "") for p in parts).strip()
        except Exception as exc:
            log.warning("Gemini attempt %d/%d failed: %s", attempt, max_retries, exc)
            if attempt < max_retries:
                time.sleep(2 ** attempt)
    return ""


def extract_id_from_text(text: str, kind: str) -> str | None:
    """Extract ENSG ID (kind='target') or EFO/MONDO/HP/DOID ID (kind='disease')."""
    if kind == "target":
        m = re.search(r"ENSG\d{11}", text)
        return m.group() if m else None
    m = re.search(
        r"(EFO_\d+|MONDO_\d+|HP_\d+|DOID[_:]\d+|Orphanet_\d+|CHEBI_\d+)",
        text, re.IGNORECASE,
    )
    return m.group().replace(":", "_") if m else None


# ── OpenTargets helpers ────────────────────────────────────────────────────────

def _ot_post(query: str, variables: dict, context: str = "") -> dict | None:
    """Shared POST to OT GraphQL with unified error handling."""
    try:
        r = requests.post(
            OT_GRAPHQL,
            json={"query": query, "variables": variables},
            headers=HEADERS_JSON,
            timeout=20,
        )
        r.raise_for_status()
        body = r.json()
        if "errors" in body:
            log.warning("OT GraphQL error [%s]: %s", context, body["errors"])
            return None
        return body.get("data")
    except Exception as exc:
        log.warning("OT request failed [%s]: %s", context, exc)
        return None


def ot_search_target(name: str) -> tuple[str | None, str | None]:
    query = """
    query SearchTarget($q: String!) {
      search(queryString: $q, entityNames: ["target"], page: {index: 0, size: 3}) {
        hits {
          id
          object { ... on Target { approvedSymbol approvedName } }
        }
      }
    }
    """
    data = _ot_post(query, {"q": name}, context=f"target:{name}")
    if data:
        hits = data.get("search", {}).get("hits", [])
        if hits:
            h = hits[0]
            return h["id"], h["object"].get("approvedSymbol")
    return None, None


def ot_search_disease(name: str) -> tuple[str | None, str | None]:
    query = """
    query SearchDisease($q: String!) {
      search(queryString: $q, entityNames: ["disease"], page: {index: 0, size: 3}) {
        hits {
          id
          object { ... on Disease { name } }
        }
      }
    }
    """
    data = _ot_post(query, {"q": name}, context=f"disease:{name}")
    if data:
        hits = data.get("search", {}).get("hits", [])
        if hits:
            h = hits[0]
            return h["id"], h["object"].get("name")
    return None, None


def ot_association_score(disease_id: str, target_id: str) -> float | None:
    """Return overall association score (0-1) between a target and disease."""
    query = """
    query AssocScore($targetId: String!, $diseaseId: String!) {
      target(ensemblId: $targetId) {
        associatedDiseases(
          enableIndirect: true
          filter: { ids: [$diseaseId] }
          page: { index: 0, size: 1 }
        ) {
          rows { score  disease { id name } }
        }
      }
    }
    """
    data = _ot_post(
        query,
        {"targetId": target_id, "diseaseId": disease_id},
        context=f"score:{target_id}×{disease_id}",
    )
    if data:
        rows = data.get("target", {}).get("associatedDiseases", {}).get("rows", [])
        if rows:
            return float(rows[0]["score"])
    return None


# ── Resolution: MoA targets ────────────────────────────────────────────────────

def _resolve_single_moa(moa: str) -> tuple[str, str | None, str | None]:
    """Resolve one MoA string → (moa, ensembl_id, symbol). Retries once."""
    log.info("  Resolving MoA → '%s'", moa)
    prompt = (
        f"Search OpenTargets (platform.opentargets.org) for the target that best "
        f"represents the mechanism of action '{moa}'. "
        f"Return ONLY the Ensembl gene ID (ENSG…) and the approved gene symbol, "
        f"separated by a space. Pick the most common primary target."
    )
    text = gemini_search(prompt)
    ensg = extract_id_from_text(text, "target")
    symbol = None
    if ensg:
        _, symbol = ot_search_target(ensg)
    if not ensg:
        ensg, symbol = ot_search_target(moa)
    if ensg:
        log.info("    ✅ MoA '%s' → %s (%s)", moa, ensg, symbol)
    else:
        log.warning("    ⚠️  Could not resolve target for '%s'", moa)
    return moa, ensg, symbol


def resolve_moa_targets(raw_moas: list[str], cache: dict) -> dict[str, tuple[str | None, str | None]]:
    """
    Resolve MoA strings → OT targets.
    Uses cache; resolves missing ones in parallel (WORKERS threads).
    MoAs are individual (not batched) since there are usually few of them.
    """
    target_map: dict[str, tuple[str | None, str | None]] = {}
    cached     = cache.get("moa_targets", {})
    to_resolve = []

    for moa in raw_moas:
        if moa in cached:
            entry = cached[moa]
            target_map[moa] = (entry.get("id"), entry.get("symbol"))
            log.info("  💾 Cache hit MoA '%s' → %s (%s)", moa, entry.get("id"), entry.get("symbol"))
        else:
            to_resolve.append(moa)

    if to_resolve:
        with ThreadPoolExecutor(max_workers=WORKERS, thread_name_prefix="moa") as exe:
            futures = {exe.submit(_resolve_single_moa, moa): moa for moa in to_resolve}
            for fut in as_completed(futures):
                moa, ensg, symbol = fut.result()
                target_map[moa] = (ensg, symbol)
                cached[moa] = {"id": ensg, "symbol": symbol}

        cache["moa_targets"] = cached
        save_cache(cache)

    return target_map


# ── Resolution: Indications (batched) ─────────────────────────────────────────

def _resolve_indication_batch(
    batch: list[str],
) -> list[tuple[str, str | None, str | None]]:
    """
    Resolve a batch of up to BATCH_SIZE indications in one Gemini call.
    Returns list of (indication, disease_id, disease_name).
    Retries the whole batch once on failure, then falls back per-item.
    """
    numbered = "\n".join(f"{i+1}. {ind}" for i, ind in enumerate(batch))
    prompt = (
        "Search OpenTargets (platform.opentargets.org) for the best matching disease "
        "for each of the following indications. "
        "Return ONLY a JSON array — no prose, no markdown fences — where each element has:\n"
        '  {"indication": "<original text>", "id": "<EFO_/MONDO_/HP_/DOID_ ID>", "name": "<OT disease name>"}\n'
        "Use null for id/name if no match is found.\n\n"
        f"Indications:\n{numbered}"
    )

    def _attempt() -> list[tuple[str, str | None, str | None]]:
        text = gemini_search(prompt)
        # Strip any accidental markdown fences
        text = re.sub(r"```(?:json)?|```", "", text).strip()
        parsed = json.loads(text)
        results = []
        for item in parsed:
            ind  = item.get("indication", "")
            did  = item.get("id") or None
            name = item.get("name") or None
            if did:
                did = did.replace(":", "_")
                # Verify via OT
                verified_id, verified_name = ot_search_disease(did)
                if verified_id:
                    did, name = verified_id, verified_name
            if not did:
                did, name = ot_search_disease(ind)
            results.append((ind, did, name))
        return results

    # Try once, retry once on any failure
    for attempt in range(1, 3):
        try:
            results = _attempt()
            # Verify we got results for every item in the batch
            if len(results) == len(batch):
                return results
            log.warning("Batch attempt %d returned %d/%d results, retrying…",
                        attempt, len(results), len(batch))
        except Exception as exc:
            log.warning("Batch attempt %d failed (%s), retrying…", attempt, exc)
        time.sleep(2)

    # Fallback: resolve each item individually
    log.warning("Falling back to individual resolution for batch: %s", batch)
    results = []
    for ind in batch:
        prompt_single = (
            f"Search OpenTargets for the disease matching '{ind}'. "
            f"Return ONLY: {{\"id\": \"<OT ID>\", \"name\": \"<OT name>\"}}"
        )
        text = gemini_search(prompt_single)
        text = re.sub(r"```(?:json)?|```", "", text).strip()
        did, name = None, None
        try:
            obj  = json.loads(text)
            did  = (obj.get("id") or "").replace(":", "_") or None
            name = obj.get("name") or None
        except Exception:
            did = extract_id_from_text(text, "disease")
        if did:
            v_id, v_name = ot_search_disease(did)
            if v_id:
                did, name = v_id, v_name
        if not did:
            did, name = ot_search_disease(ind)
        results.append((ind, did, name))
    return results


def resolve_indications(
    unique_indications: list[str],
    cache: dict,
) -> dict[str, tuple[str | None, str | None]]:
    """
    Resolve indications → OT diseases.
    - Uses cache for already-resolved items.
    - Groups remaining into batches of BATCH_SIZE.
    - Runs batches in parallel across WORKERS threads.
    """
    ind_map: dict[str, tuple[str | None, str | None]] = {}
    cached  = cache.get("indications", {})
    to_resolve = []

    for ind in unique_indications:
        if ind in cached:
            entry = cached[ind]
            ind_map[ind] = (entry.get("id"), entry.get("name"))
            log.info("  💾 Cache hit indication '%s' → %s", ind, entry.get("id"))
        else:
            to_resolve.append(ind)

    if not to_resolve:
        return ind_map

    # Split into batches of BATCH_SIZE
    batches = [
        to_resolve[i: i + BATCH_SIZE]
        for i in range(0, len(to_resolve), BATCH_SIZE)
    ]
    log.info("  📦 %d indications → %d batch(es) × %d worker(s)",
             len(to_resolve), len(batches), WORKERS)

    with ThreadPoolExecutor(max_workers=WORKERS, thread_name_prefix="ind") as exe:
        future_to_batch = {
            exe.submit(_resolve_indication_batch, batch): batch
            for batch in batches
        }
        for fut in as_completed(future_to_batch):
            try:
                results = fut.result()
            except Exception as exc:
                log.error("Batch future failed: %s", exc)
                results = [(ind, None, None) for ind in future_to_batch[fut]]

            for ind, did, dname in results:
                ind_map[ind] = (did, dname)
                cached[ind]  = {"id": did, "name": dname}
                if did:
                    log.info("    ✅ '%s' → %s (%s)", ind, did, dname)
                else:
                    log.warning("    ⚠️  No OT disease found for '%s'", ind)

    cache["indications"] = cached
    save_cache(cache)
    return ind_map


# ── Scoring (parallelised) ─────────────────────────────────────────────────────

def _score_indication(
    ind: str,
    disease_id: str,
    target_ids: list[tuple[str, str, str | None]],
) -> tuple[str, float | None]:
    """Score one indication against all targets, return (ind, max_score)."""
    scores = []
    for moa, target_id, symbol in target_ids:
        score = ot_association_score(disease_id, target_id)
        log.info("    %s (%s) × '%s' → %s",
                 symbol or moa, target_id, ind,
                 f"{score:.4f}" if score is not None else "N/A")
        if score is not None:
            scores.append(score)
    best = max(scores) if scores else None
    log.info("  → Max score for '%s': %s", ind, f"{best:.4f}" if best else "None")
    return ind, best


def compute_max_scores(
    indications: list[str],
    ind_map: dict[str, tuple[str | None, str | None]],
    target_map: dict[str, tuple[str | None, str | None]],
) -> dict[str, float | None]:
    """Fetch association scores for all indications in parallel (WORKERS threads)."""
    target_ids = [
        (moa, tid, sym)
        for moa, (tid, sym) in target_map.items()
        if tid is not None
    ]
    if not target_ids:
        log.error("No valid targets resolved — cannot score.")
        return {ind: None for ind in indications}

    max_scores: dict[str, float | None] = {}
    futures = {}

    with ThreadPoolExecutor(max_workers=WORKERS, thread_name_prefix="score") as exe:
        for ind in indications:
            disease_id, _ = ind_map.get(ind, (None, None))
            if not disease_id:
                log.warning("  Skipping '%s' — no disease ID", ind)
                max_scores[ind] = None
                continue
            log.info("  Queuing '%s' (%s) × %d targets", ind, disease_id, len(target_ids))
            fut = exe.submit(_score_indication, ind, disease_id, target_ids)
            futures[fut] = ind

        for fut in as_completed(futures):
            try:
                ind, best = fut.result()
                max_scores[ind] = best
            except Exception as exc:
                ind = futures[fut]
                log.error("Scoring failed for '%s': %s", ind, exc)
                max_scores[ind] = None

    return max_scores


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    log.info("📂 Reading: %s", INPUT_FILE)
    df = pd.read_excel(INPUT_FILE, sheet_name=SHEET_NAME or 0, dtype=str)
    df.columns = df.columns.str.strip()

    col_lower = {c.lower(): c for c in df.columns}
    missing   = [c for c in ("indication", "moa") if c not in col_lower]
    if missing:
        sys.exit(f"❌  Missing columns: {missing}. Found: {list(df.columns)}")

    ind_col = col_lower["indication"]
    moa_col = col_lower["moa"]

    raw_moa_str = df[moa_col].dropna().iloc[0]
    raw_moas    = [m.strip() for m in raw_moa_str.split(";") if m.strip()]
    unique_inds = df[ind_col].dropna().unique().tolist()

    log.info("🧬 MoAs (%d): %s", len(raw_moas), raw_moas)
    log.info("🦠 Indications (%d): %s", len(unique_inds), unique_inds)
    log.info("🔧 Workers: %d  |  Batch size: %d  |  Cache: %s", WORKERS, BATCH_SIZE, CACHE_FILE)

    cache = load_cache()

    # ── Step 1: MoA → targets ──────────────────────────────────────────────────
    log.info("\n── Step 1: Resolving MoA targets ─────────────────────────────────")
    target_map = resolve_moa_targets(raw_moas, cache)

    # ── Step 2: Indications → diseases ────────────────────────────────────────
    log.info("\n── Step 2: Resolving indications → OT diseases ───────────────────")
    ind_map = resolve_indications(unique_inds, cache)

    # ── Step 3: Association scores ─────────────────────────────────────────────
    log.info("\n── Step 3: Fetching association scores ───────────────────────────")
    max_scores = compute_max_scores(unique_inds, ind_map, target_map)

    # ── Step 4: Write Excel ────────────────────────────────────────────────────
    df["association_score"]   = df[ind_col].map(max_scores)
    df["ot_disease_id"]       = df[ind_col].map(lambda x: ind_map.get(x, (None, None))[0])
    df["ot_disease_name"]     = df[ind_col].map(lambda x: ind_map.get(x, (None, None))[1])
    df["ot_targets_resolved"] = "; ".join(
        f"{moa}→{sym or tid}"
        for moa, (tid, sym) in target_map.items() if tid
    )

    log.info("\n── Step 4: Saving to %s", OUTPUT_FILE)
    from openpyxl.styles import Font, PatternFill, Alignment
    with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Results")
        ws = writer.sheets["Results"]

        hdr_fill   = PatternFill("solid", fgColor="4F81BD")
        score_fill = PatternFill("solid", fgColor="E2EFDA")

        for cell in ws[1]:
            cell.font      = Font(bold=True, color="FFFFFF", name="Arial", size=11)
            cell.fill      = hdr_fill
            cell.alignment = Alignment(horizontal="center", wrap_text=True)

        score_col = df.columns.get_loc("association_score") + 1
        for row in ws.iter_rows(min_row=2, min_col=score_col, max_col=score_col):
            for cell in row:
                cell.fill         = score_fill
                cell.font         = Font(bold=True, name="Arial")
                cell.number_format = "0.0000"

        for col in ws.columns:
            width = max((len(str(c.value or "")) for c in col), default=10)
            ws.column_dimensions[col[0].column_letter].width = min(width + 4, 50)

    log.info("✅ Saved: %s", OUTPUT_FILE)

    # ── Summary ────────────────────────────────────────────────────────────────
    n_targets = sum(1 for v in target_map.values() if v[0])
    n_ind     = sum(1 for v in ind_map.values() if v[0])
    n_scored  = sum(1 for v in max_scores.values() if v is not None)

    log.info("\n── Summary ───────────────────────────────────────────────────────")
    log.info("  MoA targets resolved : %d / %d", n_targets, len(raw_moas))
    log.info("  Indications resolved : %d / %d", n_ind, len(unique_inds))
    log.info("  Scores found         : %d / %d", n_scored, len(unique_inds))
    log.info("  Cache saved to       : %s", CACHE_FILE)

    print("\n📊 Score results:")
    for ind in unique_inds:
        score = max_scores.get(ind)
        did, dname = ind_map.get(ind, (None, None))
        score_str = f"{score:.4f}" if score is not None else "N/A"
        print(f"  {ind:<45} {score_str:<10}  ({dname or did or 'unresolved'})")


if __name__ == "__main__":
    main()
