// 단일 파일(?data=...) 또는 병원별 분할(data/manifest.json + data/<file>) 로드.
// GitHub Pages가 수 MB 단일 파일을 잘 못 내보내서, 기본은 병원별 작은 파일로 나눠 받는다.
const SINGLE = new URLSearchParams(location.search).get("data");

let doctors = [];

async function load() {
  try {
    if (SINGLE) {
      doctors = await (await fetch(SINGLE)).json();
    } else {
      const manifest = await (await fetch("data/manifest.json")).json();
      const parts = await Promise.all(
        manifest.map((m) => fetch("data/" + m.file).then((r) => r.json()))
      );
      doctors = parts.flat();
    }
  } catch (e) {
    document.getElementById("count").textContent = "데이터 로드 실패: " + e.message;
    return;
  }
  initFilters();
  render();
}

function initFilters() {
  const hospitals = [...new Set(doctors.map((d) => d.hospital).filter(Boolean))].sort();
  const depts = [...new Set(doctors.map((d) => d.department).filter(Boolean))].sort();
  fill("hospital", hospitals);
  fill("dept", depts);
  document.getElementById("search").addEventListener("input", render);
  document.getElementById("hospital").addEventListener("change", render);
  document.getElementById("dept").addEventListener("change", render);
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

function render() {
  const q = document.getElementById("search").value.trim();
  const hospital = document.getElementById("hospital").value;
  const dept = document.getElementById("dept").value;
  const filtered = doctors.filter(
    (d) =>
      (!q || (d.name || "").includes(q)) &&
      (!hospital || d.hospital === hospital) &&
      (!dept || d.department === dept)
  );
  const LIMIT = 100; // 대량 데이터에서 렌더링 과부하 방지(필터로 좁혀서 확인)
  const shown = filtered.slice(0, LIMIT);
  document.getElementById("count").textContent =
    filtered.length > LIMIT ? `${filtered.length}명 (상위 ${LIMIT}명 표시 — 병원/진료과/이름으로 좁혀보세요)` : `${filtered.length}명`;
  document.getElementById("list").innerHTML = shown.map(card).join("");
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
  return `<div class="card">
    <h2>${escapeHtml(d.name || "")}</h2>
    <div class="meta">${escapeHtml([d.hospital, d.department, d.position].filter(Boolean).join(" · "))}
      ${d.source_url ? `· <a href="${d.source_url}" target="_blank" rel="noopener">출처</a>` : ""}</div>
    ${d.specialty && d.specialty.length ? `<div class="meta">전문분야: ${escapeHtml(d.specialty.join(", "))}</div>` : ""}
    ${listBlock("학력", d.education)}
    ${listBlock("면허·자격", d.licenses)}
    ${listBlock("경력", d.career)}
    ${listBlock("연수", d.training)}
    ${listBlock("학회활동", d.societies)}
    ${listBlock("수상이력", d.awards)}
    ${listBlock("연구분야", d.research)}
    ${listBlock("논문·저서", d.publications)}
  </div>`;
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

load();
