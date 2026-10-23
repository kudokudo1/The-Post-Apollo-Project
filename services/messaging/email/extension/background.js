// Read-only Thunderbird MailExtension prototype.
// This add-on sends account metadata only. It does not read message content,
// modify mail, send messages or handle authentication credentials.
const HOST = "post_apollo_social_email";
function compactFolder(folder) {
  return {
    id: String(folder.id || ""),
    name: String(folder.name || ""),
    type: String(folder.type || "")
  };
}
async function publishAccounts() {
  const accounts = await messenger.accounts.list();
  const snapshot = accounts.map(account => ({
    id: String(account.id || ""),
    name: String(account.name || ""),
    type: String(account.type || ""),
    identities: (account.identities || []).map(identity => ({
      email: String(identity.email || "")
    })),
    // Only the folders already included in the account inventory.
    folders: (account.folders || []).map(compactFolder)
  }));
  try {
    const result = await messenger.runtime.sendNativeMessage(HOST, {
      type: "accounts.snapshot", accounts: snapshot
    });
    if (!result || !result.ok)
      console.warn("Post-Apollo email bridge rejected account snapshot");
  } catch (error) {
    console.warn("Post-Apollo email bridge unavailable:", String(error));
  }
}
publishAccounts();
messenger.accounts.onCreated.addListener(publishAccounts);
messenger.accounts.onDeleted.addListener(publishAccounts);
