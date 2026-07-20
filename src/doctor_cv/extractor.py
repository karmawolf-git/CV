from __future__ import annotations

import os

from bs4 import BeautifulSoup

from .models import Doctor

DEFAULT_MODEL = os.environ.get("DOCTOR_CV_MODEL", "claude-sonnet-5")

EXTRACT_TOOL = {
    "name": "record_doctor",
    "description": "의료진 소개 페이지에서 한 명의 의사 경력 정보를 구조화하여 기록한다.",
    "input_schema": {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "의사 이름"},
            "position": {"type": ["string", "null"], "description": "직위 (예: 교수, 전문의)"},
            "department": {"type": ["string", "null"], "description": "진료과"},
            "specialty": {"type": "array", "items": {"type": "string"}, "description": "전문분야"},
            "photo_url": {"type": ["string", "null"]},
            "education": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "institution": {"type": "string"},
                        "degree": {"type": ["string", "null"]},
                        "year": {"type": ["string", "null"]},
                    },
                    "required": ["institution"],
                },
            },
            "licenses": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "year": {"type": ["string", "null"]},
                    },
                    "required": ["name"],
                },
            },
            "career": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "org": {"type": "string"},
                        "role": {"type": ["string", "null"]},
                        "period": {"type": ["string", "null"]},
                    },
                    "required": ["org"],
                },
            },
            "societies": {"type": "array", "items": {"type": "string"}},
            "publications": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["name"],
    },
}

PROMPT = (
    "다음은 한 병원의 의료진 소개 페이지 텍스트다. 여기서 의사 1명의 경력 정보를 "
    "record_doctor 도구 스키마에 맞춰 추출하라. 페이지에 없는 항목은 빈 배열이나 null로 두고, "
    "지어내지 마라. 개인 연락처는 수집하지 마라.\n\n---\n"
)


def clean_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer"]):
        tag.decompose()
    return soup.get_text(separator=" ", strip=True)


def extract_doctor(
    html: str,
    *,
    hospital: str,
    hospital_url: str,
    source_url: str,
    crawled_at: str,
    client=None,
    model: str | None = None,
) -> Doctor:
    if client is None:
        import anthropic

        client = anthropic.Anthropic()
    model = model or DEFAULT_MODEL

    content = clean_html(html)
    message = client.messages.create(
        model=model,
        max_tokens=2000,
        tools=[EXTRACT_TOOL],
        tool_choice={"type": "tool", "name": "record_doctor"},
        messages=[{"role": "user", "content": PROMPT + content}],
    )
    tool_use = next(b for b in message.content if getattr(b, "type", None) == "tool_use")
    data = dict(tool_use.input)
    data.update(
        hospital=hospital,
        hospital_url=hospital_url,
        source_url=source_url,
        crawled_at=crawled_at,
    )
    return Doctor(**data)
