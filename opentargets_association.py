"""
OpenTargets Association Score Enrichment Script
================================================
Reads an Excel file with 'indication' and 'moa' columns,
maps MoA entries and indications to OpenTargets equivalents using Gemini + Google Search,
fetches association scores from OpenTargets GraphQL API,
and writes the highest association score per indication back to the Excel file.

Usage:
    pip install -r requirements.txt
    python opentargets_association.py

Environment variables (in .env):
    GEMINI_API_KEY   - Google Gemini API key
    INPUT_FILE       - Path to the input Excel file
    OUTPUT_FILE      - (Optional) Output file path; defaults to <input>_scored.xlsx
    SHEET_NAME       - (Optional) Sheet name to read; defaults to first sheet
"""

import os
import re
import sys
import time
import json
import logging
import requests
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv

# ── Load .env ──────────────────────────────────────────────────────────────────
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
INPUT_FILE     = os.getenv("INPUT_FILE", "").strip()
OUTPUT_FILE    = os.getenv("OUTPUT_FILE", "").strip()
SHEET_NAME     = os.getenv("SHEET_NAME", "").strip() or None   # None → first sheet

if not GEMINI_API_KEY:
    sys.exit("❌  GEMINI_API_KEY is missing from .env")
if not INPUT_FILE:
    sys.exit("❌  INPUT_FILE is missing from .env")
if not Path(INPUT_FILE).exists():
    sys.exit(f"❌  File not found: {INPUT_FILE}")

if not OUTPUT_FILE:
    p = Path(INPUT_FILE)
    OUTPUT_FILE = str(p.parent / f"{p.stem}_scored{p.suffix}")

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────
GEMINI_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
)
OT_GRAPHQL = "https://api.platform.opentargets.org/api/v4/graphql"

HEADERS_JSON = {"Content-Type": "application/json"}

# ── Gemini helper ──────────────────────────────────────────────────────────────

def gemini_search(prompt: str, retries: int = 3) -> str:
    """
    Call Gemini with Google Search grounding enabled and return the text response.
    """
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "tools": [{"google_search": {}}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 512},
    }
    for attempt in range(1, retries + 1):
        try:
            r = requests.post(GEMINI_URL, json=payload, headers=HEADERS_JSON, timeout=30)
            r.raise_for_status()
            data = r.json()
            parts = (
                data.get("candidates", [{}])[0]
                    .get("content", {})
                    .get("parts", [])
            )
            return " ".join(p.get("text", "") for p in parts).strip()
        except Exception as exc:
            log.warning("Gemini attempt %d/%d failed: %s", attempt, retries, exc)
            time.sleep(2 ** attempt)
    return ""


def extract_id_from_gemini(text: str, prefix: str) -> str | None:
    """
    Pull the first occurrence of ENSG… (target) or EFO_/MONDO_/HP_/DOID_/Orphanet_…
    (disease) from Gemini's free-text response.
    """
    if prefix == "target":
        m = re.search(r"ENSG\d{11}", text)
        return m.group() if m else None
    else:
        m = re.search(
            r"(EFO_\d+|MONDO_\d+|HP_\d+|DOID:\d+|Orphanet_\d+|CHEBI_\d+)",
            text,
            re.IGNORECASE,
        )
        if m:
            # normalise separator
            return m.group().replace(":", "_")
        return None

# ── OpenTargets helpers ────────────────────────────────────────────────────────

def ot_search_target(name: str) -> tuple[str | None, str | None]:
    """Return (ensembl_id, approved_symbol) for the best-matching target."""
    query = """
    query SearchTarget($q: String!) {
      search(queryString: $q, entityNames: ["target"], page: {index: 0, size: 3}) {
        hits {
          id
          object {
            ... on Target {
              approvedSymbol
              approvedName
            }
          }
        }
      }
    }
    """
    try:
        r = requests.post(
            OT_GRAPHQL,
            json={"query": query, "variables": {"q": name}},
            headers=HEADERS_JSON,
            timeout=20,
        )
        r.raise_for_status()
        hits = r.json()["data"]["search"]["hits"]
        if hits:
            h = hits[0]
            return h["id"], h["object"].get("approvedSymbol")
    except Exception as exc:
        log.warning("OT target search failed for '%s': %s", name, exc)
    return None, None


def ot_search_disease(name: str) -> tuple[str | None, str | None]:
    """Return (disease_id, disease_name) for the best-matching disease."""
    query = """
    query SearchDisease($q: String!) {
      search(queryString: $q, entityNames: ["disease"], page: {index: 0, size: 3}) {
        hits {
          id
          object {
            ... on Disease {
              name
            }
          }
        }
      }
    }
    """
    try:
        r = requests.post(
            OT_GRAPHQL,
            json={"query": query, "variables": {"q": name}},
            headers=HEADERS_JSON,
            timeout=20,
        )
        r.raise_for_status()
        hits = r.json()["data"]["search"]["hits"]
        if hits:
            h = hits[0]
            return h["id"], h["object"].get("name")
    except Exception as exc:
        log.warning("OT disease search failed for '%s': %s", name, exc)
    return None, None


def ot_association_score(disease_id: str, target_id: str) -> float | None:
    """
    Return the overall association score (0-1) between a disease and a target,
    or None if not found.
    """
    query = """
    query AssocScore($diseaseId: String!, $targetId: String!) {
      disease(efoId: $diseaseId) {
        associatedTargets(
          filter: { ids: [$targetId] }
          page: { index: 0, size: 1 }
        ) {
          rows {
            score
            target { id approvedSymbol }
          }
        }
      }
    }
    """
    try:
        r = requests.post(
            OT_GRAPHQL,
            json={
                "query": query,
                "variables": {"diseaseId": disease_id, "targetId": target_id},
            },
            headers=HEADERS_JSON,
            timeout=20,
        )
        r.raise_for_status()
        rows = (
            r.json()
             .get("data", {})
             .get("disease", {})
             .get("associatedTargets", {})
             .get("rows", [])
        )
        if rows:
            return float(rows[0]["score"])
    except Exception as exc:
        log.warning(
            "OT score failed for disease=%s target=%s: %s", disease_id, target_id, exc
        )
    return None

# ── Main pipeline ──────────────────────────────────────────────────────────────

def resolve_moa_targets(raw_moas: list[str]) -> dict[str, tuple[str | None, str | None]]:
    """
    For each unique MoA string, use Gemini+Search → OT search to get
    (ensembl_id, approved_symbol).
    Returns dict keyed by original moa string.
    """
    resolved: dict[str, tuple[str | None, str | None]] = {}
    for moa in raw_moas:
        log.info("  Resolving MoA → '%s'", moa)
        prompt = (
            f"Search OpenTargets (platform.opentargets.org) for the target that best "
            f"represents the mechanism of action '{moa}'. "
            f"Return ONLY the Ensembl gene ID (ENSG…) and the approved gene symbol, "
            f"separated by a space. If there are multiple, pick the most common primary target."
        )
        text = gemini_search(prompt)
        log.debug("    Gemini raw: %s", text[:200])

        # Try to grab ENSG from Gemini response first
        ensg = extract_id_from_gemini(text, "target")
        symbol = None

        if ensg:
            # Verify via OT
            _, symbol = ot_search_target(ensg)
        if not ensg:
            # Fallback: search OT directly with the MoA name
            ensg, symbol = ot_search_target(moa)

        if ensg:
            log.info("    ✅ %s → %s (%s)", moa, ensg, symbol)
        else:
            log.warning("    ⚠️  Could not resolve target for '%s'", moa)

        resolved[moa] = (ensg, symbol)
        time.sleep(0.5)   # be polite to Gemini

    return resolved


def resolve_indications(unique_indications: list[str]) -> dict[str, tuple[str | None, str | None]]:
    """
    For each unique indication, use Gemini+Search → OT search to get
    (disease_id, disease_name).
    """
    resolved: dict[str, tuple[str | None, str | None]] = {}
    for ind in unique_indications:
        log.info("  Resolving indication → '%s'", ind)
        prompt = (
            f"Search OpenTargets (platform.opentargets.org) for the disease that best "
            f"matches the indication '{ind}'. "
            f"Return ONLY the disease ID (e.g. EFO_0000384, MONDO_0005147, etc.) "
            f"and the disease name, separated by a space."
        )
        text = gemini_search(prompt)
        log.debug("    Gemini raw: %s", text[:200])

        disease_id = extract_id_from_gemini(text, "disease")
        disease_name = None

        if disease_id:
            # Verify via OT search
            verified_id, disease_name = ot_search_disease(disease_id)
            if verified_id:
                disease_id = verified_id
        if not disease_id:
            # Fallback: direct OT search
            disease_id, disease_name = ot_search_disease(ind)

        if disease_id:
            log.info("    ✅ %s → %s (%s)", ind, disease_id, disease_name)
        else:
            log.warning("    ⚠️  Could not resolve disease for '%s'", ind)

        resolved[ind] = (disease_id, disease_name)
        time.sleep(0.5)

    return resolved


def compute_max_scores(
    indications: list[str],
    ind_map: dict[str, tuple[str | None, str | None]],
    target_map: dict[str, tuple[str | None, str | None]],
    moa_list: list[str],
) -> dict[str, float | None]:
    """
    For each unique indication, query OT for every target and return the max score.
    """
    max_scores: dict[str, float | None] = {}
    target_ids = [
        (moa, tid, sym)
        for moa, (tid, sym) in target_map.items()
        if tid is not None
    ]

    for ind in indications:
        disease_id, disease_name = ind_map.get(ind, (None, None))
        if not disease_id:
            log.warning("  Skipping '%s' — no disease ID", ind)
            max_scores[ind] = None
            continue

        log.info("  Scoring indication '%s' (%s) against %d targets …", ind, disease_id, len(target_ids))
        scores = []
        for moa, target_id, symbol in target_ids:
            score = ot_association_score(disease_id, target_id)
            log.info("    %s (%s) → %.4f", symbol or moa, target_id, score if score else 0)
            if score is not None:
                scores.append(score)
            time.sleep(0.3)

        max_scores[ind] = max(scores) if scores else None
        log.info("  → Max score for '%s': %s", ind, max_scores[ind])

    return max_scores


def main():
    log.info("📂 Reading file: %s", INPUT_FILE)
    df = pd.read_excel(INPUT_FILE, sheet_name=SHEET_NAME or 0, dtype=str)
    df.columns = df.columns.str.strip()

    # ── Validate columns ───────────────────────────────────────────────────────
    missing = [c for c in ("indication", "moa") if c.lower() not in [x.lower() for x in df.columns]]
    if missing:
        sys.exit(f"❌  Missing required columns: {missing}. Found: {list(df.columns)}")

    # Normalise column names (case-insensitive match)
    col_map = {c.lower(): c for c in df.columns}
    ind_col = col_map["indication"]
    moa_col = col_map["moa"]

    # ── Parse MoAs (same for all rows) ────────────────────────────────────────
    raw_moa_str = df[moa_col].dropna().iloc[0]
    raw_moas = [m.strip() for m in raw_moa_str.split(";") if m.strip()]
    log.info("🧬 MoAs found (%d): %s", len(raw_moas), raw_moas)

    # ── Unique indications ─────────────────────────────────────────────────────
    unique_inds = df[ind_col].dropna().unique().tolist()
    log.info("🦠 Unique indications (%d): %s", len(unique_inds), unique_inds)

    # ── Step 1: Resolve MoA → OpenTargets targets ──────────────────────────────
    log.info("\n── Step 1: Resolving MoA targets ────────────────────────────────")
    target_map = resolve_moa_targets(raw_moas)

    # ── Step 2: Resolve indications → OpenTargets diseases ────────────────────
    log.info("\n── Step 2: Resolving indications to OT diseases ─────────────────")
    ind_map = resolve_indications(unique_inds)

    # ── Step 3: Fetch association scores ──────────────────────────────────────
    log.info("\n── Step 3: Fetching association scores ──────────────────────────")
    max_scores = compute_max_scores(unique_inds, ind_map, target_map, raw_moas)

    # ── Step 4: Write back to DataFrame ───────────────────────────────────────
    df["association_score"] = df[ind_col].map(max_scores)
    df["ot_disease_id"]     = df[ind_col].map(lambda x: ind_map.get(x, (None, None))[0])
    df["ot_disease_name"]   = df[ind_col].map(lambda x: ind_map.get(x, (None, None))[1])

    # Add target resolution summary once
    ot_targets_summary = "; ".join(
        f"{moa}→{sym or tid}"
        for moa, (tid, sym) in target_map.items()
        if tid
    )
    df["ot_targets_resolved"] = ot_targets_summary

    # ── Step 5: Save ───────────────────────────────────────────────────────────
    log.info("\n── Step 5: Saving to %s", OUTPUT_FILE)
    with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Results")
        ws = writer.sheets["Results"]

        # Simple header styling
        from openpyxl.styles import Font, PatternFill, Alignment
        header_fill = PatternFill("solid", fgColor="4F81BD")
        score_fill  = PatternFill("solid", fgColor="E2EFDA")
        for cell in ws[1]:
            cell.font      = Font(bold=True, color="FFFFFF", name="Arial", size=11)
            cell.fill      = header_fill
            cell.alignment = Alignment(horizontal="center", wrap_text=True)

        # Highlight the association_score column
        score_col_idx = df.columns.get_loc("association_score") + 1
        for row in ws.iter_rows(min_row=2, min_col=score_col_idx, max_col=score_col_idx):
            for cell in row:
                cell.fill = score_fill
                cell.font = Font(bold=True, name="Arial")
                if cell.value is not None:
                    cell.number_format = "0.0000"

        # Auto-fit column widths (approximate)
        for col in ws.columns:
            max_len = max((len(str(c.value or "")) for c in col), default=10)
            ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 50)

    log.info("✅ Done! Output saved to: %s", OUTPUT_FILE)
    log.info("\n── Summary ──────────────────────────────────────────────────────")
    log.info("  MoA targets resolved: %d / %d", sum(1 for v in target_map.values() if v[0]), len(raw_moas))
    log.info("  Indications resolved: %d / %d", sum(1 for v in ind_map.values() if v[0]), len(unique_inds))
    scored = sum(1 for v in max_scores.values() if v is not None)
    log.info("  Association scores found: %d / %d", scored, len(unique_inds))

    print("\n📊 Score results:")
    for ind, score in max_scores.items():
        did, dname = ind_map.get(ind, (None, None))
        print(f"  {ind:40s} → {score:.4f}" if score else f"  {ind:40s} → N/A")


if __name__ == "__main__":
    main()
