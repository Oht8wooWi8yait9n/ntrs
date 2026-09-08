# NASA Technical Reports Server (NTRS) Sitemaps for Onyx RAG

Automated XML sitemaps and plain-text URL indexes for the **NASA Technical Reports Server (NTRS)**, indexing **602,567 total records** spanning over a century of aeronautics and aerospace research (1915–2026).

---

## Important Note on Onyx Web Connector Compatibility

Onyx's Sitemap Connector parses `<loc>` tags from the target XML file and directly queues those URLs for indexing. **It does not recursively follow `<sitemapindex>` hierarchies.** If given a sitemap index (such as `ntrs_sitemap.xml`), Onyx will index the 13 sub-sitemap `.xml` URLs rather than the documents inside them.

To accommodate Onyx directly, this repository provides **flat `<urlset>` sitemaps** containing the actual direct NASA PDF and citation URLs.

---

## Recommended Sitemap URLs for Onyx

### 1. Full-Text PDFs Only (Recommended for Deep Technical Search)
* **All Full-Text PDFs (Single Flat Sitemap, 297,463 PDFs)**:
  ```text
  https://raw.githubusercontent.com/Oht8wooWi8yait9n/ntrs/main/ntrs_pdf_all.xml
  ```
* **Modern Era PDFs Only (2010–2026, 79,391 PDFs)** *(Fastest initial technical RAG)*:
  ```text
  https://raw.githubusercontent.com/Oht8wooWi8yait9n/ntrs/main/sitemaps/pdf/ntrs_pdf_modern.xml
  ```
* **Individual 50,000-URL PDF Chunks (For Staged Ingestion)**:
  - Part 1: `https://raw.githubusercontent.com/Oht8wooWi8yait9n/ntrs/main/sitemaps/pdf/ntrs_pdf_1.xml`
  - Part 2: `https://raw.githubusercontent.com/Oht8wooWi8yait9n/ntrs/main/sitemaps/pdf/ntrs_pdf_2.xml`
  - Part 3: `https://raw.githubusercontent.com/Oht8wooWi8yait9n/ntrs/main/sitemaps/pdf/ntrs_pdf_3.xml`
  - Part 4: `https://raw.githubusercontent.com/Oht8wooWi8yait9n/ntrs/main/sitemaps/pdf/ntrs_pdf_4.xml`
  - Part 5: `https://raw.githubusercontent.com/Oht8wooWi8yait9n/ntrs/main/sitemaps/pdf/ntrs_pdf_5.xml`
  - Part 6: `https://raw.githubusercontent.com/Oht8wooWi8yait9n/ntrs/main/sitemaps/pdf/ntrs_pdf_6.xml`

### 2. Complete Catalog (PDFs + Citations / Abstracts)
* **All Records (Single Flat Sitemap, 602,567 URLs)**:
  ```text
  https://raw.githubusercontent.com/Oht8wooWi8yait9n/ntrs/main/ntrs_all.xml
  ```

### 3. Metadata & Abstract Citations Only (305,104 Records)
* **All Citations (Single Flat Sitemap, 305,104 URLs)**:
  ```text
  https://raw.githubusercontent.com/Oht8wooWi8yait9n/ntrs/main/ntrs_citations_all.xml
  ```

---

## Ingesting into Onyx

1. In the Onyx UI, navigate to **Admin Panel** → **Connectors** → **Web**.
2. Click **Add Connector** (or **Edit** your existing connector):
   - **Name**: `NASA NTRS Technical Reports`
   - **Base URL / Sitemap URL**:
     - For modern aerospace research: Use the **Modern Era PDFs** URL (`sitemaps/pdf/ntrs_pdf_modern.xml`).
     - For all 297k technical PDFs: Use the **All Full-Text PDFs** URL (`ntrs_pdf_all.xml`).
     - For the entire catalog: Use the **All Records** URL (`ntrs_all.xml`).
   - **Scrape Type**: `Sitemap`
   - **Indexing Schedule**: Weekly or Monthly
3. Click **Connect**. Onyx will parse the flat sitemap, extract the PDF URLs, download the PDFs directly, and vectorize the content into your document set.

---

## Automation & Maintenance

A GitHub Actions workflow (`.github/workflows/update-sitemap.yml`) runs weekly on Sundays at 04:00 UTC. It queries the NTRS API for newly released technical reports, updates the XML sitemaps, and commits new entries automatically.
