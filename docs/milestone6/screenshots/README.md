# Screenshot provenance

Five PNGs are real Microsoft Edge/Playwright captures of the running React application at **1440×1100**. No UI text, labels, scores or records were altered for the images. The UI's normal category filter limits the Inbox to the two existing delivery tickets; Analytics shows all 26 synthetic QA tickets.

| File | Visible state |
| --- | --- |
| `01-overview.png` | Connected backend/local AI, filtered ticket counts and Inbox |
| `02-smart-inbox.png` | English delivery ticket selected, Overview and workflow |
| `03-order-verification.png` | Synthetic LumaLite order snapshot and estimate |
| `04-draft-review.png` | Existing pending reply with explicit human controls; nothing sent |
| `05-analytics.png` | Actual QA totals, category/priority/status distributions and volume |

The database was copied with SQLite's backup API from the existing isolated `.cache/milestone5d/browser-qa.db` into `.cache/milestone6/screenshots.db`. The original configured database was never used as the capture server's target. Its path was checked before startup; the browser also verified the unique synthetic QA sentinel. The older QA database was opened read-only for copying and was not changed.

Capture used localhost backend **8017**, frontend **5196**. `frontend/scripts/capture-milestone6.mjs` permits GET requests only and validates same-origin access. Successful capture recorded **0 inference calls, 0 API mutations, 0 page errors, 0 API errors**. Screenshots reuse existing 5D model output and local review decisions; they are not new Qwen evidence. One initial locator attempt failed before the last two screenshots; the accessible target was corrected. Visual inspection then found a still-loading workflow in the Inbox image; an explicit ready-state wait and one read-only `--refresh` recapture produced the final images. Both successful capture records are preserved locally. No application code changed.

Local profiles/capture metadata stay ignored under `.cache/milestone6/`; only the reviewed PNGs/provenance are public. Screenshot generation requires that preserved synthetic QA state and the installed Edge browser; it is not required to install/run the app on a clean clone. For a fresh demo, use the empty-ticket database described in the [demo script](../demo-script.md), not this archival snapshot. Manual presentation rehearsal remains the owner's task.
