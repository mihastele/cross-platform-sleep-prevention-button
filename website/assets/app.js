/* Stay Awake site: hero demo switch (mirrors the real widget states) + footer year. */
(function () {
  "use strict";

  var year = document.getElementById("year");
  if (year) year.textContent = String(new Date().getFullYear());

  var toggle = document.getElementById("demo-switch");
  var status = document.getElementById("demo-status");
  var detail = document.getElementById("demo-detail");
  if (!toggle || !status || !detail) return;

  var TEXT = {
    on: {
      status: "Keeping you awake",
      detail: "Your computer stays awake. The screen can still dim or lock."
    },
    off: {
      status: "Sleep is allowed",
      detail: "Your system's normal idle sleep settings apply."
    }
  };

  toggle.addEventListener("click", function () {
    var on = toggle.getAttribute("aria-checked") !== "true";
    toggle.setAttribute("aria-checked", on ? "true" : "false");
    status.textContent = on ? TEXT.on.status : TEXT.off.status;
    status.classList.toggle("on", on);
    detail.textContent = on ? TEXT.on.detail : TEXT.off.detail;
  });
})();
