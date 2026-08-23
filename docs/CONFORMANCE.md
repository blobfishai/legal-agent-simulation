# Tool conformance

Pinned specifications: **2026-08-12**.

> Endpoint mapping is not API exactness. A tool counts as exact only after its wire input, success response, pagination, and documented errors all validate. Derived helpers and simulator extensions are excluded from the vendor score.

## Current result

| Measure | Count |
| --- | ---: |
| Contract tools covered by the registry | 91 / 91 |
| Vendor-targeted tools | 91 |
| Vendor targets resolved to a pinned source | 85 / 91 |
| Deterministic success calls | 91 / 91 |
| Applicable request schemas passed | 53 / 53 |
| Agent-visible MCP input schemas match pinned specs | 53 / 53 |
| Applicable success-response schemas passed | 53 / 53 |
| Fully exact vendor tools | 47 / 91 |
| Passed best-public-contract verification | 85 / 85 |
| Derived helpers (excluded) | 0 |
| Simulator-extension gaps | 0 |
| Conformance-harness failures | 0 |

Exactness is fail-closed and per tool. Only direct wire-parameter tools whose success response, pagination (when applicable), and vendor error fixtures pass against pinned public specifications count as exact. Flattened adapters, derived helpers, simulator extensions, partner-gated operations, and documentation-only mirrors remain explicitly outside that count.

## Product coverage

| Product | Tools | Exact | Verification state |
| --- | ---: | ---: | --- |
| `clio-manage-v4` | 33 | 33 | exact-to-pinned-public-contract |
| `cmecf-nextgen` | 4 | 0 | documentation-fixture-conformant |
| `courtlistener-v4` | 13 | 0 | live-diff-conformant-to-pinned-source |
| `deadline-rules-frcp` | 1 | 0 | published-standard-conformant |
| `docusign-esign-v2.1` | 4 | 4 | exact-to-pinned-public-contract |
| `google-calendar-v3` | 2 | 2 | exact-to-pinned-public-contract |
| `google-drive-v3` | 3 | 3 | exact-to-pinned-public-contract |
| `google-gmail-v1` | 3 | 3 | exact-to-pinned-public-contract |
| `google-sheets-v4` | 2 | 2 | exact-to-pinned-public-contract |
| `imanage-work` | 12 | 0 | public-connector-conformant-fidelity-ceiling, unverifiable-partner-gated |
| `ledes-1998b` | 1 | 0 | published-standard-conformant |
| `relativity-rest` | 12 | 0 | documentation-fixture-conformant |
| `utbms` | 1 | 0 | published-standard-conformant |

## Tool rows

| Tool | Product | Mode | Status | Target |
| --- | --- | --- | --- | --- |
| `bill_line_items_list` | `clio-manage-v4` | `openapi` | `exact-to-pinned-public-contract` | get · /line_items.json |
| `bills_get` | `clio-manage-v4` | `openapi` | `exact-to-pinned-public-contract` | get · /bills/{id}.json |
| `bills_list` | `clio-manage-v4` | `openapi` | `exact-to-pinned-public-contract` | get · /bills.json |
| `bills_update` | `clio-manage-v4` | `openapi` | `exact-to-pinned-public-contract` | patch · /bills/{id}.json |
| `calendar_entries_create` | `clio-manage-v4` | `openapi` | `exact-to-pinned-public-contract` | post · /calendar_entries.json |
| `calendar_entries_list` | `clio-manage-v4` | `openapi` | `exact-to-pinned-public-contract` | get · /calendar_entries.json |
| `calendar_entries_update` | `clio-manage-v4` | `openapi` | `exact-to-pinned-public-contract` | patch · /calendar_entries/{id}.json |
| `calendar_events_insert` | `google-calendar-v3` | `google_discovery` | `exact-to-pinned-public-contract` | calendar.events.insert |
| `calendar_events_list` | `google-calendar-v3` | `google_discovery` | `exact-to-pinned-public-contract` | calendar.events.list |
| `citation_lookup` | `courtlistener-v4` | `live_diff` | `live-diff-conformant-to-pinned-source` | post · /api/rest/v4/citation-lookup/ |
| `communications_create` | `clio-manage-v4` | `openapi` | `exact-to-pinned-public-contract` | post · /communications.json |
| `communications_list` | `clio-manage-v4` | `openapi` | `exact-to-pinned-public-contract` | get · /communications.json |
| `contacts_create` | `clio-manage-v4` | `openapi` | `exact-to-pinned-public-contract` | post · /contacts.json |
| `contacts_get` | `clio-manage-v4` | `openapi` | `exact-to-pinned-public-contract` | get · /contacts/{id}.json |
| `contacts_list` | `clio-manage-v4` | `openapi` | `exact-to-pinned-public-contract` | get · /contacts.json |
| `contacts_search` | `clio-manage-v4` | `openapi` | `exact-to-pinned-public-contract` | get · /contacts.json |
| `contacts_update` | `clio-manage-v4` | `openapi` | `exact-to-pinned-public-contract` | patch · /contacts/{id}.json |
| `courts_list` | `courtlistener-v4` | `live_diff` | `live-diff-conformant-to-pinned-source` | get · /api/rest/v4/courts/ |
| `deadlines_compute` | `deadline-rules-frcp` | `published_standard` | `published-standard-conformant` | frcp-6-12-33-34 |
| `docket_alerts_create` | `courtlistener-v4` | `live_diff` | `live-diff-conformant-to-pinned-source` | post · /api/rest/v4/docket-alerts/ |
| `docket_alerts_list` | `courtlistener-v4` | `live_diff` | `live-diff-conformant-to-pinned-source` | get · /api/rest/v4/docket-alerts/ |
| `docket_entries_list` | `courtlistener-v4` | `live_diff` | `live-diff-conformant-to-pinned-source` | get · /api/rest/v4/docket-entries/ |
| `dockets_get` | `courtlistener-v4` | `live_diff` | `live-diff-conformant-to-pinned-source` | get · /api/rest/v4/dockets/{id}/ |
| `dockets_list` | `courtlistener-v4` | `live_diff` | `live-diff-conformant-to-pinned-source` | get · /api/rest/v4/dockets/ |
| `dockets_search` | `courtlistener-v4` | `live_diff` | `live-diff-conformant-to-pinned-source` | get · /api/rest/v4/search/ |
| `document_versions_list` | `imanage-work` | `partner_gated` | `unverifiable-partner-gated` | private Work API version listing; connector GetDocumentVersions matches the capability but conformant adoption requires connector-shaped wire schemas — a world-version remap candidate (verified 2026-08-22) |
| `documents_checkin` | `imanage-work` | `imanage_connector` | `public-connector-conformant-fidelity-ceiling` | UpdateOrCreateNewDocVersion |
| `documents_checkout` | `imanage-work` | `partner_gated` | `unverifiable-partner-gated` | private Work API checkout lifecycle; no public machine-readable spec (connector 4.0 has no checkout or unlock operation; verified 2026-08-22) |
| `documents_code` | `relativity-rest` | `documentation_fixture` | `documentation-fixture-conformant` | documents_code |
| `documents_create` | `imanage-work` | `imanage_connector` | `public-connector-conformant-fidelity-ceiling` | UploadDocument |
| `documents_download` | `imanage-work` | `imanage_connector` | `public-connector-conformant-fidelity-ceiling` | DownloadDocument |
| `documents_get` | `imanage-work` | `imanage_connector` | `public-connector-conformant-fidelity-ceiling` | GetDocumentProfile |
| `documents_list` | `imanage-work` | `partner_gated` | `unverifiable-partner-gated` | private Work API folder-document listing; no public machine-readable spec (connector 4.0 has no folder-contents operation; verified 2026-08-22) |
| `documents_query` | `relativity-rest` | `documentation_fixture` | `documentation-fixture-conformant` | documents_query |
| `documents_search` | `imanage-work` | `partner_gated` | `unverifiable-partner-gated` | private Work API document search; no public machine-readable spec (connector 4.0 has no document-search operation; Universal API docs registration-gated; verified 2026-08-22) |
| `documents_search_fulltext` | `imanage-work` | `partner_gated` | `unverifiable-partner-gated` | private Work API full-text search; no public machine-readable spec, and 159 frozen world walks depend on the current wire shape (verified 2026-08-22) |
| `drive_files_get` | `google-drive-v3` | `google_discovery` | `exact-to-pinned-public-contract` | drive.files.get |
| `drive_files_list` | `google-drive-v3` | `google_discovery` | `exact-to-pinned-public-contract` | drive.files.list |
| `efiling_cases_get` | `cmecf-nextgen` | `documentation_fixture` | `documentation-fixture-conformant` | case-selection |
| `efiling_docket_entries_list` | `cmecf-nextgen` | `documentation_fixture` | `documentation-fixture-conformant` | docket-report |
| `efiling_filings_create` | `cmecf-nextgen` | `documentation_fixture` | `documentation-fixture-conformant` | event-pdf-submit-nef |
| `efiling_nef_notices_list` | `cmecf-nextgen` | `documentation_fixture` | `documentation-fixture-conformant` | notice-of-electronic-filing |
| `esign_envelopes_create` | `docusign-esign-v2.1` | `swagger` | `exact-to-pinned-public-contract` | Envelopes_PostEnvelopes |
| `esign_envelopes_get` | `docusign-esign-v2.1` | `swagger` | `exact-to-pinned-public-contract` | Envelopes_GetEnvelope |
| `esign_envelopes_send` | `docusign-esign-v2.1` | `swagger` | `exact-to-pinned-public-contract` | Envelopes_PutEnvelope |
| `esign_recipients_list` | `docusign-esign-v2.1` | `swagger` | `exact-to-pinned-public-contract` | Recipients_GetRecipients |
| `expense_entries_create` | `clio-manage-v4` | `openapi` | `exact-to-pinned-public-contract` | post · /activities.json |
| `expense_entries_list` | `clio-manage-v4` | `openapi` | `exact-to-pinned-public-contract` | get · /activities.json |
| `folders_list` | `imanage-work` | `imanage_connector` | `public-connector-conformant-fidelity-ceiling` | SearchFolders |
| `gmail_messages_get` | `google-gmail-v1` | `google_discovery` | `exact-to-pinned-public-contract` | gmail.users.messages.get |
| `gmail_messages_list` | `google-gmail-v1` | `google_discovery` | `exact-to-pinned-public-contract` | gmail.users.messages.list |
| `gmail_messages_send` | `google-gmail-v1` | `google_discovery` | `exact-to-pinned-public-contract` | gmail.users.messages.send |
| `holds_create` | `relativity-rest` | `documentation_fixture` | `documentation-fixture-conformant` | holds_create |
| `holds_list` | `relativity-rest` | `documentation_fixture` | `documentation-fixture-conformant` | holds_list |
| `invoices_submit` | `ledes-1998b` | `published_standard` | `published-standard-conformant` | ledes-1998b-file |
| `jobs_get` | `relativity-rest` | `documentation_fixture` | `documentation-fixture-conformant` | jobs_get |
| `matters_create` | `clio-manage-v4` | `openapi` | `exact-to-pinned-public-contract` | post · /matters.json |
| `matters_get` | `clio-manage-v4` | `openapi` | `exact-to-pinned-public-contract` | get · /matters/{id}.json |
| `matters_list` | `clio-manage-v4` | `openapi` | `exact-to-pinned-public-contract` | get · /matters.json |
| `matters_search` | `clio-manage-v4` | `openapi` | `exact-to-pinned-public-contract` | get · /matters.json |
| `matters_update` | `clio-manage-v4` | `openapi` | `exact-to-pinned-public-contract` | patch · /matters/{id}.json |
| `notes_create` | `clio-manage-v4` | `openapi` | `exact-to-pinned-public-contract` | post · /notes.json |
| `notes_list` | `clio-manage-v4` | `openapi` | `exact-to-pinned-public-contract` | get · /notes.json |
| `opinions_get` | `courtlistener-v4` | `live_diff` | `live-diff-conformant-to-pinned-source` | get · /api/rest/v4/opinions/{id}/ |
| `opinions_search` | `courtlistener-v4` | `live_diff` | `live-diff-conformant-to-pinned-source` | get · /api/rest/v4/search/ |
| `parties_list` | `courtlistener-v4` | `live_diff` | `live-diff-conformant-to-pinned-source` | get · /api/rest/v4/parties/ |
| `practice_areas_list` | `clio-manage-v4` | `openapi` | `exact-to-pinned-public-contract` | get · /practice_areas.json |
| `privilege_log_create` | `relativity-rest` | `documentation_fixture` | `documentation-fixture-conformant` | privilege_log_create |
| `privilege_log_list` | `relativity-rest` | `documentation_fixture` | `documentation-fixture-conformant` | privilege_log_list |
| `productions_create` | `relativity-rest` | `documentation_fixture` | `documentation-fixture-conformant` | productions_create |
| `productions_list` | `relativity-rest` | `documentation_fixture` | `documentation-fixture-conformant` | productions_list |
| `recap_documents_get` | `courtlistener-v4` | `live_diff` | `live-diff-conformant-to-pinned-source` | get · /api/rest/v4/recap-documents/{id}/ |
| `recap_documents_list` | `courtlistener-v4` | `live_diff` | `live-diff-conformant-to-pinned-source` | get · /api/rest/v4/recap-documents/ |
| `review_documents_get` | `relativity-rest` | `documentation_fixture` | `documentation-fixture-conformant` | review_documents_get |
| `review_documents_search` | `relativity-rest` | `documentation_fixture` | `documentation-fixture-conformant` | review_documents_search |
| `review_workspaces_list` | `relativity-rest` | `documentation_fixture` | `documentation-fixture-conformant` | review_workspaces_list |
| `sheets_values_get` | `google-sheets-v4` | `google_discovery` | `exact-to-pinned-public-contract` | sheets.spreadsheets.values.get |
| `sheets_values_update` | `google-sheets-v4` | `google_discovery` | `exact-to-pinned-public-contract` | sheets.spreadsheets.values.update |
| `spreadsheets_list` | `google-drive-v3` | `google_discovery` | `exact-to-pinned-public-contract` | drive.files.list |
| `tasks_create` | `clio-manage-v4` | `openapi` | `exact-to-pinned-public-contract` | post · /tasks.json |
| `tasks_list` | `clio-manage-v4` | `openapi` | `exact-to-pinned-public-contract` | get · /tasks.json |
| `tasks_update` | `clio-manage-v4` | `openapi` | `exact-to-pinned-public-contract` | patch · /tasks/{id}.json |
| `time_entries_create` | `clio-manage-v4` | `openapi` | `exact-to-pinned-public-contract` | post · /activities.json |
| `time_entries_get` | `clio-manage-v4` | `openapi` | `exact-to-pinned-public-contract` | get · /activities/{id}.json |
| `time_entries_list` | `clio-manage-v4` | `openapi` | `exact-to-pinned-public-contract` | get · /activities.json |
| `time_entries_update` | `clio-manage-v4` | `openapi` | `exact-to-pinned-public-contract` | patch · /activities/{id}.json |
| `trust_transactions_list` | `clio-manage-v4` | `openapi` | `exact-to-pinned-public-contract` | get · /allocations.json |
| `users_list` | `clio-manage-v4` | `openapi` | `exact-to-pinned-public-contract` | get · /users.json |
| `utbms_codes_list` | `utbms` | `published_standard` | `published-standard-conformant` | utbms-code-set |
| `workspaces_list` | `imanage-work` | `partner_gated` | `unverifiable-partner-gated` | private Work API workspace listing; connector SearchWorkspaces is the nearest public capability — a world-version remap candidate (verified 2026-08-22) |
| `workspaces_search` | `imanage-work` | `imanage_connector` | `public-connector-conformant-fidelity-ceiling` | SearchWorkspaces |

## Reproduce

```bash
python3 tools/conformance/sync_specs.py --check
python3 tools/conformance/live.py --base http://127.0.0.1:8974 --check
python3 tools/conformance/run.py --check
# The release gate requires every publicly verifiable contract and zero invented agent tools:
python3 tools/conformance/run.py --strict
```
