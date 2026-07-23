// 단일 파일(?data=...) 또는 병원별 분할(data/manifest.json + data/<file>) 로드.
// GitHub Pages가 수 MB 단일 파일을 잘 못 내보내서, 기본은 병원별 작은 파일로 나눠 받는다.
const SINGLE = new URLSearchParams(location.search).get("data");
const PAGE = 60; // 한 번에 렌더링할 카드 수

let doctors = [];
let filtered = [];
let shownCount = 0;

async function load() {
  const countEl = document.getElementById("count");
  countEl.textContent = "불러오는 중…";
  try {
    if (SINGLE) {
      doctors = await (await fetch(SINGLE)).json();
    } else {
      const manifest = await (await fetch("data/manifest.json")).json();
      const parts = await Promise.all(
        manifest.map((m) => fetch("data/" + m.file).then((r) => r.json()))
      );
      doctors = parts.flat();
      const hospN = new Set(doctors.map((d) => d.hospital).filter(Boolean)).size;
      document.getElementById("subtitle").textContent =
        `공개된 종합병원 의료진 경력 정보 · ${hospN}개 병원 ${doctors.length.toLocaleString()}명`;
    }
  } catch (e) {
    countEl.textContent = "데이터 로드 실패: " + e.message;
    return;
  }
  initFilters();
  document.getElementById("more").addEventListener("click", () => {
    shownCount += PAGE;
    renderList();
  });
  // 상세 경력을 펼치면 카드에 expanded 클래스를 붙여 가로로 넓힌다 (toggle 이벤트는 버블링 안 하므로 capture로 위임)
  document.getElementById("list").addEventListener(
    "toggle",
    (e) => {
      if (e.target.tagName !== "DETAILS") return;
      e.target.closest(".card").classList.toggle("expanded", e.target.open);
    },
    true
  );
  apply();
}

function initFilters() {
  const hospitals = [...new Set(doctors.map((d) => d.hospital).filter(Boolean))].sort();
  const depts = [...new Set(doctors.map((d) => d.department).filter(Boolean))].sort();
  fill("hospital", hospitals);
  fill("dept", depts);
  document.getElementById("search").addEventListener("input", apply);
  document.getElementById("hospital").addEventListener("change", apply);
  document.getElementById("dept").addEventListener("change", apply);
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

// 검색/필터 적용 후 첫 페이지부터 다시 렌더
function apply() {
  const q = document.getElementById("search").value.trim();
  const hospital = document.getElementById("hospital").value;
  const dept = document.getElementById("dept").value;
  filtered = doctors.filter(
    (d) =>
      (!q || (d.name || "").includes(q)) &&
      (!hospital || d.hospital === hospital) &&
      (!dept || d.department === dept)
  );
  shownCount = PAGE;
  renderList();
}

function renderList() {
  const total = filtered.length;
  const shown = filtered.slice(0, shownCount);
  document.getElementById("count").innerHTML = `<b>${total.toLocaleString()}</b>명`;
  const listEl = document.getElementById("list");
  if (total === 0) {
    listEl.innerHTML = `<div class="empty">조건에 맞는 의료진이 없습니다.</div>`;
  } else {
    listEl.innerHTML = shown.map(card).join("");
  }
  const more = document.getElementById("more");
  if (shown.length < total) {
    more.hidden = false;
    more.textContent = `더 보기 (${(total - shown.length).toLocaleString()}명 남음)`;
  } else {
    more.hidden = true;
  }
}

// 병원명 → 안정적인 배지 색상(HSL)
function badgeStyle(hospital) {
  let h = 0;
  for (let i = 0; i < (hospital || "").length; i++) h = (h * 31 + hospital.charCodeAt(i)) % 360;
  return `background:hsl(${h} 60% 92%);color:hsl(${h} 55% 32%)`;
}

function listBlock(title, items) {
  if (!items || !items.length) return "";
  const lis = items
    .map((it) =>
      typeof it === "string"
        ? `<li>${escapeHtml(it)}</li>`
        : `<li>${escapeHtml([it.institution || it.org || it.name, it.degree || it.role, it.period || it.year].filter(Boolean).join(" · "))}</li>`
    )
    .join("");
  return `<div class="section"><b>${title}</b><ul>${lis}</ul></div>`;
}

function card(d) {
  const detail =
    listBlock("학력", d.education) +
    listBlock("면허·자격", d.licenses) +
    listBlock("경력", d.career) +
    listBlock("연수", d.training) +
    listBlock("학회활동", d.societies) +
    listBlock("수상이력", d.awards) +
    listBlock("연구분야", d.research) +
    listBlock("논문·저서", d.publications);
  const src = d.source_url
    ? `<a class="src" href="${escapeHtml(d.source_url)}" target="_blank" rel="noopener">출처 보기 →</a>`
    : "";
  return `<div class="card">
    <div class="card-head">
      <div>
        <p class="name">${escapeHtml(d.name || "")}</p>
        ${d.position ? `<div class="pos">${escapeHtml(d.position)}</div>` : ""}
      </div>
      ${d.hospital ? `<span class="badge" style="${badgeStyle(d.hospital)}">${escapeHtml(d.hospital)}</span>` : ""}
    </div>
    ${d.department ? `<span class="dept">${escapeHtml(d.department)}</span>` : ""}
    ${d.specialty && d.specialty.length ? `<div class="specialty"><span>전문분야</span> ${escapeHtml(d.specialty.join(", "))}</div>` : ""}
    ${detail ? `<details><summary>상세 경력</summary><div class="detail">${detail}</div></details>` : ""}
    ${src}
  </div>`;
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

load();
