import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "CounselBench-100 — Long-horizon legal agent benchmark",
  description:
    "100 realistic legal matters, 9,600 seeded documents, and deterministic verification across 109-step MCP workflows.",
};

const HARBOR_URL =
  "https://hub.harborframework.com/datasets/blobfishai/counselbench-100";
const HF_URL =
  "https://huggingface.co/datasets/SamuelChien821/counselbench-100";

const practiceAreas = [
  ["Commercial contracts", "10", "Renewals, breaches, pricing, and assignment"],
  ["Employment", "10", "Leave, accommodations, discipline, and separation"],
  ["Data privacy", "10", "Incidents, requests, transfers, and retention"],
  ["Corporate governance", "10", "Boards, consents, conflicts, and equity"],
  ["Real estate", "10", "Leases, notices, diligence, and operating costs"],
  ["Intellectual property", "10", "Licensing, ownership, misuse, and releases"],
  ["Regulatory compliance", "10", "Reporting, controls, notices, and audits"],
  ["Disputes", "10", "Claims, preservation, settlement, and procedure"],
  ["Procurement", "10", "RFPs, vendors, service levels, and remedies"],
  ["Legal operations", "10", "Intake, billing, outside counsel, and records"],
];

const modelRuns = [
  ["Commercial contracts", "117", "Fail"],
  ["Employment", "115", "Fail"],
  ["Data privacy", "112", "Fail"],
  ["Corporate governance", "111", "Fail"],
  ["Real estate", "110", "Fail"],
  ["Intellectual property", "110", "Fail"],
  ["Regulatory compliance", "110", "Fail"],
  ["Disputes", "109", "Fail"],
  ["Procurement", "109", "Fail"],
  ["Legal operations", "109", "Fail"],
];

function Arrow() {
  return <span aria-hidden="true">↗</span>;
}

export default function Home() {
  return (
    <main>
      <header className="site-header">
        <a className="wordmark" href="#top" aria-label="CounselBench-100 home">
          <span className="wordmark-mark">CB</span>
          <span>CounselBench-100</span>
        </a>
        <nav aria-label="Primary navigation">
          <a href="#method">Method</a>
          <a href="#results">Results</a>
          <a href="#release">Release</a>
        </nav>
        <a className="header-link" href={HARBOR_URL}>
          Open in Harbor <Arrow />
        </a>
      </header>

      <section className="hero" id="top">
        <div className="eyebrow">Open benchmark · v1.0.0</div>
        <h1>
          Long-horizon legal work,
          <br /> measured end to end.
        </h1>
        <p className="hero-copy">
          CounselBench-100 tests whether agents can investigate dense matter
          files, reconcile conflicting evidence, and deliver grounded work
          product through a real Model Context Protocol filesystem.
        </p>
        <div className="hero-actions">
          <a className="button button-primary" href={HARBOR_URL}>
            Run the benchmark <Arrow />
          </a>
          <a className="button button-secondary" href={HF_URL}>
            View the dataset <Arrow />
          </a>
        </div>
        <dl className="hero-stats">
          <div><dt>100</dt><dd>distinct legal matters</dd></div>
          <div><dt>9,600</dt><dd>seeded matter documents</dd></div>
          <div><dt>109</dt><dd>minimum verified MCP calls</dd></div>
        </dl>
      </section>

      <section className="statement">
        <p>
          A benchmark for the part of agent work that shortcuts cannot solve:
          opening every relevant file, preserving provenance, and getting every
          material fact right.
        </p>
      </section>

      <section className="section" id="method">
        <div className="section-heading">
          <div><span className="section-number">01</span><span className="kicker">The method</span></div>
          <h2>One matter. Ninety-six documents. No hidden shortcut.</h2>
          <p>
            Each task is a complete synthetic matter workspace spanning twelve
            folders and seven text-native formats. The accepted path exercises
            the same filesystem MCP contract used by production agents.
          </p>
        </div>

        <div className="sequence" aria-label="Accepted action sequence">
          {[
            ["01", "Scope", "List allowed directories"],
            ["01", "Map", "Build the directory tree"],
            ["01", "Locate", "Search across the matter"],
            ["96", "Read", "Open every source document"],
            ["08", "Inspect", "Verify critical file metadata"],
            ["02", "Deliver", "Write findings and legal memo"],
          ].map(([count, label, detail], index) => (
            <article className="sequence-card" key={label}>
              <span className="sequence-index">{String(index + 1).padStart(2, "0")}</span>
              <strong>{count}</strong>
              <h3>{label}</h3>
              <p>{detail}</p>
            </article>
          ))}
        </div>

        <div className="method-grid">
          <article className="feature feature-dark">
            <span className="feature-label">Seed depth</span>
            <h3>Evidence that behaves like a matter file</h3>
            <p>
              Agreements, correspondence, chronologies, policies, invoices,
              logs, minutes, and research notes carry linked facts, controlled
              contradictions, and realistic drafting noise.
            </p>
            <div className="format-list">
              <span>.md</span><span>.txt</span><span>.csv</span><span>.json</span>
              <span>.xml</span><span>.yaml</span><span>.html</span>
            </div>
          </article>
          <article className="feature feature-mint">
            <span className="feature-label">Verification</span>
            <h3>Binary, deterministic, inspectable</h3>
            <p>
              The verifier checks the trace, required reads, exact structured
              findings, grounded memo anchors, output filenames, and MCP write
              provenance. It uses no model, network, clock, or randomness.
            </p>
            <div className="binary-mark"><span>PASS</span><span>or</span><span>FAIL</span></div>
          </article>
        </div>
      </section>

      <section className="section practices">
        <div className="section-heading compact">
          <div><span className="section-number">02</span><span className="kicker">The matters</span></div>
          <h2>Ten practice areas. One hundred original fact patterns.</h2>
        </div>
        <div className="practice-list">
          {practiceAreas.map(([name, count, description], index) => (
            <article key={name}>
              <span>{String(index + 1).padStart(2, "0")}</span>
              <h3>{name}</h3>
              <p>{description}</p>
              <strong>{count}</strong>
            </article>
          ))}
        </div>
      </section>

      <section className="proof-band" id="results">
        <div className="section-heading inverse">
          <div><span className="section-number">03</span><span className="kicker">Execution proof</span></div>
          <h2>Built to fail agents for real reasons.</h2>
          <p>
            Every task was executed, not merely linted. The oracle passes every
            Dockerized Harbor task; four adversarial strategies fail every one.
          </p>
        </div>
        <div className="proof-stats">
          <div><strong>600</strong><span>local executions</span></div>
          <div><strong>100/100</strong><span>Harbor oracle passes</span></div>
          <div><strong>0</strong><span>infra exceptions</span></div>
          <div><strong>4×100</strong><span>negative controls rejected</span></div>
        </div>
        <div className="control-grid">
          <article><span>Shortcut answer</span><strong>0/100 accepted</strong></article>
          <article><span>Incomplete reading</span><strong>0/100 accepted</strong></article>
          <article><span>One wrong fact</span><strong>0/100 accepted</strong></article>
          <article><span>Bounded reviewer</span><strong>0/100 accepted</strong></article>
        </div>
      </section>

      <section className="section model-results">
        <div className="section-heading">
          <div><span className="section-number">04</span><span className="kicker">Real model baseline</span></div>
          <h2>It completed the workflow. It still missed the standard.</h2>
          <p>
            A stratified ten-task run with GPT-5.6-sol traversed every matter
            without infrastructure errors. All ten trials read all 96 files;
            each failed only the exact findings and grounded-memo checks.
          </p>
        </div>
        <div className="result-summary">
          <div className="result-score"><strong>0/10</strong><span>tasks passed</span></div>
          <div><strong>96/96</strong><span>documents read per task</span></div>
          <div><strong>109–117</strong><span>successful calls per task</span></div>
          <div><strong>$10.24</strong><span>total model cost</span></div>
        </div>
        <div className="results-table" role="table" aria-label="Model results by practice area">
          <div className="table-row table-head" role="row">
            <span role="columnheader">Practice area</span>
            <span role="columnheader">MCP calls</span>
            <span role="columnheader">Verdict</span>
          </div>
          {modelRuns.map(([area, calls, verdict]) => (
            <div className="table-row" role="row" key={area}>
              <span role="cell">{area}</span>
              <span role="cell">{calls}</span>
              <span role="cell" className="fail-pill">{verdict}</span>
            </div>
          ))}
        </div>
        <p className="result-note">
          Model baseline run on the v1.0.0 release. Failure is binary: a task
          passes only when both deliverables and the full action trace satisfy
          the verifier.
        </p>
      </section>

      <section className="release" id="release">
        <div>
          <span className="section-number">05</span><span className="kicker">Open release</span>
          <h2>Inspect the data.<br />Run the world.<br />Reproduce the result.</h2>
        </div>
        <div className="release-links">
          <a href={HARBOR_URL}><span><small>Runnable world</small>Harbor dataset</span><Arrow /></a>
          <a href={HF_URL}><span><small>Dataset and tests</small>Hugging Face</span><Arrow /></a>
          <a href="https://github.com/blobfishai/legal-agent-simulation"><span><small>Builder and verifier</small>Source repository</span><Arrow /></a>
        </div>
        <div className="release-meta">
          <span>Data: CC BY 4.0</span><span>Code: Apache 2.0</span>
          <span>100% synthetic</span><span>Released August 2026</span>
        </div>
      </section>

      <section className="section faq">
        <div className="section-heading compact">
          <div><span className="kicker">Questions</span></div><h2>Designed for scrutiny.</h2>
        </div>
        <div className="faq-grid">
          <article><h3>Are these real client files?</h3><p>No. Every entity, person, matter, and document is synthetic. The structure and density model professional legal work without exposing confidential information.</p></article>
          <article><h3>Can a grader drift?</h3><p>No. Expected findings and trace rules are task-bound and deterministic. The grader makes no semantic model call and has no network dependency.</p></article>
          <article><h3>Is the MCP interface real?</h3><p>Yes. The mock pins the official filesystem MCP tool names, input schemas, result envelope, protocol version, and observed behavior.</p></article>
          <article><h3>Why require 100+ calls?</h3><p>The information is distributed on purpose. A complete answer requires broad evidence collection, then precise synthesis—not one lucky retrieval.</p></article>
        </div>
      </section>

      <footer>
        <a className="wordmark" href="#top"><span className="wordmark-mark">CB</span><span>CounselBench-100</span></a>
        <p>An open long-horizon benchmark for legal agents.</p>
        <a href={HARBOR_URL}>v1.0.0 <Arrow /></a>
      </footer>
    </main>
  );
}
