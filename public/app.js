"use strict";
// Los visitantes leen solo el archivo estático de GitHub Pages: nunca consultan Registradores.
const POLL_MS = 10 * 60 * 1000;
let currentData = null;
let isLoading = false;
const put = (id, value) => {
  const element = document.getElementById(id);
  if (element) element.textContent = value;
};
const formatDay = (value) => new Date(value + "T12:00:00Z").toLocaleDateString("es-ES", {
  day: "numeric", month: "long", timeZone: "Europe/Madrid"
});
const formatMoment = (value) => {
  const moment = new Date(value);
  return Number.isNaN(moment.getTime()) ? "fecha desconocida" : moment.toLocaleString("es-ES", {
    timeZone: "Europe/Madrid", day: "2-digit", month: "short",
    hour: "2-digit", minute: "2-digit"
  });
};
function isExpectedSessionWindow() {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: "Europe/Madrid", weekday: "short", hour: "2-digit", hourCycle: "h23"
  }).formatToParts(new Date());
  const weekday = parts.find((part) => part.type === "weekday")?.value;
  const hour = Number(parts.find((part) => part.type === "hour")?.value);
  return ["Mon", "Tue", "Wed", "Thu"].includes(weekday) && hour >= 9 && hour < 22;
}
function describeStatus(data) {
  const synced = data.checked_at ? Date.parse(data.checked_at) : NaN;
  const stale = !Number.isFinite(synced) || Date.now() - synced > 2 * 60 * 60 * 1000;
  const warning = stale && isExpectedSessionWindow()
    ? "AVISO: SIN SINCRONIZACIÓN RECIENTE · "
    : "";
  const lastMessage = data.source_last_at
    ? formatMoment(data.source_last_at)
    : (data.updated || "fecha desconocida");
  const lastCheck = Number.isFinite(synced) ? formatMoment(data.checked_at) : "no disponible";
  return warning + "Último parte oficial: " + lastMessage +
    " · Verificado: " + lastCheck + " · " + (data.mode || "Seguimiento");
}
function render(data) {
  for (const key of ["entries", "finished", "withdrawn", "advance"]) {
    put(key, data.means?.[key]?.toLocaleString("es-ES") ?? "—");
  }
  put("last", data.last ?? "Dato reservado");
  put("forecast", data.forecast || "Sin estimación publicada");
  put("coverage", "Medias sobre " + (data.complete ?? 0) +
    " jornadas completas. La jornada abierta no entra en la media.");
  put("status", describeStatus(data));

  const container = document.getElementById("probabilities");
  if (container) {
    container.replaceChildren();
    if (Array.isArray(data.probabilities) && data.probabilities.length) {
      for (const item of data.probabilities) {
        const card = document.createElement("article");
        card.className = "prob-card";
        const title = document.createElement("h3");
        title.textContent = item.date ? formatDay(item.date) : "Otras fechas";
        const value = document.createElement("strong");
        value.textContent = Number(item.percent).toLocaleString("es-ES", {
          minimumFractionDigits: 1, maximumFractionDigits: 1
        }) + " %";
        const bar = document.createElement("progress");
        bar.max = 100;
        bar.value = Number(item.percent);
        bar.setAttribute("aria-label", title.textContent + ": " + value.textContent);
        card.append(title, value, bar);
        container.append(card);
      }
    } else {
      const empty = document.createElement("p");
      empty.textContent = "Sin pronóstico público disponible.";
      container.append(empty);
    }
  }
  if (data.next_call) {
    const call = data.next_call;
    put("call-range", call.from == null
      ? "Rango disponible en el parte oficial"
      : "Del nº " + call.from + " al nº " + call.to);
    put("call-date", formatDay(call.date) +
      (call.time ? " · " + call.time + " h (Madrid)" : "") +
      " · según el último anuncio recogido");
  } else {
    put("call-range", "Sin convocatoria futura identificada");
    put("call-date", "Consulta el parte oficial para confirmar el llamamiento.");
  }
}
async function refresh() {
  if (isLoading) return;
  isLoading = true;
  try {
    // URL nueva en cada consulta: evita reutilizar una copia antigua de data.js.
    const url = new URL("data.js", document.baseURI);
    url.searchParams.set("_", String(Date.now()));
    const response = await fetch(url, { cache: "no-store" });
    if (!response.ok) throw new Error("HTTP " + response.status);
    const raw = (await response.text()).trim();
    const prefix = /^window\.SHURMAN\s*=\s*/;
    if (!prefix.test(raw)) throw new Error("Formato de datos inesperado");
    const data = JSON.parse(raw.replace(prefix, "").replace(/;\s*$/, ""));
    if (!data || typeof data !== "object" || !data.means || !data.updated) {
      throw new Error("Faltan campos en el informe");
    }
    currentData = data;
    render(data);
  } catch (error) {
    put("status", (currentData
      ? "NO SE PUDO COMPROBAR LA ACTUALIZACIÓN · mostrando último informe cargado. "
      : "NO SE PUDO CARGAR EL SEGUIMIENTO. ") +
      "Prueba a recargar más tarde.");
    console.warn("Seguimiento no disponible:", error);
  } finally {
    isLoading = false;
  }
}
refresh();
setInterval(() => {
  if (document.visibilityState === "visible") refresh();
}, POLL_MS);
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "visible") refresh();
});
window.addEventListener("online", refresh);
