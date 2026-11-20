// Radar de IA: lee los JSON que exporta el pipeline y arma la página.
const ACCENT = "#b31b1b";
const GREY = "#c3c8d1";
const PAGE = 15;

const TASKS = {
  "text-generation": "Generación de texto",
  "image-text-to-text": "Imagen y texto a texto",
  "text-to-image": "Texto a imagen",
  "image-to-image": "Imagen a imagen",
  "text-to-video": "Texto a video",
  "image-to-video": "Imagen a video",
  "text-to-speech": "Texto a voz",
  "automatic-speech-recognition": "Voz a texto",
  "audio-to-audio": "Audio a audio",
  "feature-extraction": "Embeddings",
  "sentence-similarity": "Similitud de frases",
  "text-classification": "Clasificación de texto",
  "any-to-any": "Cualquier formato",
  "image-to-text": "Imagen a texto",
  "robotics": "Robótica",
  "depth-estimation": "Estimación de profundidad",
  "mask-generation": "Segmentación de imágenes",
  "sin tarea": "Sin tarea declarada",
};

const nf = new Intl.NumberFormat("es-AR");
const pct = (x, digits = 1) => `${(x * 100).toLocaleString("es-AR", { maximumFractionDigits: digits, minimumFractionDigits: digits })} %`;
const pts = (x) => `${x > 0 ? "+" : ""}${(x * 100).toLocaleString("es-AR", { maximumFractionDigits: 1, minimumFractionDigits: 1 })} puntos`;
const asDate = (s) => new Date(`${s}T00:00:00Z`);
const longDate = (s) => asDate(s).toLocaleDateString("es-AR", { day: "numeric", month: "long", timeZone: "UTC" });
const shortDate = (s) => asDate(s).toLocaleDateString("es-AR", { day: "numeric", month: "short", timeZone: "UTC" });
const taskName = (t) => TASKS[t] ?? t.replaceAll("-", " ");
const $ = (id) => document.getElementById(id);

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") node.className = v;
    else node.setAttribute(k, v);
  }
  node.append(...children);
  return node;
}

const state = { topic: null, query: "", all: false, shown: PAGE, task: "", models: PAGE };
let radar, papers, topics;

async function main() {
  try {
    [radar, papers] = await Promise.all(
      ["data/radar.json", "data/papers.json"].map((u) => fetch(u).then((r) => { if (!r.ok) throw new Error(u); return r.json(); }))
    );
  } catch {
    $("dek").textContent = "No se pudieron cargar los datos. Recargá la página en unos minutos.";
    return;
  }
  topics = new Map(radar.topics.map((t) => [t.id, t]));
  const grower = [...radar.topics].sort((a, b) => (b.change ?? 0) - (a.change ?? 0))[0];
  state.topic = grower.id;

  renderOpening(grower);
  renderTopicList();
  renderTopic();
  renderModels();
  renderHow();

  $("search").addEventListener("input", (e) => { state.query = e.target.value.trim().toLowerCase(); state.shown = PAGE; renderPapers(); });
  $("all-topics").addEventListener("change", (e) => { state.all = e.target.checked; state.shown = PAGE; renderPapers(); });
  $("more").addEventListener("click", () => { state.shown += PAGE; renderPapers(); });
  $("task").addEventListener("change", (e) => { state.task = e.target.value; state.models = PAGE; renderModelRows(); });
  $("more-models").addEventListener("click", () => { state.models += PAGE; renderModelRows(); });
  let resize;
  addEventListener("resize", () => { clearTimeout(resize); resize = setTimeout(renderChart, 150); });
}

function renderOpening(grower) {
  const weeks = new Set(radar.weekly.map((d) => d.week)).size;
  if (grower.change != null && grower.change >= 0.005) {
    $("headline").textContent = `Los papers sobre ${grower.name.toLowerCase()} pasaron del ${pct(grower.share_start)} al ${pct(grower.share_end)} de todo lo que se publica en IA`;
  }
  $("dek").textContent = `${nf.format(radar.papers_total)} papers de inteligencia artificial publicados en arXiv desde el ${longDate(radar.coverage.first_day)}, agrupados por tema. ${weeks >= 8 ? `Se comparan las primeras 4 de ${weeks} semanas con las últimas 4. ` : ""}Se actualiza todos los días.`;
}

function renderTopicList() {
  const list = $("topic-list");
  list.replaceChildren(...radar.topics.map((t) => {
    const c = Math.round((t.change ?? 0) * 1000) / 1000;  // a una décima de punto, como se muestra
    const weeks = new Set(radar.weekly.map((d) => d.week)).size;
    const change = t.change == null ? "" : c === 0 ? `Sin cambios en ${weeks} semanas` : `${c > 0 ? "▲" : "▼"} ${pts(Math.abs(c)).replace("+", "")} en ${weeks} semanas`;
    const b = el("button", { type: "button", role: "radio", "data-topic": t.id },
      el("span", { class: "name" }, t.name),
      el("span", { class: "share" }, t.share_end == null ? "" : pct(t.share_end, 0)),
      el("span", { class: "change" }, change));
    b.addEventListener("click", () => selectTopic(t.id));
    return b;
  }));
  // Flechas del teclado para moverse entre temas, como en cualquier grupo de opciones.
  list.addEventListener("keydown", (e) => {
    const ids = radar.topics.map((t) => t.id);
    const step = { ArrowDown: 1, ArrowRight: 1, ArrowUp: -1, ArrowLeft: -1 }[e.key];
    if (!step) return;
    e.preventDefault();
    const next = ids[(ids.indexOf(state.topic) + step + ids.length) % ids.length];
    selectTopic(next);
    list.querySelector(`[data-topic="${next}"]`).focus();
  });
}

function selectTopic(id) {
  if (id === state.topic) return;
  state.topic = id;
  state.shown = PAGE;
  renderTopic();
}

function renderTopic() {
  for (const b of $("topic-list").children) {
    const on = b.dataset.topic === state.topic;
    b.setAttribute("aria-checked", on);
    b.tabIndex = on ? 0 : -1;
  }
  const t = topics.get(state.topic);
  const note = $("topic-note");
  note.replaceChildren(el("strong", {}, t.name), `: ${t.description} `);
  if (t.share_end != null) {
    note.append(`En las últimas 4 semanas aparece en el título del ${pct(t.share_end)} de los papers; al principio del período, del ${pct(t.share_start)}.`);
  }
  renderChart();
  renderPapers();
}

function renderChart() {
  const box = $("chart");
  const width = box.clientWidth || 640;
  const data = radar.weekly.map((d) => ({ ...d, date: asDate(d.week), name: topics.get(d.topic).name }));
  const sel = data.filter((d) => d.topic === state.topic);
  const plot = Plot.plot({
    width,
    height: Math.max(260, Math.min(400, width * 0.55)),
    marginLeft: 44,
    marginRight: 12,
    style: { fontFamily: "inherit", fontSize: "13px", color: "#5d6370" },
    x: { type: "utc", label: null, tickFormat: (d) => d.toLocaleDateString("es-AR", { day: "numeric", month: "short", timeZone: "UTC" }), ticks: width < 500 ? 4 : 8 },
    y: { label: null, grid: true, tickFormat: (d) => `${Math.round(d * 100)} %`, domain: [0, Math.max(...data.map((d) => d.share)) * 1.08] },
    marks: [
      Plot.lineY(data.filter((d) => d.topic !== state.topic), { x: "date", y: "share", z: "topic", stroke: GREY, strokeWidth: 1.2, curve: "monotone-x" }),
      Plot.lineY(sel, { x: "date", y: "share", stroke: ACCENT, strokeWidth: 2.6, curve: "monotone-x" }),
      Plot.dot(sel.slice(-1), { x: "date", y: "share", fill: ACCENT, r: 4 }),
      Plot.text(sel.slice(-1), { x: "date", y: "share", text: (d) => pct(d.share, 0), dy: -14, fill: ACCENT, fontWeight: 700, fontSize: 14 }),
      Plot.tip(data, Plot.pointer({
        x: "date", y: "share", z: "topic",
        title: (d) => `${d.name}\nSemana del ${shortDate(d.week)}: ${pct(d.share)}\n${nf.format(d.papers)} de ${nf.format(d.total)} papers\nTocá para elegir este tema`,
      })),
    ],
  });
  plot.setAttribute("aria-label", `Proporción semanal de papers por tema. Resaltado: ${topics.get(state.topic).name}.`);
  plot.addEventListener("click", () => { if (plot.value) selectTopic(plot.value.topic); });
  box.replaceChildren(plot);
}

function renderPapers() {
  const t = topics.get(state.topic);
  const pool = state.all ? papers : papers.filter((p) => p.topics.includes(state.topic));
  const hits = state.query ? pool.filter((p) => p.title.toLowerCase().includes(state.query)) : pool;
  const days = papers.length ? `entre el ${longDate(papers.at(-1).date)} y el ${longDate(papers[0].date)}` : "";
  $("papers-lead").textContent = state.all
    ? `${nf.format(papers.length)} papers de IA publicados ${days}.`
    : `${nf.format(pool.length)} de los ${nf.format(papers.length)} papers publicados ${days} tratan sobre ${t.name.toLowerCase()}. Cambiá el tema arriba o mirá todos.`;

  const list = $("paper-list");
  if (!hits.length) {
    list.replaceChildren(el("li", { class: "empty" }, state.query ? `Ningún título contiene “${state.query}”. Probá con otra palabra o marcá “Todos los temas”.` : "No hay papers de este tema en los últimos días."));
  } else {
    list.replaceChildren(...hits.slice(0, state.shown).map((p) => el("li", {},
      el("a", { href: `https://arxiv.org/abs/${p.id}`, target: "_blank", rel: "noopener" }, p.title),
      el("div", { class: "meta" }, `${shortDate(p.date)}, ${p.category}${p.topics.length ? `. Temas: ${p.topics.map((id) => topics.get(id).name.toLowerCase()).join(", ")}` : ""}`))));
  }
  const more = $("more");
  more.hidden = hits.length <= state.shown;
  more.textContent = `Ver más papers (quedan ${nf.format(Math.max(0, hits.length - state.shown))})`;
}

function renderModels() {
  const hf = radar.hf;
  if (!hf.length) { $("models-lead").textContent = "Todavía no hay fotos de Hugging Face."; $("models-wrap").hidden = true; $("task").parentElement.hidden = true; return; }
  const counts = d3.rollups(hf, (v) => v.length, (d) => d.task).sort((a, b) => b[1] - a[1]);
  const [topTask, topCount] = counts[0];
  const fresh = hf.filter((m) => m.previous_date && m.previous_rank == null).length;
  $("models-lead").textContent = `Los 100 modelos que más crecen hoy en Hugging Face. ${topCount} son de ${taskName(topTask).toLowerCase()}, la tarea más común.` +
    (hf[0].previous_date ? ` ${fresh} entraron a la lista desde ayer.` : " El cambio de puesto aparece desde la segunda foto diaria.");
  $("models-table").classList.toggle("no-prev", !hf[0].previous_date);
  $("task").append(...counts.map(([task, n]) => el("option", { value: task }, `${taskName(task)} (${n})`)));
  renderModelRows();
}

function movement(m) {
  if (!m.previous_date) return el("span", { class: "same" }, "");
  if (m.previous_rank == null) return el("span", { class: "new" }, "nuevo");
  const d = m.previous_rank - m.rank;
  if (d > 0) return el("span", { class: "up", title: `Subió ${d} puestos` }, `▲ ${d}`);
  if (d < 0) return el("span", { class: "down", title: `Bajó ${-d} puestos` }, `▼ ${-d}`);
  return el("span", { class: "same", title: "Mismo puesto" }, "=");
}

function renderModelRows() {
  const rows = radar.hf.filter((m) => !state.task || m.task === state.task);
  const more = $("more-models");
  more.hidden = rows.length <= state.models;
  more.textContent = `Ver más modelos (quedan ${rows.length - state.models})`;
  $("models-table").tBodies[0].replaceChildren(...rows.slice(0, state.models).map((m) => {
    const [author, name] = m.model_id.includes("/") ? m.model_id.split("/") : ["", m.model_id];
    return el("tr", {},
      el("td", {}, String(m.rank)),
      el("td", { class: "move" }, movement(m)),
      el("td", { class: "model" }, el("a", { href: `https://huggingface.co/${m.model_id}`, target: "_blank", rel: "noopener" },
        author ? el("span", { class: "author" }, `${author}/`) : "", name)),
      el("td", {}, taskName(m.task)),
      el("td", { class: "num" }, nf.format(m.likes ?? 0)),
      el("td", { class: "num" }, nf.format(m.days_trending)));
  }));
}

function renderHow() {
  const n = radar.pipeline.tables;
  const steps = [
    ["Extracción", ["Pide a la API de arXiv los papers de cada día (", el("b", {}, nf.format(radar.coverage.days)), " días) y saca una foto diaria de los modelos en tendencia de Hugging Face."]],
    ["Capa cruda", ["Guarda cada respuesta tal cual, un archivo JSONL comprimido por día. Si una corrida se corta, la siguiente completa solo lo que falta."]],
    ["Staging", ["Carga todo en SQLite y lo limpia con SQL: ", el("b", {}, nf.format(n.raw_arxiv)), " filas crudas quedan en ", el("b", {}, nf.format(n.stg_papers)), " papers únicos, uno por paper en su última versión."]],
    ["Temas", ["Etiqueta cada paper con reglas sobre su título: ", el("b", {}, nf.format(n.fct_paper_topics)), " etiquetas en ", el("b", {}, String(radar.topics.length)), " temas."]],
    ["Marts", ["Calcula la proporción semanal por tema, cuánto cambió cada uno y los movimientos del ranking de modelos."]],
    ["Publicación", ["Corre los controles de calidad, exporta JSON chico y publica esta página en GitHub Pages. Toda la corrida tarda ", el("b", {}, `${nf.format(radar.pipeline.seconds)} s`), "."]],
  ];
  $("flow").replaceChildren(...steps.map(([step, what]) => el("li", {}, el("span", { class: "step" }, step), el("span", { class: "what" }, ...what))));
  $("checks").replaceChildren(...radar.pipeline.checks.map((c) => el("li", {},
    el("span", { class: `mark ${c.passed ? "ok" : "warn"}`, "aria-label": c.passed ? "Pasó" : "Aviso" }, c.passed ? "✓" : "!"),
    el("span", {}, c.description))));
  const when = new Date(radar.generated_at).toLocaleString("es-AR", { dateStyle: "long", timeStyle: "short", timeZone: "America/Argentina/Buenos_Aires" });
  $("updated").textContent = `Actualizado el ${when} (hora de Argentina).`;
}

main();
