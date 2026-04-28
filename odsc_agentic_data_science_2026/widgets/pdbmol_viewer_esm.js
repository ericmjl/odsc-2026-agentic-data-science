/** Anywidget AFM: load 3Dmol.js once and render PDB structures by ID (RCSB). */
const THREEDMOL_SRC =
  "https://cdn.jsdelivr.net/npm/3dmol@2.5.2/build/3Dmol-min.js";

function loadScriptOnce(src) {
  return new Promise((resolve, reject) => {
    if (typeof window.$3Dmol !== "undefined") {
      resolve();
      return;
    }
    const existing = document.querySelector('script[data-pdbmol-widget="1"]');
    if (existing) {
      existing.addEventListener("load", () => resolve());
      existing.addEventListener("error", () =>
        reject(new Error(`failed to load ${src}`)),
      );
      return;
    }
    const s = document.createElement("script");
    s.src = src;
    s.async = true;
    s.dataset.pdbmolWidget = "1";
    s.onload = () => resolve();
    s.onerror = () => reject(new Error(`failed to load ${src}`));
    document.head.appendChild(s);
  });
}

function normalizePdbId(raw) {
  const s = String(raw ?? "").trim().toUpperCase();
  const m = s.match(/^([1-9][A-Z0-9]{3})$/);
  return m ? m[1] : "";
}

/** @param {{ model: import("@jupyter-widgets/base").DOMWidgetModel, el: HTMLElement }} ctx */
function render({ model, el }) {
  el.innerHTML = "";

  const wrap = document.createElement("div");
  wrap.style.width = `${model.get("width")}px`;
  wrap.style.height = `${model.get("height")}px`;
  wrap.style.border = "1px solid #cbd5e1";
  wrap.style.borderRadius = "6px";
  wrap.style.overflow = "hidden";
  wrap.style.boxSizing = "border-box";
  el.appendChild(wrap);

  loadScriptOnce(THREEDMOL_SRC)
    .then(() => {
      const viewer = window.$3Dmol.createViewer(wrap, {
        backgroundColor: "#ffffff",
      });

      function resizeWrap() {
        wrap.style.width = `${model.get("width")}px`;
        wrap.style.height = `${model.get("height")}px`;
        if (typeof viewer.resize === "function") viewer.resize();
      }

      function loadStructure() {
        const code = normalizePdbId(model.get("pdb_id"));
        viewer.clear();
        if (!code) return;
        window.$3Dmol.download(`pdb:${code}`, viewer, {}, () => {
          viewer.setStyle({}, { cartoon: { color: "spectrum" } });
          viewer.zoomTo();
          viewer.render();
        });
      }

      loadStructure();
      model.on("change:pdb_id", loadStructure);
      model.on("change:width", resizeWrap);
      model.on("change:height", resizeWrap);
    })
    .catch((err) => {
      el.textContent = String(err);
      el.style.color = "#b91c1c";
      el.style.fontFamily = "system-ui, sans-serif";
      el.style.padding = "8px";
    });
}

export default { render };
