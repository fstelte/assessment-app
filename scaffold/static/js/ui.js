(function () {
  const ACTIVE_MODALS = [];
  let backdrop = null;

  const createBackdrop = () => {
    if (backdrop) {
      return backdrop;
    }
    const el = document.createElement("div");
    el.className = "modal-backdrop";
    el.dataset.backdrop = "true";
    document.body.appendChild(el);
    backdrop = el;
    return el;
  };

  const destroyBackdrop = () => {
    if (backdrop && ACTIVE_MODALS.length === 0) {
      backdrop.remove();
      backdrop = null;
    }
  };

  const setScrollLock = () => {
    document.documentElement.style.overflow = ACTIVE_MODALS.length ? "hidden" : "";
    document.body.style.overflow = ACTIVE_MODALS.length ? "hidden" : "";
  };

  const resolveTarget = (selectorOrEl) => {
    if (!selectorOrEl) {
      return null;
    }
    if (selectorOrEl instanceof HTMLElement) {
      return selectorOrEl;
    }
    if (selectorOrEl.startsWith("#")) {
      return document.querySelector(selectorOrEl);
    }
    return document.getElementById(selectorOrEl) || document.querySelector(selectorOrEl);
  };

  const openModal = (selectorOrEl) => {
    const modal = resolveTarget(selectorOrEl);
    if (!modal) {
      return null;
    }
    if (ACTIVE_MODALS.includes(modal)) {
      return modal;
    }

    modal.classList.add("show");
    modal.removeAttribute("aria-hidden");
    modal.setAttribute("role", "dialog");
    modal.setAttribute("aria-modal", "true");

    createBackdrop();
    ACTIVE_MODALS.push(modal);
    setScrollLock();
    return modal;
  };

  const closeModal = (selectorOrEl) => {
    const modal = resolveTarget(selectorOrEl);
    if (!modal) {
      return;
    }
    modal.classList.remove("show");
    modal.setAttribute("aria-hidden", "true");

    const index = ACTIVE_MODALS.indexOf(modal);
    if (index !== -1) {
      ACTIVE_MODALS.splice(index, 1);
    }
    destroyBackdrop();
    setScrollLock();
  };

  const toggleCollapse = (button, targetSelector) => {
    const target = resolveTarget(targetSelector);
    if (!target) {
      return;
    }
    const isOpen = target.classList.contains("show");
    target.classList.toggle("show", !isOpen);
    button.setAttribute("aria-expanded", String(!isOpen));
  };

  const bindCollapseToggles = () => {
    document.querySelectorAll("[data-collapse-target]").forEach((button) => {
      const rawTarget = button.getAttribute("data-collapse-target") || "";
      button.addEventListener("click", () => toggleCollapse(button, rawTarget));
    });
  };

  const bindModalTriggers = () => {
    document.querySelectorAll("[data-modal-target]").forEach((button) => {
      const target = button.getAttribute("data-modal-target");
      button.addEventListener("click", () => openModal(target));
    });

    document.querySelectorAll("[data-modal-close]").forEach((button) => {
      button.addEventListener("click", () => {
        const modal = button.closest(".modal");
        closeModal(modal);
      });
    });

    document.querySelectorAll(".modal").forEach((modal) => {
      modal.setAttribute("aria-hidden", "true");
      modal.addEventListener("click", (event) => {
        if (event.target === modal) {
          closeModal(modal);
        }
      });
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && ACTIVE_MODALS.length) {
        const modal = ACTIVE_MODALS[ACTIVE_MODALS.length - 1];
        closeModal(modal);
      }
    });
  };

  document.addEventListener("DOMContentLoaded", () => {
    bindCollapseToggles();
    bindModalTriggers();
  });

  window.tailwindUI = Object.assign(window.tailwindUI || {}, {
    openModal,
    closeModal,
    toggleCollapse,
  });
})();
