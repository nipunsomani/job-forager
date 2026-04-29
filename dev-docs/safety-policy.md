# Safety Policy

## Core Principles

1. **No automated job application submission** - Job Forager discovers and filters jobs. It never submits applications on behalf of users.
2. **No credential handling** - No passwords, API keys, or OAuth tokens are stored or transmitted.
3. **No ATS browser automation** - No Selenium, Playwright, or similar tools for automated form filling.
4. **Additive, reversible changes only** - Every change must be undoable without data loss.
5. **Explicit user confirmation** - Any future apply-assist features require explicit user approval per action.

## Data Handling

- Job data is fetched from public APIs only
- No personal data (resumes, cover letters) is processed unless explicitly provided by the user
- No data is sent to third-party services beyond the public job APIs
- Local caching is used for company lists and API responses only

## Rate Limiting & Respect

- All collectors include delays between requests
- User-Agent headers identify the tool clearly
- No aggressive scraping or circumvention of API limits
- Respects robots.txt and terms of service where applicable

## Future Automation Boundaries

If apply-assist features are implemented (Phase "Later"):
- Forms may be pre-filled for user review
- Cover letters may be generated as drafts
- **No form may be submitted without explicit user confirmation**
- Screenshots may be captured for record-keeping
- All automation is opt-in per action

## Reporting Issues

If you discover any safety or security concern:
1. Do not open a public issue
2. Contact the maintainers directly
3. Provide details of the concern and suggested mitigation
