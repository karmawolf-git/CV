const DATA_URL = new URLSearchParams(location.search).get("data") || "sample-doctors.json";

let doctors = [];

async function load() {
  try {
    const res = await fetch(DATA_URL);
    doctors = await res.json();
  } catch (e) {
    doctors = [];
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
