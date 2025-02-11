// taken from https://github.com/hzrd149/nostrudel

import { nip19, verifyEvent } from "nostr-tools";
import createDefer, { Deferred } from "./classes/deffered";
import { getPubkeyFromDecodeResult, isHexKey } from "./helpers/nip19";
import { NostrEvent } from "./types/nostr-event";

export function createGetPublicKeyIntent() {
  return `intent:#Intent;scheme=nostrsigner;S.compressionType=none;S.returnType=signature;S.type=get_public_key;end`;
}
export function createSignEventIntent(draft) {
  return `intent:${encodeURIComponent(
    JSON.stringify(draft),
  )}#Intent;scheme=nostrsigner;S.compressionType=none;S.returnType=event;S.type=sign_event;end`;
}

let pendingRequest: Deferred<string> | null = null;

function rejectPending() {
  if (pendingRequest) {
    pendingRequest.reject("Canceled");
    pendingRequest = null;
  }
}

function onVisibilityChange() {
  if (document.visibilityState === "visible") {
    if (!pendingRequest || !navigator.clipboard) return;

    // read the result from the clipboard
    setTimeout(() => {
      navigator.clipboard
        .readText()
        .then((result) => pendingRequest?.resolve(result))
        .catch((e) => pendingRequest?.reject(e));
    }, 200);
  }
}
document.addEventListener("visibilitychange", onVisibilityChange);

async function intentRequest(intent: string) {
  rejectPending();
  const request = createDefer<string>();
  window.open(intent, "_blank");
  // NOTE: wait 500ms before setting the pending request since the visibilitychange event fires as soon as window.open is called
  setTimeout(() => {
    pendingRequest = request;
  }, 500);
  const result = await request;
  if (result.length === 0) throw new Error("Empty clipboard");
  return result;
}

async function getPublicKey() {
  const result = await intentRequest(createGetPublicKeyIntent());
  if (isHexKey(result)) return result;
  else if (result.startsWith("npub") || result.startsWith("nprofile")) {
    const decode = nip19.decode(result);
    const pubkey = getPubkeyFromDecodeResult(decode);
    if (!pubkey) throw new Error("Expected npub from clipboard");
    return pubkey;
  }
  throw new Error("Expected clipboard to have pubkey");
}

async function signEvent(draft): Promise<NostrEvent> {
  const signedEventJson = await intentRequest(createSignEventIntent(draft));
  const signedEvent = JSON.parse(signedEventJson) as NostrEvent;

  if (!verifyEvent(signedEvent)) throw new Error("Invalid signature");
  return signedEvent;
}

const amberSignerService = {
  supported: navigator.userAgent.includes("Android") && navigator.clipboard,
  getPublicKey,
  signEvent
};

export default amberSignerService;
