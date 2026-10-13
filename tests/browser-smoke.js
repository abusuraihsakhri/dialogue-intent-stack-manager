"use strict";
// Dependency-free DOM smoke test: exercises the inline browser handlers.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

class Element {
  constructor(id = "") {
    this.id = id;
    this.value = "";
    this.textContent = "";
    this.className = "";
    this.hidden = false;
    this.disabled = false;
    this.checked = false;
    this.children = [];
    this.handlers = {};
  }
  addEventListener(type, callback) { this.handlers[type] = callback; }
  replaceChildren() { this.children = []; }
  append(...children) { this.children.push(...children); }
  focus() {}
  click() { if (this.handlers.click) return this.handlers.click(); }
  async fire(type, event = {}) {
    const e = { preventDefault() {}, target: this, ...event };
    return this.handlers[type](e);
  }
}
const els = new Map();
const document = {
  getElementById(id) {
    if (!els.has(id)) els.set(id, new Element(id));
    return els.get(id);
  },
  createElement() { return new Element(); },
};
const $ = document.getElementById.bind(document);
const html = fs.readFileSync("web/index.html", "utf8");
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)];
assert.equal(scripts.length, 1);
const sandbox = {
  document,
  crypto: { randomUUID: (() => { let n = 0; return () => "id-" + (++n); })() },
  confirm: () => true,
  Blob: class {},
  URL: { createObjectURL: () => "blob:mock", revokeObjectURL() {} },
  setTimeout() {},
  fetch: async () => { throw Error("No server"); },
};
vm.runInNewContext(scripts[0][1], sandbox, { filename: "web/index.html" });

async function run() {
  assert.equal($("depth").textContent, "0");
  $("intent-name").value = "Primary goal";
  $("intent-notes").value = "Resume section two";
  await $("intent-form").fire("submit");
  assert.equal($("depth").textContent, "1");
  $("intent-name").value = "Side task";
  await $("intent-form").fire("submit");
  assert.equal($("depth").textContent, "2");
  assert.equal($("stack-list").children[0].children[0].textContent, "suspended");
  assert.equal($("stack-list").children[1].children[0].textContent, "active");
  await $("resume").fire("click");
  assert.equal($("depth").textContent, "1");
  assert.equal($("active").textContent, "Primary goal");
  assert.equal($("stack-list").children[0].children[2].textContent, "Resume section two");
  $("task_id").value = "TASK-1";
  $("target_identifier").value = "KEY-1";
  $("primary_metric").value = "5";
  $("secondary_metric").value = "2";
  $("status_descriptor").value = "NOMINAL";
  $("audit-mode").value = "browser";
  await $("audit-form").fire("submit");
  const preview = JSON.parse($("audit-output").textContent);
  assert.equal(preview.overall_urgency, "ROUTINE");
  assert.equal(preview.mode, "LOCAL_UNSIGNED_PREVIEW");
  assert.ok(!Object.hasOwn(preview, "audit_hash"));
  $("is_critical").checked = true;
  await $("audit-form").fire("submit");
  const critical = JSON.parse($("audit-output").textContent);
  assert.equal(critical.overall_urgency, "CRITICAL_STAT_PANIC");
  $("audit-mode").value = "server";
  await $("audit-form").fire("submit");
  assert.match($("audit-message").textContent, /No simulated result was substituted/);
  await $("clear").fire("click");
  assert.equal($("depth").textContent, "0");
  console.log("Browser DOM smoke tests passed.");
}
run().catch(error => { console.error(error); process.exitCode = 1; });
