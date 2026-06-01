(function () {
  const dataEl = document.getElementById("pipeline-details-data");
  const strip = document.querySelector(".pipeline-detail-strip");
  if (!dataEl || !strip) return;

  let detailsMap;
  try {
    detailsMap = JSON.parse(dataEl.textContent || "{}");
  } catch {
    return;
  }

  const titleEl = strip.querySelector(".pipeline-detail-strip-title");
  const bodyEl = strip.querySelector(".pipeline-detail-strip-body");
  let pinnedId = null;

  function setActive(el) {
    document
      .querySelectorAll(".pipeline-active, .pipeline-pinned")
      .forEach((n) => {
        if (n !== el) {
          n.classList.remove("pipeline-active");
          if (!n.classList.contains("pipeline-stage--core") || n.dataset.detailId !== pinnedId) {
            n.classList.remove("pipeline-pinned");
          }
        }
      });
    if (el) el.classList.add("pipeline-active");
  }

  function showDetail(id, el) {
    const entry = detailsMap[id];
    if (!entry) return;
    setActive(el);
    if (titleEl) titleEl.textContent = entry.title || "";
    if (bodyEl) bodyEl.innerHTML = entry.html || "";
  }

  function bind(el) {
    const id = el.dataset.detailId;
    if (!id) return;

    el.addEventListener("mouseenter", () => {
      if (pinnedId && el.classList.contains("pipeline-stage--core") && pinnedId !== id) {
        /* still preview on hover */
      }
      showDetail(id, el);
    });

    el.addEventListener("focus", () => showDetail(id, el));

    if (el.classList.contains("pipeline-stage--core")) {
      el.addEventListener("click", () => {
        if (pinnedId === id) {
          pinnedId = null;
          el.classList.remove("pipeline-pinned");
        } else {
          document.querySelectorAll(".pipeline-pinned").forEach((n) => n.classList.remove("pipeline-pinned"));
          pinnedId = id;
          el.classList.add("pipeline-pinned");
          showDetail(id, el);
        }
      });
    }
  }

  document.querySelectorAll("[data-detail-id]").forEach(bind);
})();
