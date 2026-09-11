# NASA Technical Reports Server (NTRS) Sitemaps for Onyx RAG

Automated XML sitemaps and plain-text URL indexes for the **NASA Technical Reports Server (NTRS)**, indexing **602,567 total records** spanning over a century of aeronautics and aerospace research (1915–2026).

---

## Important Note on Onyx Web Connector Compatibility

Onyx's Sitemap Connector parses `<loc>` tags from the target XML file and directly queues those URLs for indexing. **It does not recursively follow `<sitemapindex>` hierarchies.** If given a sitemap index (such as `ntrs_sitemap.xml`), Onyx will index the sub-sitemap `.xml` URLs rather than the documents inside them.

To accommodate Onyx directly, this repository provides **flat `<urlset>` sitemaps** containing the actual direct NASA PDF and citation URLs.

---

## Recommended Sitemap URLs for Onyx

### 1. Two-Tier Full-Text PDF Strategy (Recommended - Zero Duplicate Indexing)
To prevent Onyx from spending time re-indexing modern PDFs when ingesting historical reports, the full-text technical collection is split into two non-overlapping connectors:

* **Tier 1: Modern Era PDFs (2010–2026, 79,391 PDFs)** *(Fastest initial technical RAG)*:
  ```text
  https://raw.githubusercontent.com/Oht8wooWi8yait9n/ntrs/main/sitemaps/pdf/ntrs_pdf_modern.xml
  ```

* **Tier 2: Historical / Pre-2010 PDFs (1914–2009, 218,072 PDFs)** *(Modern 2010–2026 excluded to eliminate duplicate re-indexing)*:
  ```text
  https://raw.githubusercontent.com/Oht8wooWi8yait9n/ntrs/main/ntrs_pdf_all.xml
  ```
  *(Also accessible via `https://raw.githubusercontent.com/Oht8wooWi8yait9n/ntrs/main/ntrs_pdf_historical.xml`)*

> [!NOTE]
> **Zero Duplicate Ingestion**: Tier 1 (79,391) and Tier 2 (218,072) have **0% overlap**. Adding both connectors indexes 100% of all 297,463 NASA technical PDFs without re-indexing a single document.

* **Optional: Complete Master Archive (1914–2026, 297,463 PDFs in a single flat file)**:
  ```text
  https://raw.githubusercontent.com/Oht8wooWi8yait9n/ntrs/main/ntrs_pdf_complete.xml
  ```

* **Individual 50,000-URL Historical PDF Chunks (For Staged Ingestion)**:
  - Part 1: `https://raw.githubusercontent.com/Oht8wooWi8yait9n/ntrs/main/sitemaps/pdf/ntrs_pdf_1.xml`
  - Part 2: `https://raw.githubusercontent.com/Oht8wooWi8yait9n/ntrs/main/sitemaps/pdf/ntrs_pdf_2.xml`
  - Part 3: `https://raw.githubusercontent.com/Oht8wooWi8yait9n/ntrs/main/sitemaps/pdf/ntrs_pdf_3.xml`
  - Part 4: `https://raw.githubusercontent.com/Oht8wooWi8yait9n/ntrs/main/sitemaps/pdf/ntrs_pdf_4.xml`
  - Part 5: `https://raw.githubusercontent.com/Oht8wooWi8yait9n/ntrs/main/sitemaps/pdf/ntrs_pdf_5.xml`

---

### 2. Complete Catalog (PDFs + Citations / Abstracts)
* **All Records (Single Flat Sitemap, 602,567 URLs)**:
  ```text
  https://raw.githubusercontent.com/Oht8wooWi8yait9n/ntrs/main/ntrs_all.xml
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
