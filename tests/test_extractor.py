from types import SimpleNamespace

from doctor_cv.extractor import clean_html, extract_doctor
from doctor_cv.models import Doctor


def test_clean_html_strips_script_and_style():
    html = "<html><head><style>x{}</style></head><body><script>var a=1</script><p>홍길동</p></body></html>"
    cleaned = clean_html(html)
    assert "홍길동" in cleaned
    assert "var a" not in cleaned
    assert "x{}" not in cleaned


class FakeClient:
    """anthropic.Anthropic 대체 — tool_use 블록을 가진 메시지를 반환."""

    def __init__(self, tool_input):
        self._tool_input = tool_input
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        block = SimpleNamespace(type="tool_use", name="record_doctor", input=self._tool_input)
        return SimpleNamespace(content=[block])


def test_extract_doctor_returns_validated_model():
    fake = FakeClient(
        {
            "name": "홍길동",
            "position": "교수",
            "department": "정형외과",
            "specialty": ["척추"],
            "education": [{"institution": "서울대 의대", "degree": "의학박사", "year": "2005"}],
            "licenses": [],
            "career": [{"org": "서울아산병원", "role": "전임의", "period": "2006-2008"}],
            "societies": ["대한정형외과학회"],
            "publications": [],
            "photo_url": None,
        }
    )
    doctor = extract_doctor(
        html="<html><body><p>홍길동 교수 정형외과</p></body></html>",
        hospital="서울아산병원",
        hospital_url="https://www.amc.seoul.kr",
        source_url="https://www.amc.seoul.kr/doctor/1",
        crawled_at="2026-07-20T00:00:00+00:00",
        client=fake,
        model="claude-sonnet-5",
    )
    assert isinstance(doctor, Doctor)
    assert doctor.name == "홍길동"
    assert doctor.department == "정형외과"
    assert doctor.career[0].org == "서울아산병원"
    assert doctor.source_url == "https://www.amc.seoul.kr/doctor/1"
