"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const { test } = require("node:test");

const root = path.join(__dirname, "../..");
const file = path.join(root, "widgets/messanger/PhonePersonalDraftState.js");
const ctx = vm.createContext({});
vm.runInContext(fs.readFileSync(file, "utf8"), ctx, { filename: file });
const norm = (x) => JSON.parse(JSON.stringify(x));
const ID_A = "phone-row-a";
const ID_B = "phone-row-b";

test("draft begins empty and never implies a saved favorite", () => {
  const initial = norm(ctx.start(ID_A));
  assert.deepEqual(initial, {
    contactId: ID_A, favorite: null, note: null, changed: false
  });
  assert.equal(ctx.summary(initial, ID_A), "NO CHANGE PROPOSED");
});

test("favorite ON/OFF, note clear, cancel are memory-only independent changes", () => {
  let state = ctx.start(ID_A);
  state = ctx.withFavorite(state, ID_A, true);
  assert.equal(state.favorite, true);
  assert.match(ctx.summary(state, ID_A), /NOT SAVED/);
  state = ctx.withFavorite(state, ID_A, false);
  assert.equal(state.favorite, false);
  state = ctx.withNote(state, ID_A, "TEST PRIVATE NOTE");
  assert.equal(state.note, "TEST PRIVATE NOTE");
  assert.equal(ctx.summary(state, ID_A).includes("TEST PRIVATE NOTE"), false);
  state = ctx.withNote(state, ID_A, "");
  assert.equal(state.note, "");
  state = ctx.empty();
  assert.equal(state.contactId, "");
  assert.equal(state.note, null);
  assert.equal(state.favorite, null);
});

test("cross-contact selection and invalid mutations discard instead of mixing", () => {
  let state = ctx.withNote(ctx.start(ID_A), ID_A, "secret");
  let newState = ctx.withFavorite(state, ID_B, true);
  assert.deepEqual(norm(newState), norm(ctx.empty()));
  newState = ctx.withNote(state, ID_B, "bad");
  assert.deepEqual(norm(newState), norm(ctx.empty()));
  for (const value of [123, null, false, "x".repeat(4097), "bad\u0000note"]) {
    assert.deepEqual(norm(ctx.withNote(state, ID_A, value)), norm(ctx.empty()));
  }
  assert.deepEqual(norm(ctx.withFavorite(state, ID_A, "true")), norm(ctx.empty()));
});

test("no persistent contact identity, storage, save method or private status", () => {
  const source = fs.readFileSync(file, "utf8");
  for (const banned of [
    "localStorage", "FileView", "XMLHttpRequest", "secret-tool",
    "fetch(", "writeFile", "indexedDB", "sessionStorage",
    "P35", "PhonePersonalContactVault", "console.log(", "print("
  ]) assert.equal(source.includes(banned), false, banned);
  assert.equal(ctx.save, undefined);
  assert.equal(ctx.commit, undefined);
});
