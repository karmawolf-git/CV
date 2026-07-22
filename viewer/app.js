const DATA_URL = new URLSearchParams(location.search).get("data") || "sample-doctors.json";

// file:// 로 직접 열었거나 데이터 로드 실패 시에도 화면이 비지 않도록 내장하는 샘플
const EMBEDDED_SAMPLE = [
  {
    hospital: "서울아산병원", name: "홍길동", position: "교수", department: "정형외과",
    specialty: ["척추", "척추측만증", "최소침습수술"], profile_url: "https://www.amc.seoul.kr/doctor/1",
    education: [{ institution: "서울대학교 의과대학", degree: "의학박사", year: "2005" }],
    licenses: [{ name: "정형외과 전문의", year: "2003" }],
    career: [{ org: "서울아산병원", role: "교수", period: "2012-현재" }],
    societies: ["대한정형외과학회"], awards: ["대한정형외과학회 학술상 (2018)"], research: ["척추 변형 교정"],
  },
  {
    hospital: "삼성서울병원", name: "김영희", position: "임상조교수", department: "내분비내과",
    specialty: ["당뇨병", "갑상선"], profile_url: "https://www.samsunghospital.com/doctor/2",
    education: [{ institution: "연세대학교 의과대학", degree: "의학박사", year: "2011" }],
    licenses: [{ name: "내분비대사내과 세부전문의", year: "2014" }],
    career: [{ org: "삼성서울병원", role: "임상조교수", period: "2016-현재" }],
    societies: ["대한당뇨병학회"], research: ["제2형 당뇨병 합병증"],
  },
];

let doctors = [];

function setNotice(msg) {
  const el = document.getElementById("notice");
  if (!el) return;
  el.innerHTML = msg || "";
  el.style.display = msg ? "block" : "none";
}

async function load() {
  try {
    const res = await fetch(DATA_URL);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    if (!Array.isArray(data)) throw new Error("데이터 형식이 배열이 아닙니다");
    doctors = data;
    setNotice("");
  } catch (e) {
    // file:// 직접 열기(브라우저가 fetch 차단), 404, JSON 오류 등
    doctors = EMBEDDED_SAMPLE;
    setNotice(
      `⚠️ 데이터 파일을 불러오지 못해 <b>샘플</b>을 표시하고 있습니다 (${escapeHtml(e.message)}).<br>` +
      `실제 데이터를 보려면 위 <b>파일 열기</b> 버튼으로 JSON을 직접 열거나, 폴더에서 로컬 서버로 실행하세요 ` +
      `(<code>python3 -m http.server</code> 후 <code>http://localhost:8000/</code> 접속).`
    );
  }
  initFilters();
  render();
}

function useData(data) {
  doctors = data;
  setNotice("");
  // 필터 옵션 재구성
  for (const id of ["hospital", "dept"]) {
    const sel = document.getElementById(id);
    sel.length = 1; // 첫 옵션(전체) 유지
  }
  const hospitals = [...new Set(doctors.map((d) => d.hospital).filter(Boolean))].sort();
  const depts = [...new Set(doctors.map((d) => d.department).filter(Boolean))].sort();
  fill("hospital", hospitals);
  fill("dept", depts);
  render();
}

function initFileInput() {
  const input = document.getElementById("file");
  if (!input) return;
  input.addEventListener("change", async (ev) => {
    const file = ev.target.files[0];
    if (!file) return;
    try {
      const data = JSON.parse(await file.text());
      if (!Array.isArray(data)) throw new Error("JSON 최상위가 배열이어야 합니다");
      useData(data);
    } catch (e) {
      setNotice(`⚠️ 파일을 읽지 못했습니다: ${escapeHtml(e.message)}`);
    }
  });
}

function initFilters() {
  const hospitals = [...new Set(doctors.map((d) => d.hospital).filter(Boolean))].sort();
  const depts = [...new Set(doctors.map((d) => d.department).filter(Boolean))].sort();
  fill("hospital", hospitals);
  fill("dept", depts);
  document.getElementById("search").addEventListener("input", render);
  document.getElementById("hospital").addEventListener("change", render);
  document.getElementById("dept").addEventListener("change", render);
  initFileInput();
}

function fill(id, values) {
  const sel = document.getElementById(id);
  for (const v of values) {
    const opt = document.createElement("option");
    opt.value = v;
    opt.textContent = v;
    sel.appendChild(opt);
  }
}

function haystack(d) {
  return [d.name, d.hospital, d.department, d.position, ...(d.specialty || [])]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
}

function render() {
  const q = document.getElementById("search").value.trim().toLowerCase();
  const hospital = document.getElementById("hospital").value;
  const dept = document.getElementById("dept").value;
  const filtered = doctors.filter(
    (d) =>
      (!q || haystack(d).includes(q)) &&
      (!hospital || d.hospital === hospital) &&
      (!dept || d.department === dept)
  );
  const LIMIT = 100; // 대량 데이터에서 렌더링 과부하 방지(필터로 좁혀서 확인)
  const shown = filtered.slice(0, LIMIT);
  document.getElementById("count").textContent =
    filtered.length > LIMIT
      ? `${filtered.length}명 (상위 ${LIMIT}명 표시 — 병원/진료과/이름으로 좁혀보세요)`
      : `${filtered.length}명`;

  const list = document.getElementById("list");
  if (!shown.length) {
    list.classList.remove("grid");
    list.innerHTML = `<div class="empty"><div class="big">🔍</div>조건에 맞는 의료진이 없습니다.</div>`;
    return;
  }
  list.classList.add("grid");
  list.innerHTML = shown.map(card).join("");
}

function listBlock(icon, title, items) {
  if (!items || !items.length) return "";
  const lis = items
    .map((it) =>
      typeof it === "string"
        ? `<li>${escapeHtml(it)}</li>`
        : `<li>${escapeHtml([it.institution || it.org || it.name, it.degree || it.role, it.period || it.year].filter(Boolean).join(" · "))}</li>`
    )
    .join("");
  return `<div class="section"><b>${icon} ${title}</b><ul>${lis}</ul></div>`;
}

function initials(name) {
  const n = (name || "").trim();
  return n ? escapeHtml(n.slice(0, 2)) : "?";
}

function avatar(d) {
  if (d.photo_url) {
    return `<img class="avatar" src="${escapeAttr(d.photo_url)}" alt="${escapeAttr(d.name || "")}" loading="lazy" onerror="this.replaceWith(Object.assign(document.createElement('span'),{className:'avatar',textContent:'${initials(d.name)}'}))" />`;
  }
  return `<span class="avatar">${initials(d.name)}</span>`;
}

function card(d) {
  const metaParts = [];
  if (d.hospital) metaParts.push(escapeHtml(d.hospital));
  if (d.department) metaParts.push(escapeHtml(d.department));
  const meta = metaParts.join(` <span class="dot">·</span> `);
  const link = d.profile_url || d.source_url;

  return `<div class="card">
    <div class="card-head">
      ${avatar(d)}
      <div class="who">
        <h2>${escapeHtml(d.name || "")}${d.position ? `<span class="pos">${escapeHtml(d.position)}</span>` : ""}</h2>
        <div class="meta">
          ${meta}
          ${link ? `${meta ? '<span class="dot">·</span>' : ""}<a href="${escapeAttr(link)}" target="_blank" rel="noopener">프로필 ↗</a>` : ""}
        </div>
        ${d.specialty && d.specialty.length ? `<div class="chips">${d.specialty.map((s) => `<span class="chip">${escapeHtml(s)}</span>`).join("")}</div>` : ""}
      </div>
    </div>
    <div class="sections">
      ${listBlock("🎓", "학력", d.education)}
      ${listBlock("📜", "면허·자격", d.licenses)}
      ${listBlock("💼", "경력", d.career)}
      ${listBlock("✈️", "연수", d.training)}
      ${listBlock("👥", "학회활동", d.societies)}
      ${listBlock("🏆", "수상이력", d.awards)}
      ${listBlock("🔬", "연구분야", d.research)}
      ${listBlock("📄", "논문·저서", d.publications)}
    </div>
  </div>`;
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function escapeAttr(s) {
  return escapeHtml(s);
}

load();
