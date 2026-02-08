document.addEventListener("DOMContentLoaded", function () {
  console.log("Password toggle script loaded");

  function setupToggle(passwordId, toggleId) {
    const passwordField = document.getElementById(passwordId);
    const toggleIcon = document.getElementById(toggleId);

    if (!passwordField || !toggleIcon) {
      console.log(
        `Elements not found: password=${passwordId}, toggle=${toggleId}`
      );
      return;
    }

    console.log(`Password toggle initialized: ${passwordId} with ${toggleId}`);

    passwordField.type = "password";
    toggleIcon.className = "fa fa-eye-slash password-toggle";

    toggleIcon.onclick = function (e) {
      if (e) e.preventDefault();

      console.log(
        "Toggle clicked, current password field type:",
        passwordField.type
      );
      console.log("Toggle current class:", this.className);

      if (passwordField.type === "password") {
        passwordField.type = "text";
        this.className = "fa fa-eye password-toggle";
        console.log("Changed to: fa-eye, new class:", this.className);
      } else {
        passwordField.type = "password";
        this.className = "fa fa-eye-slash password-toggle";
        console.log("Changed to: fa-eye-slash, new class:", this.className);
      }

      console.log(`Toggled ${passwordId} to ${passwordField.type}`);
      return false;
    };
  }

  setTimeout(function () {
    setupToggle("password", "password_toggle_public");

    setupToggle("password", "password_toggle_signup");
    setupToggle("confirm_password", "password_toggle_confirm");
    setupToggle("password", "password_toggle_reset");
    setupToggle("confirm_password", "password_toggle_reset_confirm");

    console.log("All password toggles initialized");
  }, 300);
});

if (typeof jQuery !== "undefined") {
  jQuery(document).ready(function () {
    console.log("jQuery document ready - initializing toggles");

    jQuery("#password_toggle_public").on("click", function (e) {
      e.preventDefault();
      var pwField = jQuery("#password");
      if (pwField.attr("type") === "password") {
        pwField.attr("type", "text");
        jQuery(this).attr("class", "fa fa-eye password-toggle");
      } else {
        pwField.attr("type", "password");
        jQuery(this).attr("class", "fa fa-eye-slash password-toggle");
      }
      return false;
    });

    jQuery("#password_toggle_signup, #password_toggle_reset").on(
      "click",
      function (e) {
        e.preventDefault();
        var pwField = jQuery("#password");
        if (pwField.attr("type") === "password") {
          pwField.attr("type", "text");
          jQuery(this).attr("class", "fa fa-eye password-toggle");
        } else {
          pwField.attr("type", "password");
          jQuery(this).attr("class", "fa fa-eye-slash password-toggle");
        }
        return false;
      }
    );

    jQuery("#password_toggle_confirm, #password_toggle_reset_confirm").on(
      "click",
      function (e) {
        e.preventDefault();
        var pwField = jQuery("#confirm_password");
        if (pwField.attr("type") === "password") {
          pwField.attr("type", "text");
          jQuery(this).attr("class", "fa fa-eye password-toggle");
        } else {
          pwField.attr("type", "password");
          jQuery(this).attr("class", "fa fa-eye-slash password-toggle");
        }
        return false;
      }
    );
  });
}
