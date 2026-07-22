from doctor_cv.deptfilter import dept_matches, parse_depts_arg
from doctor_cv.adapters import amc, smc, snubh, cmc, kumc


def test_dept_matches_substring():
    assert dept_matches("순환기내과", ["내과"]) is True
    assert dept_matches("가정의학과", ["내과"]) is False
    assert dept_matches("아무거나", None) is True  # 필터 없으면 전체 허용
    # '신경과'는 '신경외과'를 포함하지 않는다(서로 다른 과).
    assert dept_matches("신경외과", ["신경과"]) is False
    assert dept_matches("신경과", ["신경과"]) is True


def test_parse_depts_arg():
    assert parse_depts_arg("가정의학과, 내과 ,정형외과") == ["가정의학과", "내과", "정형외과"]
    assert parse_depts_arg("") is None
    assert parse_depts_arg(None) is None


def test_adapter_parse_departments_return_names():
    # 각 어댑터가 (코드,이름)/(tp,코드,이름)을 파싱하는지.
    amc_html = "<a onclick=\"fnSelectDeptPopup('D001')\">가정의학과</a><a onclick=\"fnSelectDeptPopup('D003')\">내과</a>"
    assert ("D001", "가정의학과") in amc.parse_departments(amc_html)

    smc_html = '<option value="FM">가정의학과</option><option value="IM1">순환기내과</option>'
    assert ("IM1", "순환기내과") in smc.parse_departments(smc_html)

    snubh_xml = "<DEPT><NM>가정의학과</NM><TP>O</TP><DPCD>FM</DPCD></DEPT>"
    assert ("O", "FM", "가정의학과") in snubh.parse_departments(snubh_xml)

    cmc_json = '[{"deptCd":"1","deptNm":"가정의학과"},{"deptCd":"6","deptNm":"간담췌외과"}]'
    assert ("1", "가정의학과") in cmc.parse_departments(cmc_json)

    kumc_json = '{"deptList":[{"deptCd":"GRFM","deptNm":"가정의학과"},{"deptCd":"GRL1","deptNm":"순환기내과"}]}'
    assert ("GRL1", "순환기내과") in kumc.parse_departments(kumc_json)


def test_amc_iter_filters_by_dept():
    INDEX = "<a onclick=\"fnSelectDeptPopup('D001')\">가정의학과</a><a onclick=\"fnSelectDeptPopup('D003')\">피부과</a>"
    LIST = "<a onclick=\"fnDrDetail('E1','D001');\"></a>"

    def fetch(url):
        return INDEX if url == amc.dept_index_url() else LIST

    refs = list(amc.iter_doctor_refs(fetch, depts=["가정의학과"]))
    assert refs == [("D001", "E1")]  # 피부과(D003)는 제외


def test_kumc_iter_filters_by_dept():
    DEPTS = '{"deptList":[{"deptCd":"GRFM","deptNm":"가정의학과"},{"deptCd":"GRDERM","deptNm":"피부과"}]}'
    L1 = '{"doctorTotCnt":1,"doctorList":[{"drNo":"7454","drName":"강동오"}]}'
    EMPTY = '{"doctorTotCnt":1,"doctorList":[]}'

    def fetch(url):
        if "department.do" in url:
            return DEPTS
        if "deptCd=GRFM" in url and "startIndex=1&" in url:
            return L1
        return EMPTY

    ids = list(kumc.iter_doctor_ids(fetch, "https://guro.kumc.or.kr", "2", depts=["가정의학과"]))
    assert ids == ["7454"]  # 피부과 제외
