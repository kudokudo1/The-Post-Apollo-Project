#!/usr/bin/env node
// All records are fictional. No crawler, network, or local export file needed.
import assert from "node:assert/strict";
import {normalizePage, normalizeCrawl, readCrawl} from "../../scripts/finance/read_scrapy_crawl.mjs";

const sample = {
  schemaVersion: 1, source: "finance-demo-scrapy", readOnly: true,
  url: "https://quotes.toscrape.com/",
  title: "Demo Page 1",
  observedAt: "2026-10-24T20:25:00+00:00",
  snippets: ["An imaginary extracted quotation."],
  links: [
    "https://quotes.toscrape.com/page/2/",
    "https://quotes.toscrape.com/page/2/", // duplicate
    "https://evil.example/steal",           // excluded
    "javascript:alert(1)"                    // excluded
  ]
};
const page = normalizePage(sample);
assert.equal(page.title,"Demo Page 1");
assert.equal(page.links.length,1);
assert.equal(page.snippet,"An imaginary extracted quotation.");
assert.equal(normalizePage({...sample, readOnly:false}),null);
assert.equal(normalizePage({...sample, source:"arbitrary"}),null);
assert.equal(normalizePage({...sample, url:"http://127.0.0.1:5000/"}),null);
assert.equal(normalizePage({...sample, url:"https://evil.example/"}),null);
assert.equal(normalizePage({...sample, links:Array(33).fill(sample.url)}),null);
assert.equal(normalizePage({...sample, observedAt:"not a date"}),null);
const normalized = normalizeCrawl([sample,{...sample,url:"https://quotes.toscrape.com/page/2/"}]);
assert.equal(normalized.pageCount,2);
assert.equal(normalized.linkCount,2);
assert.equal(normalized.status,"snapshot");
assert.equal(normalized.readOnly,true);
assert.equal(normalizeCrawl([]).status,"empty");
assert.throws(()=>normalizeCrawl([{...sample}, {...sample}]),/duplicate-page/);
assert.throws(()=>normalizeCrawl({pages:[sample]}),/invalid-export/);
assert.throws(()=>normalizeCrawl(Array(7).fill(sample)),/invalid-export/);
await assert.rejects(readCrawl("/__post_apollo_nonexistent__/missing.json"),/missing-export/);
console.log("FinanceW Research Scrapy bridge fake fixture tests: PASS");
