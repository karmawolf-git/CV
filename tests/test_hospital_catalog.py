from doctor_cv.hospital_catalog import load_bed_counts, load_catalog

BASIC_CSV = (
    "요양기관명,종별코드명,시도코드명,병원홈페이지,암호화요양기호\n"
    "서울아산병원,상급종합병원,서울,https://www.amc.seoul.kr,CODE_AMC\n"
    "튼튼종합병원,종합병원,경기,http://ttt.example,CODE_TTT\n"
    "작은의원,의원,서울,http://clinic.example,CODE_CLINIC\n"
    "소형종합병원,종합병원,부산,,CODE_SMALL\n"
)

FACILITY_CSV = (
    "암호화요양기호,총병상수\n"
    "CODE_AMC,2700\n"
    "CODE_TTT,450\n"
    "CODE_SMALL,120\n"
)


def _write(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def test_load_catalog_filters_by_type_only_without_facility(tmp_path):
    basic = _write(tmp_path, "basic.csv", BASIC_CSV)
    cat = load_catalog(basic, facility_path=None, min_beds=300)
    names = {c["name"] for c in cat}
    # 의원 제외, 종합/상급종합만. 병상 파일 없으면 병상 필터 미적용.
    assert names == {"서울아산병원", "튼튼종합병원", "소형종합병원"}
    assert all(c["beds"] is None for c in cat)


def test_load_catalog_applies_bed_filter_with_facility(tmp_path):
    basic = _write(tmp_path, "basic.csv", BASIC_CSV)
    fac = _write(tmp_path, "fac.csv", FACILITY_CSV)
    cat = load_catalog(basic, facility_path=fac, min_beds=300)
    names = {c["name"] for c in cat}
    # 소형종합병원(120)은 300 미만이라 제외. 서울아산(2700), 튼튼(450)만.
    assert names == {"서울아산병원", "튼튼종합병원"}
    amc = next(c for c in cat if c["name"] == "서울아산병원")
    assert amc["beds"] == 2700 and amc["homepage"] == "https://www.amc.seoul.kr"


def test_load_catalog_detects_columns_and_homepage(tmp_path):
    basic = _write(tmp_path, "basic.csv", BASIC_CSV)
    fac = _write(tmp_path, "fac.csv", FACILITY_CSV)
    cat = load_catalog(basic, facility_path=fac, min_beds=300)
    ttt = next(c for c in cat if c["name"] == "튼튼종합병원")
    assert ttt["region"] == "경기"
    assert ttt["type"] == "종합병원"
    assert ttt["homepage"] == "http://ttt.example"


def test_load_bed_counts(tmp_path):
    fac = _write(tmp_path, "fac.csv", FACILITY_CSV)
    beds = load_bed_counts(fac)
    assert beds["CODE_AMC"] == 2700 and beds["CODE_SMALL"] == 120


def test_load_bed_counts_sums_multiple_columns_excluding_noninpatient(tmp_path):
    # 실제 구조: 단일 총병상수 없음. 입원 병상 합산, 수술실/응급실 등은 제외.
    fac_multi = (
        "암호화요양기호,일반입원실상급병상수,일반입원실일반병상수,성인중환자병상수,수술실병상수,응급실병상수\n"
        "CODE_X,100,180,20,15,10\n"
    )
    fac = _write(tmp_path, "facm.csv", fac_multi)
    beds = load_bed_counts(fac)
    # 100+180+20 = 300 (수술실 15, 응급실 10 제외)
    assert beds["CODE_X"] == 300


def test_homepage_none_string_becomes_empty(tmp_path):
    basic = (
        "요양기관명,종별코드명,병원홈페이지,암호화요양기호\n"
        "널병원,종합병원,None,CODE_NULL\n"
    )
    p = _write(tmp_path, "b.csv", basic)
    cat = load_catalog(p, facility_path=None, min_beds=None)
    assert cat[0]["homepage"] == ""
