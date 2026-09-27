import { PublicClientApplication } from "@azure/msal-browser";

const clientId = import.meta.env.VITE_MICROSOFT_CLIENT_ID;
const scopes = ["Files.ReadWrite"];
const app = clientId ? new PublicClientApplication({
  auth: {
    clientId,
    authority: "https://login.microsoftonline.com/organizations",
    redirectUri: window.location.origin,
  },
  cache: { cacheLocation: "sessionStorage" },
}) : null;

let readyPromise;

async function ready() {
  if (!app) return null;
  readyPromise ||= (async () => {
    await app.initialize();
    const response = await app.handleRedirectPromise();
    if (response?.account) app.setActiveAccount(response.account);
  })();
  await readyPromise;
  const account = app.getActiveAccount() || app.getAllAccounts()[0] || null;
  if (account && !app.getActiveAccount()) app.setActiveAccount(account);
  return account;
}

export function microsoftAuthConfigured() {
  return Boolean(app);
}

export async function currentMicrosoftAccount() {
  return ready();
}

export async function signInMicrosoft() {
  await ready();
  return app?.loginRedirect({ scopes });
}

export async function microsoftAccessToken() {
  const account = await ready();
  if (!account) return null;
  try {
    return (await app.acquireTokenSilent({ scopes, account })).accessToken;
  } catch {
    await app.acquireTokenRedirect({ scopes, account });
    return null;
  }
}

export async function signOutMicrosoft() {
  const account = await ready();
  return app?.logoutRedirect({ account, postLogoutRedirectUri: window.location.origin });
}
