import { brand, button } from "../components.js";
import { state } from "../data.js";

export function authView() {
  const isSignUp = state.authMode === "signup";
  const heading = isSignUp ? "Create your secure account" : "Welcome back";
  const description = isSignUp
    ? "Register with the email address linked to your property invitation."
    : "Sign in to view your allocated property records and approved survey information.";
  const submitLabel = isSignUp ? "Create account" : "Sign in";
  const nameField = isSignUp
    ? `<div class="field">
        <label for="auth-name">Full name</label>
        <input id="auth-name" autocomplete="name" placeholder="e.g. Chiamaka Okoro">
      </div>`
    : "";
  const accountHelp = isSignUp
    ? `<p class="auth-consent">
        By creating an account, you confirm that you are authorized to access the linked property record.
      </p>`
    : `<button class="text-action" data-action="toast:Password recovery requires a connected identity service.">
        Forgot password?
      </button>`;
  const alternateAction = isSignUp ? "signin" : "signup";
  const alternateLabel = isSignUp ? "Sign in" : "Create an account";

  return /* HTML */ `<main class="auth-page">
    <section class="auth-card">
      <aside class="auth-intro">
        <a class="brand" href="#home">${brand()}</a>
        <div>
          <p class="eyebrow">Secure property access</p>
          <h1>Your land records, in one trusted place.</h1>
          <p>
            Access allocation details, approved survey information and boundary
            records connected to your account.
          </p>
        </div>
        <div class="auth-security">
          <p>
            <strong>Controlled access</strong>Only authorized allottees can view
            linked property records.
          </p>
        </div>
      </aside>
      <section class="auth-form-wrap">
        <button
          class="auth-back"
          data-action="public"
          aria-label="Return to the public site"
        >
          ← Back to site
        </button>
        <div class="auth-form-head">
          <p class="eyebrow">${isSignUp ? "New here?" : "Account access"}</p>
          <h2>${heading}</h2>
          <p>${description}</p>
        </div>
        <div class="auth-tabs" role="tablist" aria-label="Account options">
          <button
            class="${!isSignUp ? "active" : ""}"
            data-action="auth-mode:signin"
            role="tab"
            aria-selected="${!isSignUp}"
          >
            Sign in
          </button>
          <button
            class="${isSignUp ? "active" : ""}"
            data-action="auth-mode:signup"
            role="tab"
            aria-selected="${isSignUp}"
          >
            Create account
          </button>
        </div>
        <div class="auth-fields">
          ${nameField}
          <div class="field">
            <label for="auth-email">Email address</label>
            <input
              id="auth-email"
              type="email"
              autocomplete="email"
              placeholder="name@example.com"
            />
          </div>
          <div class="field">
            <label for="auth-password">Password</label>
            <input
              id="auth-password"
              type="password"
              autocomplete="${isSignUp ? "new-password" : "current-password"}"
              placeholder="Enter your password"
            />
          </div>
          ${accountHelp}
        </div>
        ${button(submitLabel, "authenticate", "primary", "auth-submit")}
        <p class="auth-switch">
          ${isSignUp ? "Already have an account?" : "New to TerraLedger?"}
          <button
            class="text-action"
            data-action="auth-mode:${alternateAction}"
          >
            ${alternateLabel}
          </button>
        </p>
      </section>
    </section>
  </main>`;
}
