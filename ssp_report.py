"""Balanced Serious Safety PDF report generator.

This version is intentionally in-between the previous complex report and the
latest ultra-simple report:
- Uses prompt-based section extraction (LLM)
- Keeps PDF rendering simple and readable
- Uses bold section titles and separator lines
"""

from __future__ import annotations

import json
from datetime import date
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from medical_potential.serious_safety_profile.llm_runtime import gemini_call_without_search, safe_json_parse


NAVY = colors.HexColor("#1F3864")
BLUE = colors.HexColor("#2E75B6")
GREY = colors.HexColor("#666666")
DARK_TEXT = colors.HexColor("#1A1A2E")

SECTION_ORDER = [
    "serious_safety_profile",
    "clinical_trial_safety",
    "serious_adverse_events_found",
    "regulatory_assessment",
    "post_marketing_safety",
]

SECTION_TITLES = {
    "serious_safety_profile": "Serious Safety Profile Landscape",
    "clinical_trial_safety": "Clinical Trial Safety",
    "serious_adverse_events_found": "Serious Adverse Events Found",
    "regulatory_assessment": "Regulatory Assessment",
    "post_marketing_safety": "Post-Marketing Safety",
}


def escape_html(text: str | None) -> str:
    if text is None:
        return ""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def build_styles():
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name="ReportTitle",
        fontSize=18,
        leading=22,
        textColor=NAVY,
        fontName="Helvetica-Bold",
        spaceAfter=2,
        alignment=TA_LEFT,
    ))
    styles.add(ParagraphStyle(
        name="ReportSubtitle",
        fontSize=9.5,
        leading=12,
        textColor=GREY,
        fontName="Helvetica",
        spaceAfter=1,
    ))
    styles.add(ParagraphStyle(
        name="SectionHeader",
        fontSize=11.5,
        leading=14,
        textColor=colors.white,
        fontName="Helvetica-Bold",
        spaceBefore=10,
        spaceAfter=0,
        backColor=NAVY,
        alignment=TA_LEFT,
        leftIndent=0,
        rightIndent=0,
        firstLineIndent=0,
        borderPadding=(6, 8, 6, 8),
    ))
    styles.add(ParagraphStyle(
        name="BodyProse",
        fontSize=9.5,
        leading=13,
        textColor=DARK_TEXT,
        fontName="Helvetica",
        spaceAfter=5,
        alignment=TA_JUSTIFY,
    ))
    styles.add(ParagraphStyle(
        name="SnapshotLabel",
        fontSize=8,
        leading=10,
        textColor=GREY,
        fontName="Helvetica-Bold",
        spaceAfter=0,
    ))
    styles.add(ParagraphStyle(
        name="SnapshotValue",
        fontSize=10,
        leading=11,
        textColor=DARK_TEXT,
        fontName="Helvetica-Bold",
        spaceAfter=0,
    ))
    styles.add(ParagraphStyle(
        name="FooterText",
        fontSize=7,
        leading=9,
        textColor=GREY,
        fontName="Helvetica",
    ))
    return styles


def _build_summary_table(styles, score_text: str, total_trials_text: str) -> Table:
    snap_cells = [[
        [
            Paragraph(score_text, ParagraphStyle("score-value", parent=styles["SnapshotValue"], textColor=NAVY)),
            Paragraph("Score", styles["SnapshotLabel"]),
        ],
        [
            Paragraph(total_trials_text, ParagraphStyle("trial-value", parent=styles["SnapshotValue"], textColor=NAVY)),
            Paragraph("Trials Found", styles["SnapshotLabel"]),
        ],
    ]]

    table = Table(snap_cells, colWidths=[3.25 * inch, 3.25 * inch], rowHeights=[0.4 * inch])
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F5F7FA")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#E0E0E0")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def _build_section_flowables(section_title: str, section_body: str, styles) -> list:
    flowables = [Paragraph(escape_html(section_title.upper()), styles["SectionHeader"]), Spacer(1, 8)]

    for paragraph in (section_body or "").split("\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        flowables.append(Paragraph(escape_html(paragraph), styles["BodyProse"]))

    flowables.append(Spacer(1, 8))
    return flowables


def _humanize_key(key: str) -> str:
    return str(key).replace("_", " ").strip().capitalize()


def _normalize_section_value(value) -> str:
    """Convert LLM section value to plain descriptive text."""
    if value is None:
        return ""

    if isinstance(value, str):
        return value.strip()

    if isinstance(value, list):
        parts = []
        for item in value:
            item_text = _normalize_section_value(item)
            if item_text:
                parts.append(item_text)
        return " ".join(parts).strip()

    if isinstance(value, dict):
        sentences = []
        for k, v in value.items():
            v_text = _normalize_section_value(v)
            if not v_text:
                continue
            if isinstance(v, (dict, list)):
                sentences.append(v_text)
            else:
                sentences.append(f"{_humanize_key(str(k))}: {v_text}.")
        return " ".join(sentences).strip()

    return str(value).strip()


def _safe_float(v) -> float | None:
    try:
        if v is None:
            return None
        return float(v)
    except Exception:
        return None


def _is_expected_event(expectedness: str | None) -> bool:
    label = str(expectedness or "").strip().lower()
    return label.startswith("expected")


def _extract_significant_events(data: dict) -> tuple[list[str], list[str]]:
    """Return (expected, unexpected) significant event labels from SAE categorization."""
    expected_events: list[str] = []
    unexpected_events: list[str] = []

    for event in (data.get("sae_event_categorization", []) or []):
        if not event.get("material_event_flag", False):
            continue

        sae_name = str(event.get("sae_name") or "Unknown SAE").strip()
        num_studies = event.get("number_of_studies")
        suffix = f" ({num_studies} study)" if num_studies == 1 else f" ({num_studies} studies)" if isinstance(num_studies, int) else ""
        label = f"{sae_name}{suffix}"

        if _is_expected_event(event.get("expectedness_classification") or event.get("expectedness")):
            expected_events.append(label)
        else:
            unexpected_events.append(label)

    return expected_events[:10], unexpected_events[:10]


def _prepare_prompt_payload(data: dict) -> dict:
    """Reduce JSON to only what is needed for narrative section generation."""
    approval = data.get("approval_market_status", {})
    safety_score = data.get("safety_score", {})
    sae_agg = data.get("sae_aggregation", {})
    reg = data.get("regulatory_impact", {})
    pm = data.get("post_marketing_safety", {})

    events = []
    for event in (data.get("sae_event_categorization", []) or []):
        events.append(
            {
                "sae_name": event.get("sae_name"),
                "severity_category": event.get("severity_category"),
                "expectedness": event.get("expectedness") or event.get("expectedness_classification"),
                "number_of_studies": event.get("number_of_studies"),
                "material_event_flag": event.get("material_event_flag"),
            }
        )

    expected_significant_events, unexpected_significant_events = _extract_significant_events(data)

    trial_snapshot = []
    for trial in (sae_agg.get("trials", []) or [])[:200]:
        trial_snapshot.append(
            {
                "trial_id": trial.get("Trial ID"),
                "phase": trial.get("Phase"),
                "size": trial.get("Size"),
                "sae_rate_drug": trial.get("SAE Rate Drug (%)"),
                "sae_rate_control": trial.get("SAE Rate Control (%)"),
                "deaths_reported": trial.get("Deaths Reported"),
            }
        )

    return {
        "molecule_name": data.get("molecule_name", "Unknown"),
        "dimension_name": "Serious Safety Profile",
        "total_trials": len(sae_agg.get("trials",[])),
        "approval": {
            "is_approved": approval.get("is_approved"),
            "is_marketed": approval.get("is_marketed"),
            "status_summary": approval.get("status_summary"),
            "major_markets": approval.get("major_markets", []),
        },
        "sae_aggregation": {
            "sae_rate": sae_agg.get("sae_rate"),
            "control_rate": sae_agg.get("control_rate"),
            "delta_rate": sae_agg.get("delta_rate"),
        },
        "safety_score": {
            "score": safety_score.get("score"),
            "score_label": safety_score.get("score_label"),
            "key_drivers": safety_score.get("key_drivers", []),
            "adjustments_applied": safety_score.get("adjustments_applied",[]),
            "reasoning": safety_score.get("reasoning",{})
        },
        "regulatory_impact": {
            "regulatory_consequence": reg.get("regulatory_consequence"),
            "rationale": reg.get("rationale"),
            "key_safety_drivers": reg.get("key_safety_drivers", []),
        },
        "post_marketing_safety": {
            "evaluated": pm.get("evaluated"),
            "is_marketed": pm.get("is_marketed"),
            "risk_level": pm.get("risk_level"),
            "key_findings": pm.get("key_findings", []),
            "skip_reason": pm.get("skip_reason"),
        },
        "expected_significant_events": expected_significant_events,
        "unexpected_significant_events": unexpected_significant_events,
        "sae_events": events,
        "trial_snapshot": trial_snapshot,
    }


def _fallback_sections(payload: dict) -> dict:
    """Fallback section content if LLM output is unavailable."""
    molecule = payload.get("molecule_name", "Unknown")
    total_trials = payload.get("total_trials", 0)
    score = payload.get("safety_score", {}).get("score", "N/A")
    score_label = payload.get("safety_score", {}).get("score_label", "N/A")
    expected_sig = payload.get("expected_significant_events", []) or []
    unexpected_sig = payload.get("unexpected_significant_events", []) or []

    expected_line = ", ".join(expected_sig) if expected_sig else "No expected significant events were flagged in the categorization output."
    unexpected_line = ", ".join(unexpected_sig) if unexpected_sig else "No unexpected significant events were flagged in the categorization output."

    return {
        "serious_safety_profile": (
            f"This section provides the overall serious safety profile landscape for {molecule} based on the available evidence. "
            f"The current assessment score is {score}/5 ({score_label}) based on available evidence."
        ),
        "clinical_trial_safety": (
            f"A total of {total_trials} trials were reviewed for serious safety signals. "
            "The report considers rates in drug and control groups where available."
        ),
        "serious_adverse_events_found": (
            "Serious adverse events are summarized from the extracted trial data and categorized by severity and expectedness.\n"
            f"Expected significant events: {expected_line}\n"
            f"Unexpected significant events: {unexpected_line}"
        ),
        "regulatory_assessment": str(payload.get("regulatory_impact", {}).get("rationale") or "No detailed regulatory rationale was available."),
        "post_marketing_safety": str(payload.get("post_marketing_safety", {}).get("skip_reason") or "Post-marketing findings are included when available."),
    }


async def _extract_sections_via_prompt(payload: dict, model_name: str) -> dict:
    """Generate section narratives with Gemini using the same section structure as before."""
    prompt = f"""
You are a business-focused medical insights analyst. 
Goal: 
    - Create a concise, 2-page report for a given molecule focusing on Serious safety profile, highlighting key findings and insights derived from the provided input json data. 
    - The report is intended for a Medical Affairs business audience. 
Context: 
    - The data comes from the structured json data (e.g., serious adverse events, comparison between placebo and control groups, etc.). 
    - The audience is non-technical and not familiar with internal analytical frameworks, scoring methodologies, or internal jargon. 

Source: 
    - Use only the provided json data as the source of truth. 
    - Focus specifically on serious safety related data points. 
    - Do not introduce external assumptions unless clearly derived from the data
  

Input data (JSON):
{json.dumps(payload, indent=2)}

Return strictly valid JSON with exactly these keys:
- serious_safety_profile
    - Provide the overall landscape of the serious safety profile for this drug based on the given data
    - Add the details on number of trials found and the primary regions these trials were conducted, and highlight some major serious adverse events from the list
    - Give a concise brief on how the overall serious safety assessment for the molecule is
- clinical_trial_safety
- serious_adverse_events_found
    - If key note in the safety_score indicates 'No usable SAE rate data found for trials; applying default base score' or something like this then mention this clearly in the report
    - Additionally, include the commentary about the expected and unexpected significant serious events 
    - Do not mention the events as list or bullet points, jsut highlight the major events point out in the data
    - Also strictly do not use terms like clinically meaningful expected or unexpected [JUST MENTION IN PLAIN LANGUAGE]
- regulatory_assessment
- post_marketing_safety
    - If a molecule is not marketed, keep this section very brief just to 1-2 lines

Critical output constraints:
- Each of the 5 keys must map to a single paragraph string value.
- Do NOT return nested JSON objects, arrays, or key-value maps for these section keys.
- Do NOT wrap the output in markdown code fences.

Single-shot sample output format (follow this structure exactly; content should depend on input data):
{{
    "serious_safety_profile": "Across 18 trials reviewed for Molecule X, the serious safety profile landscape appears broadly manageable but still requires close monitoring in high-risk populations. Most serious events were infrequent, while a small set of recurrent events warrants clear risk communication and follow-up planning.",
    "clinical_trial_safety": "The trial evidence shows serious adverse event rates that are generally in line with control groups in most studies, although a subset reported higher rates in the treatment arm. Larger late-phase studies carried more weight, and the observed pattern suggests the need for continued vigilance during broader clinical use.",
    "serious_adverse_events_found": "The dataset points to both expected and less-expected serious events, with expected events occurring more consistently across studies and unexpected events appearing in fewer but notable instances. Where usable SAE rate data was limited, the analysis should be interpreted cautiously and positioned as directional rather than definitive.",
    "regulatory_assessment": "The current safety pattern may support ongoing development with standard risk controls, but any concentration of serious events in specific subgroups could increase regulatory scrutiny. Clear documentation of mitigation steps and post-approval monitoring plans would strengthen the benefit-risk narrative.",
    "post_marketing_safety": "For marketed settings, available post-marketing signals should be monitored for event frequency shifts and emerging clusters that were not prominent in trials. If the molecule is not yet marketed, this section should explain that post-marketing conclusions are preliminary and outline the intended surveillance focus areas."
}}

Writing rules:

- Be more descriptive for the clinical_trial_safety, serious_adverse_events_found sections

Language and Style Guidelines:
    - Do NOT use internal jargon, scoring framework names, or technical modeling terms.    
    - Avoid methodological explanations of how score was derived.   
    - Use clear, simple, business-friendly language.   
    - Translate clinical findings into plain-language impact (e.g., what side effects mean for patients and treatment continuation).

Formatting Requirements:
    - Limit the report (combining all sections) to approximately 2 pages of content.    
    - Use clear headings paragraphs.   
    - Use bullet points where helpful for readability. 

Tone:
    - Professional, objective, and insight-driven.    
    - Focus on clarity, relevance, and business impact
""".strip()

    try:
        response = await gemini_call_without_search(
            prompt=prompt,
            model=model_name,
            # response_mime_type="application/json",
        )
        parsed = safe_json_parse(response, context="balanced_safety_report_sections")
        if isinstance(parsed, dict):
            sections = {}
            for key in SECTION_ORDER:
                value = parsed.get(key)
                sections[key] = _normalize_section_value(value)
            if all(sections.get(k) for k in SECTION_ORDER):
                return sections
    except Exception as e:
        print(f"[ERROR] Exception in _extract_sections_via_prompt: {e}")
        pass
    return _fallback_sections(payload)


async def generate_prompt_safety_report_bytes(
    data: dict,
    model_name: str,
) -> tuple[bytes, dict[str, dict | str | int | float | None], dict]:
    """Generate a balanced PDF report and return PDF bytes plus structured content."""
    payload = _prepare_prompt_payload(data)
    sections = await _extract_sections_via_prompt(payload, model_name=model_name)

    molecule = payload.get("molecule_name", "Unknown")
    dimension = payload.get("dimension_name", "Serious Safety Profile")

    buffer = BytesIO()
    styles = build_styles()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
        leftMargin=0.6 * inch,
        rightMargin=0.6 * inch,
        title=f"{molecule} - {dimension}",
    )

    story = [
        Paragraph(escape_html(dimension), styles["ReportTitle"]),
        Paragraph(
            f"Molecule: <b>{escape_html(molecule)}</b>&nbsp;&nbsp;|&nbsp;&nbsp;{escape_html(date.today().isoformat())}",
            styles["ReportSubtitle"],
        ),
        Spacer(1, 4),
        HRFlowable(width="100%", thickness=1, color=NAVY),
        Spacer(1, 6),
    ]

    score_value = payload.get("safety_score", {}).get("score")
    score_label = payload.get("safety_score", {}).get("score_label")
    total_trials = payload.get("total_trials", 0)

    if score_value is None:
        score_text = "N/A"
    elif score_label:
        score_text = f"{score_value}/5 ({score_label})"
    else:
        score_text = f"{score_value}/5"

    summary_table = {
        "score": score_value,
        "total_trials": total_trials,
    }

    story.append(_build_summary_table(styles, score_text=score_text, total_trials_text=str(total_trials)))
    story.append(Spacer(1, 8))

    for key in SECTION_ORDER:
        section_title = SECTION_TITLES[key]
        section_body = sections.get(key, "")
        story.extend(_build_section_flowables(section_title, section_body, styles))

    story.extend([
        Spacer(1, 6),
        HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#CCCCCC")),
        Paragraph(
            f"Report generated {escape_html(date.today().isoformat())}  |  Analytical narrative generated by Gemini",
            styles["FooterText"],
        ),
    ])

    doc.build(story)
    pdf_bytes = buffer.getvalue()

    report_content: dict[str, dict | str | int | float | None] = {
        "summary_table": summary_table,
        "sections": sections,
    }

    return pdf_bytes, report_content, payload
