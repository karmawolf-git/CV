from doctor_cv.adapters import amc

INDEX_HTML = """
<html><body>
  <a href="#" onclick="fnSelectDeptPopup('D001'); return false;">가정의학과</a>
  <a href="#" onclick="fnSelectDeptPopup('D003'); return false;">내과</a>
  <a href="#" onclick="fnSelectDeptPopup('D001'); return false;">가정의학과(중복)</a>
</body></html>
"""

# 의사 카드마다 fnDrDetail 링크가 3번씩(사진/이름/상세보기) 나오는 실제 구조를 모사.
LIST_HTML = """
<html><body>
  <div class="doctor_photo"><a onclick="fnDrDetail('EMP_A','D001');return false;"></a></div>
  <div class="name"><a onclick="fnDrDetail('EMP_A','D001');return false;">홍길동</a></div>
  <a onclick="fnDrDetail('EMP_A','D001');return false;">상세보기</a>
  <div class="doctor_photo"><a onclick="fnDrDetail('EMP_B','D001');return false;"></a></div>
  <a onclick="fnDrDetail('EMP_B','D001');return false;">상세보기</a>
</body></html>
"""


def test_parse_dept_codes_dedups_in_order():
    assert amc.parse_dept_codes(INDEX_HTML) == ["D001", "D003"]


def test_parse_doctor_ids_dedups_in_order():
    assert amc.parse_doctor_ids(LIST_HTML) == ["EMP_A", "EMP_B"]


def test_list_url_and_detail_url_have_expected_params():
    lu = amc.list_url("D001")
    assert amc.LIST_PATH in lu and "searchHpCd=D001" in lu
    du = amc.detail_url("EMP_A", "D001")
    assert amc.DETAIL_PATH in du and "drEmpId=EMP_A" in du and "searchHpCd=D001" in du


def test_iter_detail_urls_dedups_across_depts_and_respects_limits():
    calls = []

    def fake_fetch(url):
        calls.append(url)
        if url == amc.dept_index_url():
            return INDEX_HTML
        return LIST_HTML  # 두 진료과 모두 EMP_A, EMP_B 반환

    # 진료과 2개지만 EMP_A/EMP_B는 전역 중복제거 → 2명만.
    results = list(amc.iter_detail_urls(fake_fetch))
    emp_ids = [u for _, u in results]
    assert len(results) == 2
    assert any("EMP_A" in u for u in emp_ids)
    assert any("EMP_B" in u for u in emp_ids)

    # 한도 적용: 진료과 1개 × 의사 1명 = 1건.
    limited = list(amc.iter_detail_urls(fake_fetch, max_depts=1, max_per_dept=1))
    assert len(limited) == 1
