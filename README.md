# NASA Technical Reports Server (NTRS) Sitemaps for Onyx RAG

Automated XML sitemaps and plain-text URL indexes for the **NASA Technical Reports Server (NTRS)**, indexing **602,567 total records** spanning over a century of aeronautics and aerospace research (1915–2026).

---

## Important Note on Onyx Web Connector Compatibility

Onyx's Sitemap Connector parses `<loc>` tags from the target XML file and directly queues those URLs for indexing. **It does not recursively follow `<sitemapindex>` hierarchies.** If given a sitemap index (such as `ntrs_sitemap.xml`), Onyx will index the sub-sitemap `.xml` URLs rather than the documents inside them.

To accommodate Onyx directly, this repository provides **flat `<urlset>` sitemaps** containing the actual direct NASA PDF and citation URLs.

---

## Recommended Sitemap URLs for Onyx

### 1. Three-Tier Full-Text PDF Strategy (Zero Duplicate Indexing & Rapid Updates)
To prevent Onyx from spending days re-crawling ~80,000 modern PDFs every time new reports are released, the collection is split into discrete, non-overlapping connectors:

* **Tier 1: Modern Era Baseline (2010–August 2026, ~83,600 PDFs, Frozen)**:
  ```text
  https://raw.githubusercontent.com/Oht8wooWi8yait9n/ntrs/main/sitemaps/pdf/ntrs_pdf_modern.xml
  ```
  *(Frozen baseline. Indexed once by Onyx; never modified, eliminating multi-day re-indexing cycles.)*

* **Tier 2: Active 2026 Updates (September 2026–December 2026, ~225+ PDFs)**:
  ```text
  https://raw.githubusercontent.com/Oht8wooWi8yait9n/ntrs/main/sitemaps/pdf/ntrs_pdf_2026.xml
  ```
  *(Active weekly updates for the remainder of 2026. Indexes in Onyx in under 2 minutes.)*

* **Future Annual Rollover (2027+)**:
  ```text
  https://raw.githubusercontent.com/Oht8wooWi8yait9n/ntrs/main/sitemaps/pdf/ntrs_pdf_2027.xml
  ```
  *(When 2027 begins, `ntrs_pdf_2026.xml` freezes automatically and new updates flow into `ntrs_pdf_2027.xml`.)*

* **Tier 3: Historical / Pre-2010 PDFs (1914–2009, 218,072 PDFs)**:
  ```text
  https://raw.githubusercontent.com/Oht8wooWi8yait9n/ntrs/main/ntrs_pdf_all.xml
  ```
  *(Modern and 2026+ publications excluded to eliminate duplicate re-indexing.)*

> [!NOTE]
> **Zero Duplicate Ingestion**: Tier 1, Tier 2, and Tier 3 have **0% overlap**. Adding these connectors indexes 100% of all NASA technical PDFs without re-indexing a single document.

* **Optional: Complete Master Archive (1914–2026, ~298,000 PDFs in a compressed sitemap)**:
  ```text
  https://raw.githubusercontent.com/Oht8wooWi8yait9n/ntrs/main/ntrs_pdf_complete.xml.gz
  ```

* **Staged 20,000-URL Historical PDF Chunks (~24-Hour Embedding Batches)**:
  Ingesting 20,000 PDFs takes approximately 24 hours in Onyx. Using these 20k chunks lets you stage ingestion day-by-day, allowing you to reboot, run updates, or index other collections in between:
  - **Part 1 (20,000 URLs)**: `https://raw.githubusercontent.com/Oht8wooWi8yait9n/ntrs/main/sitemaps/pdf/ntrs_pdf_1.xml`
  - **Part 2 (20,000 URLs)**: `https://raw.githubusercontent.com/Oht8wooWi8yait9n/ntrs/main/sitemaps/pdf/ntrs_pdf_2.xml`
  - **Part 3 (20,000 URLs)**: `https://raw.githubusercontent.com/Oht8wooWi8yait9n/ntrs/main/sitemaps/pdf/ntrs_pdf_3.xml`
  - **Part 4 (20,000 URLs)**: `https://raw.githubusercontent.com/Oht8wooWi8yait9n/ntrs/main/sitemaps/pdf/ntrs_pdf_4.xml`
  - **Part 5 (20,000 URLs)**: `https://raw.githubusercontent.com/Oht8wooWi8yait9n/ntrs/main/sitemaps/pdf/ntrs_pdf_5.xml`
  - **Part 6 (20,000 URLs)**: `https://raw.githubusercontent.com/Oht8wooWi8yait9n/ntrs/main/sitemaps/pdf/ntrs_pdf_6.xml`
  - **Part 7 (20,000 URLs)**: `https://raw.githubusercontent.com/Oht8wooWi8yait9n/ntrs/main/sitemaps/pdf/ntrs_pdf_7.xml`
  - **Part 8 (20,000 URLs)**: `https://raw.githubusercontent.com/Oht8wooWi8yait9n/ntrs/main/sitemaps/pdf/ntrs_pdf_8.xml`
  - **Part 9 (20,000 URLs)**: `https://raw.githubusercontent.com/Oht8wooWi8yait9n/ntrs/main/sitemaps/pdf/ntrs_pdf_9.xml`
  - **Part 10 (20,000 URLs)**: `https://raw.githubusercontent.com/Oht8wooWi8yait9n/ntrs/main/sitemaps/pdf/ntrs_pdf_10.xml`
  - **Part 11 (18,072 URLs)**: `https://raw.githubusercontent.com/Oht8wooWi8yait9n/ntrs/main/sitemaps/pdf/ntrs_pdf_11.xml`

---

### 2. Complete Catalog (PDFs + Citations / Abstracts)
* **All Records (Compressed Sitemap, 602,567 URLs)**:
  ```text
  https://raw.githubusercontent.com/Oht8wooWi8yait9n/ntrs/main/ntrs_all.xml.gz
  ```

---

### 3. Metadata & Abstract Citations Only (305,104 Records)
* **All Citations (Single Flat Sitemap, 305,104 URLs)**:
  ```text
  https://raw.githubusercontent.com/Oht8wooWi8yait9n/ntrs/main/ntrs_citations_all.xml
  ```

---

## Ingesting into Onyx

1. In the Onyx UI, navigate to **Admin Panel** → **Connectors** → **Web**.
2. Click **Add Connector**:
   - **Name**: `NASA NTRS Historical Technical PDFs (1914-2009)`
   - **Base URL / Sitemap URL**:
     ```text
     https://raw.githubusercontent.com/Oht8wooWi8yait9n/ntrs/main/ntrs_pdf_all.xml
     ```
   - **Scrape Type**: `Sitemap`
   - **Indexing Schedule**: Weekly or Monthly
3. Click **Connect**. Onyx will parse the sitemap, extract the 218,072 historical PDF URLs, and index them without re-indexing any modern era documents.

---

## Automation & Maintenance

A GitHub Actions workflow (`.github/workflows/update-sitemap.yml`) runs weekly on Sundays at 04:00 UTC. It queries the NTRS API for newly released technical reports, updates the XML sitemaps, and commits new entries automatically.
