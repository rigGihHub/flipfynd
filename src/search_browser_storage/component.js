export default function({data,parentElement,setStateValue}) {
  const prefix = "flipfynd.search.v1.";
  const args = data || {};
  let reply = {token: "", blob: ""};
  try {
    if (args.clear) {
      for (const key of Object.keys(localStorage)) if (key.startsWith(prefix)) localStorage.removeItem(key);
      reply.cleared = true;
    } else {
      const token = /^[a-f0-9]{32}$/.test(args.token || "") ? args.token : localStorage.getItem(prefix + "latest");
      if (/^[a-f0-9]{32}$/.test(token || "")) {
        if (args.blob) {
          // Store this user's run only; bound device storage to three searches.
          const keys = JSON.parse(localStorage.getItem(prefix + "history") || "[]").filter(key => key !== token);
          keys.push(token);
          while (keys.length > 3) localStorage.removeItem(prefix + keys.shift());
          localStorage.setItem(prefix + token, args.blob);
          localStorage.setItem(prefix + "history", JSON.stringify(keys));
          localStorage.setItem(prefix + "latest", token);
        }
        reply = {token, blob: localStorage.getItem(prefix + token) || ""};
      }
    }
  } catch (error) { reply = {token: args.token || "", blob: "", error: "STORAGE_UNAVAILABLE"}; }
  const request = JSON.stringify([args.token || "", Boolean(args.clear)]);
  if (request !== parentElement.dataset.repliedFor) {
    parentElement.dataset.repliedFor = request;
    setStateValue("reply",reply);
  }

}
