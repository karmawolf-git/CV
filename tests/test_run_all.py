from doctor_cv.run_all import run_all
from doctor_cv.models import Doctor


def _fake_extract(html, *, hospital, hospital_url, source_url, crawled_at):
    return Doctor(
        hospital=hospital, hospital_url=hospital_url, name="의사",
        profile_url=source_url, source_url=source_url, crawled_at=crawled_at,
    )


def test_run_all_no_llm_collects_cmc_and_isolates_errors():
    # CMC 4곳: 1곳은 정상 JSON, 나머지는 실패시켜 격리 확인.
    DEPT = '[{"deptCd":"1","deptNm":"가정의학과","deptClsf":"A"}]'
    DOC = '[{"drNo":"D1","drName":"홍길동","nuHptlJobTitle":"교수","doctorDept":{"deptNm":"가정의학과","nuSpecial":"간"}}]'

    def fetch(url):
        if "cmcseoul" in url:
            return DEPT if "/api/department" in url else DOC
        raise RuntimeError("unreachable")  # 나머지 CMC 도메인 실패

    docs, summary = run_all(
        fetch, now="2026-07-21T00:00:00+00:00", extract=_fake_extract,
        include_llm=False,
    )
    # 서울성모만 성공(1명), 나머지 3곳은 error 기록.
    assert summary["가톨릭대학교 서울성모병원"]["doctors"] == 1
    assert summary["가톨릭대학교 부천성모병원"]["error"] is not None
    assert len(docs) == 1
    # LLM 병원은 include_llm=False라 요약에 없음
    assert "서울아산병원" not in summary
