"use strict";

// Post-Apollo Proton // operator-click-only web Notification constructor pilot.
// Runs in the page MAIN world, never in extension's privileged world.
// WARNING: replacing a constructor is observable by the page. It is a
// temporary, pass-through instrumentation, NOT a provider identity proof.
// It sees attempts at "new Notification()" only while active; service-worker
// showNotification(), already-constructed objects and cached constructors
// are NOT observable by this pilot.
//
// The only return values are fixed enums, booleans and bounded counts. Do not
// read Notification arguments, tags, titles, URLs or mail/session data.
(() => {
  const KIND = "PROTON_EVENT_PILOT_V1";
  const KEY = "__postApolloProtonNotificationCountV1__";
  const WINDOW_MS = 90000;
  const MAX_COUNT = 20;
  const output = (stage, originOk, attempts = 0, capped = false) => ({
    kind: KIND,
    stage: stage,
    originOk: originOk,
    attempts: attempts,
    capped: capped,
    windowMs: WINDOW_MS,
    messageIdentityVerified: false,
    canMutate: false
  });

  if (location.origin !== "https://mail.proton.me")
    return output("wrong-origin", false);

  const prior = window[KEY];
  if (prior !== undefined) {
    // The page can inspect or interfere with MAIN world state. A collision
    // must never be interpreted as real or trusted event evidence.
    if (!prior || prior.owner !== KIND
        || typeof prior.finish !== "function"
        || !Number.isInteger(prior.attempts)
        || prior.attempts < 0 || prior.attempts > MAX_COUNT
        || typeof prior.capped !== "boolean"
        || typeof prior.active !== "boolean")
      return output("unavailable", true);

    if (prior.active)
      prior.finish("stopped");
    const result = output(prior.stage, true, prior.attempts, prior.capped);
    Reflect.deleteProperty(window, KEY);
    return result;
  }

  const original = window.Notification;
  if (typeof original !== "function" || typeof Proxy !== "function")
    return output("unavailable", true);
  const descriptor = Object.getOwnPropertyDescriptor(window, "Notification");
  if (descriptor && (descriptor.writable !== true || descriptor.configurable !== true))
    return output("unavailable", true);

  const state = {
    owner: KIND,
    attempts: 0,
    capped: false,
    active: true,
    stage: "started",
    timer: null,
    proxy: null,
    finish(stage) {
      if (!this.active)
        return;
      this.active = false;
      this.stage = stage;
      clearTimeout(this.timer);
      // Do not clobber a later change made by Proton or another extension.
      if (window.Notification === this.proxy) {
        if (descriptor) {
          window.Notification = original;
        } else {
          Reflect.deleteProperty(window, "Notification");
        }
      }
    }
  };

  try {
    state.proxy = new Proxy(original, {
      construct(target, args, newTarget) {
        if (state.active) {
          if (state.attempts < MAX_COUNT)
            state.attempts++;
          else
            state.capped = true;
        }
        // No arguments are inspected or modified. Keep ordinary behavior.
        return Reflect.construct(target, args, newTarget);
      }
    });
    window.Notification = state.proxy;
    if (window.Notification !== state.proxy)
      return output("unavailable", true);
    Object.defineProperty(window, KEY, {
      value: state, writable: false, enumerable: false, configurable: true
    });
    state.timer = setTimeout(() => state.finish("expired"), WINDOW_MS);
    return output("started", true);
  } catch (_) {
    // Best effort restore before failing closed.
    if (state.proxy && window.Notification === state.proxy) {
      if (descriptor) window.Notification = original;
      else Reflect.deleteProperty(window, "Notification");
    }
    Reflect.deleteProperty(window, KEY);
    return output("unavailable", true);
  }
})()
