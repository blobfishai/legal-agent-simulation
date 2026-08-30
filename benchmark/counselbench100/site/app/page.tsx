import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "CounselBench-100 — Long-horizon legal agent benchmark",
  description:
    "100 realistic legal matters, 9,700 provider-bound assets, and deterministic CounselScore verification across Clio, Gmail, Drive, and Slack.",
};

const HARBOR_URL =
  "https://hub.harborframework.com/datasets/blobfishai/counselbench-100";
const HF_URL =
  "https://huggingface.co/datasets/SamuelChien821/counselbench-100";

const practiceAreas = [
  ["Corporate and M&A", "10", "Signing, closing, consent, and diligence decisions"],
  ["Commercial contracts", "10", "Exit, renewal, pricing, breach, and transition positions"],
  ["Internal investigations", "10", "Attribution, reporting, remediation, and evidence holds"],
  ["Litigation and discovery", "10", "Preservation, production, privilege, and representation controls"],
  ["Restructuring", "10", "Claims, authority, estate impact, and deadline reconciliation"],
  ["Real estate", "10", "Title, access, covenants, water, leases, and insurance"],
  ["Privacy and regulatory", "10", "Transfers, incidents, assurances, controls, and response readiness"],
  ["Employment", "10", "Payroll, accommodation, training, agency, and workforce decisions"],
  ["IP and technology", "10", "Ownership, licensing, code, patent, domain, and release defects"],
  ["Public company", "10", "Disclosure, filing, committee, equity, cyber, and certification readiness"],
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
        <div className="eyebrow">Open benchmark · v3.2.4</div>
        <h1>
          Long-horizon legal work,
          <br /> measured end to end.
        </h1>
        <p className="hero-copy">
          CounselBench-100 tests whether agents can investigate dense matter
          files, reconcile conflicting evidence, and deliver grounded work
          product through provider-shaped Clio, Gmail, Drive, and Slack MCP
          operations in a closed sandbox.
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
          <div><dt>9,700</dt><dd>unique provider-bound assets</dd></div>
          <div><dt>69–97</dt><dd>causal MCP calls per oracle</dd></div>
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
          <h2>One matter. Ninety-seven records. No exposed task recipe.</h2>
          <p>
            Each task is a complete synthetic matter workspace spanning twelve
            evidence areas and nine native formats. The employee asks for a
            decision; the agent must discover the relevant systems, controlling
            revisions, viable options, and safe state changes.
          </p>
        </div>

        <div className="sequence" aria-label="Accepted action sequence">
          {[
            ["04", "Discover", "Find the exact matter across provider systems"],
            ["58–86", "Investigate", "Correlate material records before acting"],
            ["03", "Decide", "Compare documented paths and preserve evidence holds"],
            ["03", "Commit", "Update the matter, note, and working team channel"],
            ["03", "Verify", "Read the committed provider state back"],
            ["14", "Score", "Grade task-specific semantic milestones"],
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
              workbooks, approvals, Slack threads, and matter notes carry linked
              facts, controlled contradictions, and realistic drafting noise.
            </p>
            <div className="format-list">
              <span>.md</span><span>.txt</span><span>.eml</span><span>.csv</span>
              <span>.json</span><span>.xml</span><span>.html</span><span>.pdf</span><span>.xlsx</span>
            </div>
          </article>
          <article className="feature feature-mint">
            <span className="feature-label">Verification</span>
            <h3>Semantic, deterministic, inspectable</h3>
            <p>
              CounselScore measures investigation, option analysis, exact native
              provider state, collaboration, readback, and containment through
              fourteen task-specific milestones. Strict pass remains 100/100.
            </p>
            <div className="binary-mark"><span>0–100</span><span>and</span><span>strict pass</span></div>
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
            isolated task twice; fourteen adversarial strategies fail every one.
          </p>
        </div>
        <div className="proof-stats">
          <div><strong>1,600</strong><span>local qualification executions</span></div>
          <div><strong>100/100</strong><span>oracle passes</span></div>
          <div><strong>100/100</strong><span>exact deterministic replays</span></div>
          <div><strong>1,400/1,400</strong><span>negative controls rejected</span></div>
        </div>
        <div className="control-grid">
          <article><span>No-op or copied-gold shortcut</span><strong>0/200 accepted</strong></article>
          <article><span>Missing state or incomplete or late investigation</span><strong>0/300 accepted</strong></article>
          <article><span>Wrong value, decision, branch, or evidence</span><strong>0/400 accepted</strong></article>
          <article><span>Premature, missing-readback, duplicate, or rejected provider mutation</span><strong>0/400 accepted</strong></article>
          <article><span>Serialization keyword stuffing without distinct business rows</span><strong>0/100 accepted</strong></article>
        </div>
      </section>

      <section className="section model-results">
        <div className="section-heading">
          <div><span className="section-number">04</span><span className="kicker">Model leaderboard</span></div>
          <h2>The v3.2 row opens only after a full, bound run.</h2>
          <p>
            Partial runs and scores from earlier task bytes are not ranked. The
            first model row must cover all 100 released matters, bind every
            Harbor lock and task digest to v3.2, and publish inspectable redacted
            trajectories with zero infrastructure exceptions.
          </p>
        </div>
        <div className="result-summary">
          <div className="result-score"><strong>—</strong><span>exact-release score</span></div>
          <div><strong>100</strong><span>required task trials</span></div>
          <div><strong>100</strong><span>required task-digest bindings</span></div>
          <div><strong>0</strong><span>allowed infrastructure exceptions</span></div>
        </div>
        <p className="result-note">
          Oracle and adversarial controls establish solvability and verifier
          discrimination; they are never presented as model leaderboard rows.
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
          <article><h3>Is the MCP interface provider-shaped?</h3><p>Yes. Every allowlisted operation maps to a documented Clio Manage v4, Gmail v1, Drive v3, or Slack Web API method and strict task-relevant schema. The state and data are synthetic and closed.</p></article>
          <article><h3>Why require dozens of calls?</h3><p>The answer depends on identity, effective authority, current operations, approvals, capacity, and counterrecords distributed across systems. The count emerges from the work; exact call order is not graded.</p></article>
        </div>
      </section>

      <footer>
        <a className="wordmark" href="#top"><span className="wordmark-mark">CB</span><span>CounselBench-100</span></a>
        <p>An open long-horizon benchmark for legal agents.</p>
        <a href={HARBOR_URL}>v3.2.4 <Arrow /></a>
      </footer>
    </main>
  );
}
