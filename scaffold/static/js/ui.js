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
    // Updated logic for Tailwind 'hidden' class toggle
    // Instead of toggling 'show' (bootstrap), we toggle 'hidden' (tailwind)
    // If it has 'hidden', it is closed. We remove 'hidden' to open.
    const isHidden = target.classList.contains("hidden");
    
    // Toggle hidden class
    if (isHidden) {
      target.classList.remove("hidden");
    } else {
      target.classList.add("hidden");
    }
    
    button.setAttribute("aria-expanded", String(isHidden)); // isHidden means we just opened it
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

  // Asset picker (partials/asset_picker.html, decisions 20261119-0740/0742/0800).
  // The hidden <select multiple> is the source of truth; the list and the
  // overlay are views on its options. Labels go in via textContent only.
  const bindAssetPickers = () => {
    document.querySelectorAll("[data-asset-picker]").forEach((picker) => {
      const select = picker.querySelector("select");
      const addButton = picker.querySelector("[data-asset-picker-add]");
      if (!select || !addButton) {
        return; // read-only picker: the server-rendered list is final
      }
      const list = picker.querySelector("[data-asset-picker-list]");
      const empty = picker.querySelector("[data-asset-picker-empty]");
      const modal = picker.querySelector("[data-asset-picker-modal]");
      const dialog = modal.querySelector("[data-asset-picker-dialog]");
      const search = modal.querySelector("[data-asset-picker-search]");
      const optionsBox = modal.querySelector("[data-asset-picker-options]");
      const noMatches = modal.querySelector("[data-asset-picker-no-matches]");
      const noneAvailable = modal.querySelector("[data-asset-picker-none-available]");
      const removeTemplate = picker.dataset.removeTemplate || "{label}";
      const options = () => Array.from(select.options);

      const renderList = () => {
        list.replaceChildren(
          ...options()
            .filter((option) => option.selected)
            .map((option) => {
              const row = document.createElement("li");
              row.className = "flex items-center justify-between gap-2 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-1.5 text-sm text-[var(--color-text)]";
              row.dataset.value = option.value;
              const text = document.createElement("span");
              text.textContent = option.text;
              const remove = document.createElement("button");
              remove.type = "button";
              remove.className = "inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-[var(--color-muted)] hover:bg-slate-500/10 hover:text-[var(--color-text)]";
              remove.dataset.assetPickerRemove = "";
              remove.setAttribute("aria-label", removeTemplate.replace("{label}", option.text));
              remove.innerHTML = '<i class="fas fa-times" aria-hidden="true"></i>';
              row.append(text, remove);
              return row;
            })
        );
        empty.classList.toggle("hidden", list.children.length > 0);
      };

      // Remove: deselect, re-render, then move focus to the next row's ×,
      // else the previous row's ×, else the add button (CHK016).
      list.addEventListener("click", (event) => {
        const remove = event.target.closest("[data-asset-picker-remove]");
        if (!remove) {
          return;
        }
        const row = remove.closest("li");
        const index = Array.from(list.children).indexOf(row);
        const option = options().find((opt) => opt.value === row.dataset.value);
        if (option) {
          option.selected = false;
        }
        renderList();
        const buttons = list.querySelectorAll("[data-asset-picker-remove]");
        (buttons[index] || buttons[index - 1] || addButton).focus();
      });

      const applySearch = () => {
        const query = search.value.trim().toLowerCase();
        let visible = 0;
        optionsBox.querySelectorAll("label").forEach((row) => {
          const match = row.textContent.toLowerCase().includes(query);
          row.classList.toggle("hidden", !match);
          visible += match ? 1 : 0;
        });
        const available = optionsBox.children.length;
        noneAvailable.classList.toggle("hidden", available > 0);
        noMatches.classList.toggle("hidden", available === 0 || visible > 0);
      };

      // The picker opens/closes its own overlay with the same Tailwind classes
      // as the BIA modals; ui.js openModal only toggles an unstyled .show.
      const closeOverlay = () => {
        dialog.classList.add("opacity-0", "scale-95");
        dialog.classList.remove("opacity-100", "scale-100");
        modal.classList.add("opacity-0", "invisible");
        modal.setAttribute("aria-hidden", "true");
        addButton.focus(); // CHK015
      };

      addButton.addEventListener("click", () => {
        optionsBox.replaceChildren(
          ...options()
            .filter((option) => !option.selected)
            .map((option) => {
              const row = document.createElement("label");
              row.className = "flex items-center gap-2 rounded-md px-2 py-1.5 text-sm text-[var(--color-text)] hover:bg-slate-500/10 cursor-pointer";
              const box = document.createElement("input");
              box.type = "checkbox";
              box.value = option.value;
              const text = document.createElement("span");
              text.textContent = option.text;
              row.append(box, text);
              return row;
            })
        );
        search.value = "";
        applySearch();
        modal.classList.remove("opacity-0", "invisible");
        modal.removeAttribute("aria-hidden");
        void modal.offsetWidth; // let the dialog transition run
        dialog.classList.remove("opacity-0", "scale-95");
        dialog.classList.add("opacity-100", "scale-100");
        // The wrapper only transitions opacity, so visibility flips at once
        // and the search can take focus immediately.
        search.focus(); // CHK015
      });

      modal.querySelectorAll("[data-asset-picker-close]").forEach((button) => {
        button.addEventListener("click", closeOverlay);
      });
      // On document, so Esc works wherever focus is while the overlay is open.
      document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && modal.getAttribute("aria-hidden") !== "true") {
          closeOverlay();
        }
      });

      search.addEventListener("input", applySearch);
      // The overlay sits inside the form: Enter must not submit it.
      search.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
          event.preventDefault();
        }
      });

      modal.querySelector("[data-asset-picker-confirm]").addEventListener("click", () => {
        const chosen = new Set(
          Array.from(optionsBox.querySelectorAll("input:checked")).map((box) => box.value)
        );
        options().forEach((option) => {
          if (chosen.has(option.value)) {
            option.selected = true;
          }
        });
        renderList();
        closeOverlay();
      });

      renderList(); // sync with restored form state (back/forward cache)
    });
  };

  // Block an upload whose selected files exceed the form's total limit, so the
  // user gets a translated message instead of the gateway's bare 413, and
  // disable the submit button once a valid upload starts (decision 20261120-0900).
  const bindUploadSizeLimits = () => {
    document.querySelectorAll("form[data-max-total-bytes]").forEach((form) => {
      const limit = Number(form.dataset.maxTotalBytes);
      const errorSlot = form.querySelector("[data-max-total-error]");
      const submitButtons = () => form.querySelectorAll('[type="submit"]');

      form.addEventListener("submit", (event) => {
        const total = Array.from(form.querySelectorAll('input[type="file"]'))
          .flatMap((input) => Array.from(input.files || []))
          .reduce((sum, file) => sum + file.size, 0);
        if (total > limit) {
          event.preventDefault();
          if (errorSlot) {
            errorSlot.textContent = form.dataset.maxTotalMessage || "";
            errorSlot.hidden = false;
          }
          return;
        }
        if (errorSlot) {
          errorSlot.hidden = true;
        }
        submitButtons().forEach((button) => {
          button.disabled = true;
        });
      });

      // Back/forward cache restores the page with the button still disabled.
      window.addEventListener("pageshow", () => {
        submitButtons().forEach((button) => {
          button.disabled = false;
        });
      });
    });
  };

  document.addEventListener("DOMContentLoaded", () => {
    // Ensure scroll lock is cleared on page load
    document.documentElement.style.overflow = "";
    document.body.style.overflow = "";
    bindAssetPickers();
    bindUploadSizeLimits();
    bindCollapseToggles();
    bindModalTriggers();
  });

  window.tailwindUI = Object.assign(window.tailwindUI || {}, {
    openModal,
    closeModal,
    toggleCollapse,
  });
})();
