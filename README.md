# NASA Technical Reports Server (NTRS) Sitemaps for Onyx RAG

Automated XML sitemaps and plain-text URL indexes for the **NASA Technical Reports Server (NTRS)**, indexing **602,567 total records** spanning over a century of aeronautics and aerospace research (1915–2026).

---

## Overview

NTRS hosts NASA's technical publications, meeting papers, contractor reports, research papers, and NACA historical archives.

The catalog contains two primary resource types:

1. **Full-Text PDFs (297,463 documents)**: Direct links to the actual technical PDF files hosted on NASA servers (`https://ntrs.nasa.gov/api/citations/{id}/downloads/{filename}.pdf`). Onyx downloads the full PDF, parses the entire technical text, and embeds all chunks into your vector database.
2. **Metadata & Abstract Citations (305,104 records)**: Links to the server-side rendered citation pages (`https://ntrs.nasa.gov/citations/{id}`) containing paper titles, author affiliations, publication details, and full abstracts for commercial journal reprints (paywalled articles in *Nature*, *Science*, *AIAA*, *IEEE*) and conference proceedings where no public PDF was submitted.

---

## Sitemap Architecture & URLs for Onyx

Because standard XML sitemaps have a protocol limit of **50,000 URLs per file**, the collection is partitioned into chunked sub-sitemaps referenced by standard `<sitemapindex>` roots.

### 1. Full-Text PDFs Only (Recommended for Deep Technical Search)
* **All PDFs Sitemap Index (297,463 PDFs)**:
  ```text
  https://raw.githubusercontent.com/Oht8wooWi8yait9n/ntrs/main/ntrs_pdf_sitemap.xml
  ```
* **Modern Era PDFs Only (2010–2026, 79,391 PDFs)**:
  ```text
  https://raw.githubusercontent.com/Oht8wooWi8yait9n/ntrs/main/sitemaps/pdf/ntrs_pdf_modern.xml
  ```
* **Individual 50,000-URL PDF Chunks**:
  - Part 1: `https://raw.githubusercontent.com/Oht8wooWi8yait9n/ntrs/main/sitemaps/pdf/ntrs_pdf_1.xml`
  - Part 2: `https://raw.githubusercontent.com/Oht8wooWi8yait9n/ntrs/main/sitemaps/pdf/ntrs_pdf_2.xml`
  - Part 3: `https://raw.githubusercontent.com/Oht8wooWi8yait9n/ntrs/main/sitemaps/pdf/ntrs_pdf_3.xml`
  - Part 4: `https://raw.githubusercontent.com/Oht8wooWi8yait9n/ntrs/main/sitemaps/pdf/ntrs_pdf_4.xml`
  - Part 5: `https://raw.githubusercontent.com/Oht8wooWi8yait9n/ntrs/main/sitemaps/pdf/ntrs_pdf_5.xml`
  - Part 6: `https://raw.githubusercontent.com/Oht8wooWi8yait9n/ntrs/main/sitemaps/pdf/ntrs_pdf_6.xml`

### 2. Metadata & Abstract Citations Only (305,104 Records)
* **Citations Sitemap Index**:
  ```text
  https://raw.githubusercontent.com/Oht8wooWi8yait9n/ntrs/main/ntrs_citations_sitemap.xml
  ```
* **Individual 50,000-Record Citations Chunks**:
  - `sitemaps/citations/ntrs_citations_1.xml` through `ntrs_citations_7.xml`

### 3. Master Index (Combined PDFs + Citations, 602,567 Records)
* **Master Sitemap Index**:
  ```text
  https://raw.githubusercontent.com/Oht8wooWi8yait9n/ntrs/main/ntrs_sitemap.xml
  ```

---

## Ingesting into Onyx

1. In the Onyx UI, navigate to **Admin Panel** → **Connectors** → **Web**.
2. Click **Add Connector**:
   - **Name**: `NASA NTRS Technical Reports`
   - **Base URL / Sitemap URL**:
     - For modern papers first: Paste the **Modern Era PDFs** URL (`sitemaps/pdf/ntrs_pdf_modern.xml`).
     - For all technical PDFs: Paste the **All PDFs Sitemap Index** URL (`ntrs_pdf_sitemap.xml`).
     - For the entire archive: Paste the **Master Sitemap Index** URL (`ntrs_sitemap.xml`).
   - **Scrape Type**: `Sitemap`
   - **Indexing Schedule**: Weekly or Monthly
3. Click **Connect**. Onyx will parse the sitemap index, crawl the sub-sitemaps, download the PDFs, and vectorize the content into your document set.

---

## Automation & Maintenance

This repository includes a GitHub Actions workflow (`.github/workflows/update-sitemap.yml`) that runs weekly on Sundays at 04:00 UTC. It queries the NTRS API for newly released technical reports, updates the XML sitemaps, and commits new entries automatically.
