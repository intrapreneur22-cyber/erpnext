// IntraERP Branding - Login Page Customization
frappe.ready(function () {
    // Change "Login to Frappe" to "Login to IntraERP"
    setTimeout(function () {
        // Target the login page heading
        var loginHeading = document.querySelector('.page-card-head h4');
        if (loginHeading && loginHeading.textContent.includes('Frappe')) {
            loginHeading.textContent = loginHeading.textContent.replace('Frappe', 'IntraERP');
        }

        // Also check for any other instances
        document.querySelectorAll('h4, h3, h2').forEach(function (heading) {
            if (heading.textContent.includes('Login to Frappe')) {
                heading.textContent = heading.textContent.replace('Login to Frappe', 'Login to IntraERP');
            }
        });
    }, 100);
});

// Hide Help menu from navbar
$(document).ready(function () {
    setTimeout(function () {
        // Hide the Help dropdown menu
        $('.dropdown-help').closest('li.dropdown').hide();
        $('li.dropdown:has(.dropdown-help)').hide();

        // Alternative selectors for robustness
        $('a[data-label="Help"]').closest('li').hide();
        $('.navbar-nav li:has(a[href*="help"])').hide();
    }, 300);
});
