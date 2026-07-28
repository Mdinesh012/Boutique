// main.js
// Small vanilla-JS enhancements shared across pages.

document.addEventListener('DOMContentLoaded', function () {
  // Auto-dismiss flash alerts after 4 seconds
  document.querySelectorAll('.alert').forEach(function (alertEl) {
    setTimeout(function () {
      const bsAlert = bootstrap && bootstrap.Alert ? bootstrap.Alert.getOrCreateInstance(alertEl) : null;
      if (bsAlert) bsAlert.close();
    }, 4000);
  });

  // ---------- Mobile hamburger sidebar toggle ----------
  const sidebar = document.getElementById('appSidebar');
  const toggleBtn = document.getElementById('sidebarToggle');
  const overlay = document.getElementById('sidebarOverlay');
  const sidebarNav = document.getElementById('sidebarNav');

  function openSidebar() {
    if (!sidebar || !overlay) return;
    sidebar.classList.add('sidebar-open');
    overlay.classList.add('active');
  }

  function closeSidebar() {
    if (!sidebar || !overlay) return;
    sidebar.classList.remove('sidebar-open');
    overlay.classList.remove('active');
  }

  if (toggleBtn) {
    toggleBtn.addEventListener('click', function (e) {
      e.stopPropagation();
      if (sidebar.classList.contains('sidebar-open')) {
        closeSidebar();
      } else {
        openSidebar();
      }
    });
  }

  // Tap outside the sidebar (on the overlay) closes it
  if (overlay) {
    overlay.addEventListener('click', closeSidebar);
  }

  // Selecting a menu item closes the sidebar (before navigation happens)
  if (sidebarNav) {
    sidebarNav.querySelectorAll('a').forEach(function (link) {
      link.addEventListener('click', closeSidebar);
    });
  }

  // If the window is resized/rotated up to desktop width, make sure the
  // mobile "open" state doesn't linger and block anything.
  window.addEventListener('resize', function () {
    if (window.innerWidth >= 768) {
      closeSidebar();
    }
  });
});
