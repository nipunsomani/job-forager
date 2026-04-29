# Job Source API Documentation

This document describes every job source collector in detail: the API endpoint, authentication, request format, response schema, pagination strategy, and coverage.

## Coverage Summary (No Limits)

| Source | Endpoints Explored | Pagination | Jobs Fetched |
|--------|-------------------|------------|--------------|
| **Remotive** | 1 API call | None - single request | All available (~22) |
| **Hacker News** | 1 thread + 50 comments | None - single thread | Top 50 comments |
| **RemoteOK** | 1 API call | None - single request | All available (~99) |
| **ArbeitNow** | 1 API call | None - single request | All available (~100) |
| **Greenhouse** | **All 8,032 board tokens** | None - single GET per board | All jobs per board |
| **Lever** | **All 4,368 company slugs** | None - single GET per company | All jobs per company |
| **Ashby** | **All 2,796 board names** | None - single GET per board | All jobs per board |
| **Workday** | **All companies** (live list) | 20 jobs per page, **all pages** | Up to 2,000 per company (API hard limit) |
| **SmartRecruiters** | **All slugs** (live list) | 100 jobs per page, **all pages** | All jobs per slug |
| **Hiring.cafe** | 1 API query | 1,000 jobs per page, **all pages** | All matching jobs |
| **LinkedIn** | JobSpy scraper | Page-scrolled scraping | Up to 50 per query (configurable) |
| **Indeed** | JobSpy scraper | Page-scrolled scraping | Up to 50 per query (configurable) |
| **Glassdoor** | JobSpy scraper | Page-scrolled scraping | Up to 50 per query (configurable) |

All multi-endpoint sources use **ThreadPoolExecutor** for concurrent fetching. Default: 30 workers.

---

## Remotive

**Module**: `search/remotive.py`
**Function**: `collect_remotive_jobs()`

### Endpoint
```
GET https://remotive.com/api/remote-jobs?category=software-dev&limit=50
```

### Authentication
None. No API key required.

### Headers Required
```python
{
    "User-Agent": "Mozilla/5.0 (compatible; jobforager/1.0)",
    "Accept": "application/json",
    "Referer": "https://remotive.com/",
}
```

### Response Format
```json
{
  "jobs": [
    {
      "id": 123,
      "title": "Software Engineer",
      "company_name": "Example Co",
      "description": "<p>Job description HTML</p>",
      "url": "https://remotive.com/remote-jobs/...",
      "candidate_required_location": "Worldwide",
      "salary": "$100k-$150k",
      "tags": ["python", "django"],
      "publication_date": "2024-01-15T09:00:00",
      "job_type": "full_time"
    }
  ]
}
```

### Fields Mapped
| Raw Field | JobRecord Field |
|-----------|-----------------|
| `title` | `title` |
| `company_name` | `company` |
| `url` | `job_url` |
| `candidate_required_location` | `location` |
| `salary` | `salary_raw` |
| `tags` | `tags` |
| `publication_date` | `posted_at` |
| `job_type` | `metadata["job_type"]` |

### Coverage
- **Endpoints**: 1 API call (`category=software-dev`, `limit=999`)
- **Pagination**: None - single request returns all available jobs
- **Jobs fetched**: All available (API ceiling, typically ~20-50)

### Notes
- HTML descriptions are stripped to plain text
- All Remotive jobs are treated as remote

---

## Hacker News "Who is Hiring"

**Module**: `search/hackernews.py`
**Function**: `collect_hackernews_jobs()`

### Endpoints
1. **Thread Discovery**: Algolia Search API
   ```
   GET https://hn.algolia.com/api/v1/search?query=Ask+HN:+Who+is+hiring&tags=story&hitsPerPage=5
   ```

2. **Comment Fetching**: Firebase HN API
   ```
   GET https://hacker-news.firebaseio.com/v0/item/{thread_id}.json
   GET https://hacker-news.firebaseio.com/v0/item/{comment_id}.json
   ```

### Authentication
None.

### Response Format
Thread object:
```json
{
  "id": 39081621,
  "title": "Ask HN: Who is hiring? (January 2024)",
  "kids": [39081701, 39081715, ...],
  "time": 1704499200
}
```

Comment object:
```json
{
  "id": 39081701,
  "by": "companyname",
  "text": "CompanyName | Role | Location | Remote | ...",
  "time": 1704500000
}
```

### Parsing Strategy
Comments use a pipe-delimited format:
```
Company | Role | Location | Remote/Onsite | Technologies | URL
```

The parser falls back to line-by-line extraction if pipes are missing.

### Coverage
- **Endpoints**: 1 Algolia search + 1 thread + up to 50 comment fetches
- **Pagination**: None - fetches top 50 comments from the current month's thread
- **Jobs fetched**: Up to 50 (all top-level comments)

### Notes
- Finds the most recent "Who is Hiring" thread automatically
- Fetches top-level comments only (jobs)
- May miss jobs with non-standard formatting
- No salary data available

---

## RemoteOK

**Module**: `search/remoteok.py`
**Function**: `collect_remoteok_jobs(tag=None)`

### Endpoint
```
GET https://remoteok.com/api
GET https://remoteok.com/api?tag=python
```

### Authentication
None.

### Headers Required
```python
{
    "User-Agent": "Mozilla/5.0 (compatible; jobforager/1.0)",
    "Accept": "application/json",
    "Referer": "https://remoteok.com/",
}
```

### Response Format
Array where the first element is metadata, rest are jobs:
```json
[
  {"legal": "...", "count": 42},
  {
    "id": "remoteok-123",
    "position": "Senior Engineer",
    "company": "Remote Co",
    "location": "Worldwide",
    "url": "https://remoteok.com/remote-jobs/...",
    "apply_url": "https://...",
    "description": "Job description...",
    "salary": "$120k - $150k",
    "tags": ["python", "remote"],
    "date": "2024-01-15T09:00:00Z"
  }
]
```

### Coverage
- **Endpoints**: 1 API call (`/api` or `/api?tag={tag}`)
- **Pagination**: None - single request returns all available jobs
- **Jobs fetched**: All available (typically ~99)

### Notes
- First array element is metadata (skipped)
- All jobs are remote by definition
- Optional `tag` parameter filters by technology

---

## ArbeitNow

**Module**: `search/arbeitnow.py`
**Function**: `collect_arbeitnow_jobs()`

### Endpoint
```
GET https://arbeitnow.com/api/job-board-api
```

### Authentication
None.

### Headers Required
```python
{
    "User-Agent": "Mozilla/5.0 (compatible; jobforager/1.0)",
    "Accept": "application/json",
    "Referer": "https://arbeitnow.com/",
}
```

### Response Format
```json
{
  "data": [
    {
      "slug": "software-engineer-example-co",
      "title": "Software Engineer",
      "company_name": "Example Co",
      "description": "Job description...",
      "url": "https://arbeitnow.com/jobs/...",
      "location": "Berlin, Germany",
      "remote": true,
      "tags": ["python", "django"],
      "date": "2024-01-15T09:00:00Z"
    }
  ]
}
```

### Coverage
- **Endpoints**: 1 API call (`/api/job-board-api`)
- **Pagination**: None - single request returns all available jobs
- **Jobs fetched**: All available (typically ~100)

### Notes
- Response is wrapped in `{"data": [...]}` (not a direct array)
- `remote` boolean field determines `remote_type`
- European-focused job board

---

## Greenhouse

**Module**: `search/greenhouse.py`
**Function**: `collect_greenhouse_jobs(board_tokens, include_content, delay)`

### Endpoint
```
GET https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs
GET https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true
```

### Authentication
None. Public API.

### Response Format
```json
{
  "jobs": [
    {
      "id": 123,
      "internal_job_id": 456,
      "title": "Software Engineer",
      "absolute_url": "https://boards.greenhouse.io/stripe/jobs/123",
      "location": {"name": "San Francisco, CA"},
      "updated_at": "2024-01-15T09:00:00-05:00",
      "first_published": "2024-01-10T09:00:00-05:00",
      "requisition_id": "REQ-001",
      "company_name": "Stripe",
      "metadata": [
        {"name": "Workplace Type", "value": "Remote", "value_type": "single_select"}
      ],
      "content": "<p>Full description HTML</p>"
    }
  ]
}
```

### Remote Type Detection
Checks `metadata` array for item with `name == "Workplace Type"`:
- `"Remote"` → `remote`
- `"Hybrid"` → `hybrid`
- `"On-site"`, `"Onsite"` → `onsite`

### Coverage
- **Endpoints**: **All 8,032 board tokens** explored concurrently (30 workers)
- **Pagination**: None - single GET per board returns all jobs
- **Jobs fetched**: All jobs from every board

### Company Lists
- Fetches **8,032 tokens** live from Feashliaa + stapply-ai on every run
- No local caching - fresh data on every execution

### Notes
- `content=true` fetches full HTML descriptions (slower)
- `metadata` may be `null` - handled gracefully
- Concurrent fetching: 100 boards → ~1,143 jobs in ~2 seconds

---

## Lever

**Module**: `search/lever.py`
**Function**: `collect_lever_jobs(company_slugs, delay)`

### Endpoint
```
GET https://api.lever.co/v0/postings/{company_slug}?mode=json
```

### Authentication
None. Public API.

### Response Format
Array of job objects:
```json
[
  {
    "id": "abc-123",
    "text": "Senior Engineer",
    "categories": {
      "location": "San Francisco, CA",
      "commitment": "Full-time",
      "team": "Platform",
      "department": "Engineering"
    },
    "country": "US",
    "workplaceType": "remote",
    "createdAt": 1705276800000,
    "hostedUrl": "https://jobs.lever.co/netflix/abc-123",
    "applyUrl": "https://jobs.lever.co/netflix/abc-123/apply",
    "descriptionPlain": "Build scalable systems.",
    "salaryRange": {
      "currency": "USD",
      "interval": "yearly",
      "min": 180000,
      "max": 250000
    }
  }
]
```

### Field Mapping
| Raw Field | JobRecord Field |
|-----------|-----------------|
| `text` | `title` |
| `categories.location` | `location` |
| `categories.department` | `tags[0]` |
| `categories.team` | `tags[1]` |
| `categories.commitment` | `tags[2]` |
| `workplaceType` | `remote_type` |
| `createdAt` (ms epoch) | `posted_at` (ISO) |
| `hostedUrl` | `job_url` |
| `applyUrl` | `apply_url` |
| `descriptionPlain` | `description` |
| `salaryRange` | `salary_raw`, `salary_min_usd`, `salary_max_usd` |

### Coverage
- **Endpoints**: **All 4,368 company slugs** explored concurrently (30 workers)
- **Pagination**: None - single GET per company returns all jobs
- **Jobs fetched**: All jobs from every company

### Company Lists
- Fetches **4,368 slugs** live from Feashliaa + stapply-ai on every run
- No local caching - fresh data on every execution

### Notes
- Concurrent fetching: 100 companies → ~1,051 jobs in ~20 seconds

---

## Ashby

**Module**: `search/ashby.py`
**Function**: `collect_ashby_jobs(board_names, include_compensation, delay)`

### Endpoint
```
GET https://api.ashbyhq.com/posting-api/job-board/{board_name}?includeCompensation=true
```

### Authentication
None. Public API.

### Response Format
```json
{
  "jobs": [
    {
      "title": "Software Engineer",
      "jobUrl": "https://jobs.ashbyhq.com/supabase/...",
      "location": "Remote",
      "workplaceType": "remote",
      "publishedAt": "2024-01-15T09:00:00Z",
      "applyUrl": "https://jobs.ashbyhq.com/supabase/.../apply",
      "descriptionPlain": "Job description...",
      "descriptionHtml": "<p>Job description...</p>",
      "department": "Engineering",
      "team": "Platform",
      "employmentType": "Full-time",
      "isRemote": true,
      "compensation": {
        "compensationTierSummary": "$120k - $150k",
        "summaryComponents": [
          {"compensationType": "Salary", "minValue": 120000, "maxValue": 150000}
        ]
      }
    }
  ]
}
```

### Salary Extraction
Parses `compensation.summaryComponents` for `compensationType == "Salary"`, extracts `minValue` and `maxValue`.

### Coverage
- **Endpoints**: **All 2,796 board names** explored concurrently (30 workers)
- **Pagination**: None - single GET per board returns all jobs
- **Jobs fetched**: All jobs from every board

### Company Lists
- Fetches **2,796 boards** live from Feashliaa + stapply-ai on every run
- No local caching - fresh data on every execution

### Notes
- Concurrent fetching: 100 boards → ~1,591 jobs in ~17 seconds

---

## Workday

**Module**: `search/workday.py`
**Function**: `collect_workday_jobs(companies, max_results_per_company, delay)`

### API Approach
**Reverse-engineered Calypso API** - no official public API exists. Workday career sites expose an internal JSON API used by their frontend.

### Two-Step Process

#### Step 1: Obtain CSRF Token
```
GET https://{company}.wd5.myworkdayjobs.com/{site_name}
```
Extract `x-calypso-csrf-token` from response headers.

#### Step 2: Search Jobs
```
POST https://{company}.wd5.myworkdayjobs.com/wday/cxs/{company}/{site_name}/jobs
```

**Request Body**:
```json
{
  "appliedFacets": {},
  "limit": 20,
  "offset": 0,
  "searchText": ""
}
```

**Headers**:
```python
{
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Origin": "https://{domain}",
    "Referer": "https://{career_site_url}",
    "x-calypso-csrf-token": "{csrf_token}",
}
```

### Response Format
```json
{
  "jobPostings": [
    {
      "title": "Software Engineer",
      "externalPath": "/job/Location/Title_ID",
      "postedOn": "Posted Today",
      "bulletFields": ["REQ-123", "San Francisco, CA"]
    }
  ],
  "total": 150,
  "facets": [...]
}
```

### Field Mapping
| Raw Field | JobRecord Field | Notes |
|-----------|-----------------|-------|
| `title` | `title` | |
| `externalPath` | `job_url` | Prepended with career site URL |
| `bulletFields[0]` | `external_id` | Usually requisition ID |
| `bulletFields[1]` | `location` | May be missing |
| `postedOn` | `posted_at` | Human-readable string (e.g., "Posted Today") |

### Coverage
- **Endpoints**: All companies from live list (currently 2: Accenture, NVIDIA)
- **Pagination**: 20 jobs per page, **all pages fetched** until exhausted
- **Jobs fetched**: All pages per company (up to 2,000 - Workday API hard limit)

### Company Lists
- Fetches live from stapply-ai/ats-scrapers CSV on every run
- No local caching - fresh data on every execution

### Known Issues
- **2000 results maximum** per company (Workday API hard limit - cannot bypass)
- `postedOn` is a human-readable string, not a parseable date
- Location may be missing from `bulletFields` for some postings
- CSRF approach is brittle - may break if Workday changes their frontend

---

## SmartRecruiters

**Module**: `search/smartrecruiters.py`
**Function**: `collect_smartrecruiters_jobs(company_slugs, delay)`

### Endpoint
```
GET https://api.smartrecruiters.com/v1/companies/{company_slug}/postings?limit=100&offset=0
```

### Authentication
None. Public API.

### Response Format
```json
{
  "content": [
    {
      "id": "6000000001019641",
      "name": "Senior Engineer",
      "company": {"name": "Adobe"},
      "location": {"city": "San Francisco", "country": "US"},
      "postingUrl": null,
      "createdOn": "2024-01-15T09:00:00Z",
      "refNumber": "REF-001",
      "jobAd": {
        "sections": {
          "jobDescription": {"text": "Build great products."}
        }
      },
      "typeOfEmployment": {"label": "Full-time"}
    }
  ],
  "totalFound": 150,
  "limit": 100,
  "offset": 0
}
```

### URL Construction
The list API does **not** return `postingUrl`. URLs are constructed as:
```
https://jobs.smartrecruiters.com/{company_slug}/{job_id}
```

### Pagination
- `limit=100` per page
- Increment `offset` by 100 until `len(content) < 100` or `len(all_content) >= totalFound`
- 404 on first page = company slug not found

### Coverage
- **Endpoints**: All slugs from live list (currently 5: adobe1, canva, deloitte6, experian, samsung1)
- **Pagination**: 100 jobs per page, **all pages fetched** per slug
- **Jobs fetched**: All jobs from every slug

### Company Lists
- Fetches live from stapply-ai CSV on every run
- No local caching - fresh data on every execution

### Notes
- Description extracted from `jobAd.sections.jobDescription.text`
- Location built from `city + country`
- Employment type added to tags

---

## Hiring.cafe

**Module**: `search/hiringcafe.py`
**Function**: `collect_hiringcafe_jobs(search_query, location, remote_only, max_results)`

### API Approach
**Aggregated meta-search API** - Hiring.cafe maintains a 2.1M+ job index from 46 ATS platforms. This collector queries their API rather than scraping individual sites.

### Endpoints
1. **Count**: `POST https://hiring.cafe/api/search-jobs/get-total-count`
2. **Jobs**: `POST https://hiring.cafe/api/search-jobs`

### Authentication
None. No API key required.

### Headers Required
```python
{
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ...",
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "Referer": "https://hiring.cafe/",
    "Origin": "https://hiring.cafe",
}
```

### Request Payload
```json
{
  "size": 1000,
  "page": 0,
  "searchState": {
    "searchQuery": "python",
    "locations": [],
    "workplaceTypes": ["Remote", "Hybrid", "Onsite"],
    "commitmentTypes": ["Full Time", "Part Time", "Contract", ...],
    "seniorityLevel": ["No Prior Experience Required", "Entry Level", "Mid Level"],
    "dateFetchedPastNDays": 61,
    "sortBy": "default"
  }
}
```

### Response Format
```json
{
  "results": [
    {
      "id": "job-id",
      "board_token": "company-board",
      "source": "Company Name",
      "apply_url": "https://careers.company.com/job/123",
      "job_information": {
        "title": "Software Engineer",
        "description": "<p>Job description HTML</p>",
        "viewedByUsers": [],
        "appliedFromUsers": [],
        "savedFromUsers": [],
        "hiddenFromUsers": []
      }
    }
  ]
}
```

### Fields Mapped
| Raw Field | JobRecord Field |
|-----------|-----------------|
| `job_information.title` | `title` |
| `source` | `company` |
| `apply_url` | `job_url`, `apply_url` |
| `job_information.description` | `description` (HTML stripped) |
| `id` | `external_id` |
| `board_token` | `metadata["board_token"]` |

### Coverage
- **Endpoints**: 1 API query
- **Pagination**: 1,000 jobs per page, **all pages fetched**
- **Jobs fetched**: All matching jobs from the 2.1M+ index

### Transport Layers (3-Tier Fallback)
1. `urllib` - fastest, works if no bot protection
2. `curl_cffi` - TLS fingerprint spoofing for some WAFs
3. `Playwright` - browser automation for Cloudflare JS challenge

### Notes
- HTML descriptions are stripped to plain text
- Includes user engagement metadata (viewed/applied/saved counts)
- Returns jobs from 46 underlying ATS platforms transparently
- To enable Playwright fallback: `pip install playwright && playwright install chromium`

---

## LinkedIn (via JobSpy)

**Module**: `search/jobspy_source.py`  
**Function**: `collect_linkedin_jobs(search_term, location, results_wanted, hours_old)`

### API Approach
**Scraper-based** - JobSpy uses headless-browser-style requests to scrape LinkedIn job search results. No official public API.

### Authentication
None. No API key required.

### Parameters
| Parameter | Default | Description |
|-----------|---------|-------------|
| `search_term` | (from `--keywords` or `--title-keywords`) | Keywords sent to LinkedIn search |
| `location` | (from `--location`) | Geographic location filter |
| `results_wanted` | `50` | Max results to fetch |
| `hours_old` | `168` | Only jobs posted within last N hours |

### Response Format
JobSpy returns a pandas DataFrame. Fields mapped to JobRecord:

| Raw Field | JobRecord Field |
|-----------|-----------------|
| `title` | `title` |
| `company` | `company` |
| `job_url` | `job_url`, `apply_url` |
| `location` | `location` |
| `description` | `description` |
| `date_posted` | `posted_at` |
| `is_remote` | `remote_type` (`remote` or `onsite`) |
| `min_amount` / `max_amount` / `currency` | `salary_raw`, `salary_min_usd`, `salary_max_usd` |
| `id` | `external_id` |

### Coverage
- **Endpoints**: LinkedIn `/jobs-guest/jobs/api/jsee...` internal endpoint
- **Pagination**: Scrolled pagination inside JobSpy
- **Jobs fetched**: Up to `results_wanted` per query (default 50)

### Notes
- **Optional dependency**: Requires `pip install python-jobspy`. If not installed, collector returns `[]` silently.
- `--keywords`, `--title-keywords`, and `--desc-keywords` are combined into `search_term` for the scraper. Local title/description filters still apply after fetch.
- LinkedIn rate-limits aggressively; results may vary by IP.

---

## Indeed (via JobSpy)

**Module**: `search/jobspy_source.py`  
**Function**: `collect_indeed_jobs(search_term, location, results_wanted, hours_old)`

### API Approach
**Scraper-based** - JobSpy scrapes Indeed search results HTML.

### Parameters
Same interface as LinkedIn above.

### Coverage
- **Endpoints**: Indeed search results pages
- **Pagination**: Scrolled pagination inside JobSpy
- **Jobs fetched**: Up to `results_wanted` per query (default 50)

### Notes
- **Optional dependency**: Requires `pip install python-jobspy`.
- Generally more stable than LinkedIn scraping.

---

## Glassdoor (via JobSpy)

**Module**: `search/jobspy_source.py`  
**Function**: `collect_glassdoor_jobs(search_term, location, results_wanted, hours_old)`

### API Approach
**Scraper-based** - JobSpy scrapes Glassdoor job search results.

### Parameters
Same interface as LinkedIn above.

### Coverage
- **Endpoints**: Glassdoor search results pages
- **Pagination**: Scrolled pagination inside JobSpy
- **Jobs fetched**: Up to `results_wanted` per query (default 50)

### Notes
- **Optional dependency**: Requires `pip install python-jobspy`.
- Subject to Cloudflare WAF blocks; may return empty results on some IPs.

---

## Rate Limiting & Concurrency

| Source | Concurrency | Delay | Workers |
|--------|------------|-------|---------|
| Remotive | Single call | None | N/A |
| Hacker News | Sequential | 0.5s between comments | N/A |
| RemoteOK | Single call | None | N/A |
| ArbeitNow | Single call | None | N/A |
| **Greenhouse** | **Parallel** (ThreadPoolExecutor) | None | **30** |
| **Lever** | **Parallel** (ThreadPoolExecutor) | None | **30** |
| **Ashby** | **Parallel** (ThreadPoolExecutor) | None | **30** |
| **Workday** | **Parallel** (ThreadPoolExecutor) | 0.5s | **10** |
| **SmartRecruiters** | **Parallel** (ThreadPoolExecutor) | None | **10** |
| Hiring.cafe | Sequential pages | None | N/A |
| LinkedIn | Internal (JobSpy) | None | N/A |
| Indeed | Internal (JobSpy) | None | N/A |
| Glassdoor | Internal (JobSpy) | None | N/A |

### General Guidelines
- **No artificial limits**: All multi-endpoint sources explore every available company/board/slug
- **Concurrent fetching**: Greenhouse, Lever, Ashby, Workday, and SmartRecruiters use `ThreadPoolExecutor` for parallel requests
- **CLI `--workers` flag**: Controls concurrency for multi-company sources (default: 30)
- All collectors gracefully handle network errors and return `[]`
- Company lists are fetched live from GitHub on every run (no caching)
- JobSpy sources (LinkedIn, Indeed, Glassdoor) are **optional** - install with `pip install python-jobspy`
