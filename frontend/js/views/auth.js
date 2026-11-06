import { brand, uiIcon } from "../components.js?v=20261026";
import { currentEndpoint, state } from "../data.js?v=20261106";

const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (character) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
})[character]);

function emailField(value = "", locked = false) {
  return `<div class="field"><label for="auth-email">Email address</label><input id="auth-email" name="email" type="email" autocomplete="email" placeholder="name@example.com" value="${escapeHtml(value)}" ${locked ? "readonly" : ""} required /></div>`;
}

function passwordResetView() {
  return `<main class="auth-page"><section class="auth-card">
    <aside class="auth-intro"><a class="brand" href="#home">${brand()}</a><div><p class="eyebrow">Account recovery</p><h1>Reset your password securely.</h1><p>Enter your account email address and we will send a secure password reset link if the account exists.</p></div><div class="auth-security"><span>${uiIcon("shield")}</span><p><strong>Privacy first</strong>Recovery links are issued only to the email address on your account.</p></div></aside>
    <section class="auth-form-wrap"><button class="auth-back" data-action="auth-mode:signin" aria-label="Return to sign in">← Back to sign in</button><div class="auth-form-head"><p class="eyebrow">Password recovery</p><h2>Forgot your password?</h2><p>We will send a link to create a new password.</p></div>
      <form id="password-reset-form" class="auth-form"><div class="auth-fields">${emailField()}</div><p class="auth-error" id="auth-error" role="alert" hidden></p>${state.passwordResetNotice ? `<p class="auth-success" role="status">${state.passwordResetNotice}</p>` : ""}<button class="button primary auth-submit" type="submit">Send reset link</button></form>
    </section>
  </section></main>`;
}

export function authView() {
  const isAdminPortal = currentEndpoint === "admin";
  const isCompanyAdminInvitation = Boolean(state.companyAdminInvitationToken);
  const isAllocationInvitation = Boolean(state.allocationInvitationToken);
  const hasInvitation = isCompanyAdminInvitation || isAllocationInvitation;
  if (state.authMode === "forgot") return passwordResetView();

  const isSignUp = state.authMode === "signup";
  const heading = hasInvitation ? (isSignUp ? "Create your TerraLedger account" : "Sign in to accept your invitation") : isAdminPortal ? "Administrator sign in" : isSignUp ? "Create your secure account" : "Welcome back";
  const description = hasInvitation ? `Use ${escapeHtml(isCompanyAdminInvitation ? state.companyAdminInvitation?.email : state.allocationInvitation?.email || "the invited email address")} for this invitation.` : isAdminPortal ? "Sign in with your authorized Platform Admin or Company Admin account to manage company records." : isSignUp ? "Create an account with your email address and password." : "Sign in to your TerraLedger account.";
  const submitLabel = hasInvitation ? (isSignUp ? "Create account and accept invitation" : "Sign in and accept invitation") : isAdminPortal ? "Sign in to workspace" : isSignUp ? "Create account" : "Sign in";
  const nameField = isSignUp ? `<div class="field"><label for="auth-name">Full name</label><input id="auth-name" name="full_name" autocomplete="name" placeholder="Enter your full name" required /></div>` : "";
  const accountHelp = isSignUp ? `<p class="auth-consent">${isAllocationInvitation ? "The invitation verifies the email address and links the allocation to this account." : "By creating an account, you confirm that you are authorized to access the linked record."}</p>` : `<button type="button" class="text-action" data-action="auth-mode:forgot">Forgot password?</button>`;
  const alternateAction = isSignUp ? "signin" : "signup";
  const alternateLabel = isSignUp ? "Sign in" : "Create an account";

  return `<main class="auth-page"><section class="auth-card">
    <aside class="auth-intro"><a class="brand" href="#home">${brand()}</a><div><p class="eyebrow">${isAdminPortal ? "Administrator access" : "Secure property access"}</p><h1>${isAdminPortal ? "Estate records, securely managed." : "Your land records, in one trusted place."}</h1><p>${isAdminPortal ? "Only authorized staff members can access and manage estate records." : "Access allocation details, approved survey information and boundary records connected to your account."}</p></div><div class="auth-security"><span>${uiIcon("shield")}</span><p><strong>Controlled access</strong>Only authorized users can view linked property records.</p></div></aside>
    <section class="auth-form-wrap"><button class="auth-back" data-action="public" aria-label="Return to the public site">← Back to site</button><div class="auth-form-head"><p class="eyebrow">${isSignUp ? "New here?" : "Account access"}</p><h2>${heading}</h2><p>${description}</p></div>
      ${isAdminPortal ? "" : `<div class="auth-tabs" role="tablist" aria-label="Account options"><button class="${!isSignUp ? "active" : ""}" data-action="auth-mode:signin" role="tab" aria-selected="${!isSignUp}">Sign in</button><button class="${isSignUp ? "active" : ""}" data-action="auth-mode:signup" role="tab" aria-selected="${isSignUp}">Create account</button></div>`}
      <form class="auth-form" id="auth-form"><div class="auth-fields">${nameField}${emailField(isCompanyAdminInvitation ? state.companyAdminInvitation?.email || "" : isAllocationInvitation ? state.allocationInvitation?.email || "" : "", hasInvitation)}<div class="field"><label for="auth-password">Password</label><input id="auth-password" name="password" type="password" autocomplete="${isSignUp ? "new-password" : "current-password"}" placeholder="Enter your password" minlength="8" required /></div>${accountHelp}</div><p class="auth-error" id="auth-error" role="alert" hidden></p><button class="button primary auth-submit" type="submit">${submitLabel}</button></form>
      ${isAdminPortal ? "" : `<p class="auth-switch">${isSignUp ? "Already have an account?" : "New to TerraLedger?"} <button class="text-action" data-action="auth-mode:${alternateAction}">${alternateLabel}</button></p>`}
  <p class="auth-note">${isAdminPortal ? "Administrative roles are assigned only through secure platform workflows." : "Only allocation records verified by the backend are displayed after sign-in."}</p>
    </section>
  </section></main>`;
}
