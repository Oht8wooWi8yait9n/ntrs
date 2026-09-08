#!/usr/bin/env python3
"""
Generate comprehensive XML sitemaps for the NASA Technical Reports Server (NTRS).
Indexes:
  1. Full-Text PDFs (~302,000 direct NASA-hosted PDF URLs)
  2. Metadata/Abstract Citations (~300,000 NTRS landing/abstract pages)
  3. Modern Era PDFs (2010-2026) for focused indexing
Outputs:
  - ntrs_sitemap.xml (Root Master Sitemap Index)
  - ntrs_pdf_sitemap.xml (PDF Sitemap Index)
  - sitemaps/pdf/ntrs_pdf_1.xml ... 7.xml (50k URLs each)
  - sitemaps/pdf/ntrs_pdf_modern.xml (Modern PDFs 2010-2026)
  - ntrs_citations_sitemap.xml (Citations Sitemap Index)
  - sitemaps/citations/ntrs_citations_1.xml ... 6.xml (50k URLs each)
  - ntrs_pdf_urls.txt, ntrs_citations_urls.txt, ntrs_all_urls.txt
"""

import os
import re
import gzip
import time
import datetime
from concurrent.futures import ThreadPoolExecutor
import requests

GITHUB_RAW_BASE = "https://raw.githubusercontent.com/Oht8wooWi8yait9n/ntrs/main"
NTRS_API_SEARCH = "https://ntrs.nasa.gov/api/citations/search"
NTRS_SITEMAP_INDEX = "https://ntrs.nasa.gov/sitemap.xml"
CHUNK_SIZE = 50000

def get_iso_date():
    return datetime.date.today().isoformat()

def step1_fetch_all_citation_ids():
    """Download official NTRS sitemaps and extract all citation IDs."""
    print("=== Step 1: Downloading 116 official NTRS sitemaps ===")
    t0 = time.time()
    resp = requests.get(NTRS_SITEMAP_INDEX, timeout=15)
    sitemap_urls = re.findall(r'<loc>(https://ntrs\.nasa\.gov/sitemap-[^<]+)</loc>', resp.text)
    print(f"Found {len(sitemap_urls)} sub-sitemaps in official index.")

    def parse_sub(url):
        try:
            r = requests.get(url, timeout=20)
            text = gzip.decompress(r.content).decode("utf-8")
            return re.findall(r'<loc>https://ntrs\.nasa\.gov/citations/(\d+)</loc>', text)
        except Exception as e:
            print(f"  Error fetching {url}: {e}")
            return []

    all_ids = set()
    with ThreadPoolExecutor(max_workers=20) as ex:
        for ids in ex.map(parse_sub, sitemap_urls):
            all_ids.update(ids)

    dt = time.time() - t0
    print(f"Step 1 Complete: Extracted {len(all_ids):,} total unique citation IDs in {dt:.2f}s.\n")
    return all_ids

def step2_harvest_full_text_pdfs():
    """Query NTRS search API across publication and creation years to extract direct PDF links."""
    print("=== Step 2: Harvesting direct full-text PDF links from NTRS API ===")
    t0 = time.time()

    tasks = []
    # 1. Published years 1914 to 2027
    for y in range(1914, 2028):
        body = {
            "page": {"size": 10000},
            "index": ["submissions*"],
            "disseminated": ["DOCUMENT_AND_METADATA"],
            "published": {"gte": f"{y}-01-01T00:00:00", "lte": f"{y}-12-31T23:59:59"}
        }
        tasks.append((f"pub_{y}", body, y))

    # 2. Created years 2014 to 2026 (catches recent submissions without published dates)
    for y in range(2014, 2027):
        body = {
            "page": {"size": 10000},
            "index": ["submissions*"],
            "disseminated": ["DOCUMENT_AND_METADATA"],
            "created": {"gte": f"{y}-01-01T00:00:00", "lte": f"{y}-12-31T23:59:59"}
        }
        tasks.append((f"cre_{y}", body, y))

    print(f"Dispatching {len(tasks)} partition queries with ThreadPoolExecutor...")

    def query_partition(item):
        name, body, year = item
        max_retries = 3
        for attempt in range(max_retries):
            try:
                r = requests.post(NTRS_API_SEARCH, json=body, timeout=45)
                if r.status_code == 200:
                    results = r.json().get("results", [])
                    extracted = []
                    for doc in results:
                        cid = str(doc.get("id", ""))
                        downloads = doc.get("downloads", [])
                        for d in downloads:
                            pdf_rel = d.get("links", {}).get("pdf")
                            if pdf_rel and pdf_rel.endswith(".pdf"):
                                full_url = f"https://ntrs.nasa.gov{pdf_rel}"
                                extracted.append((cid, full_url, year))
                                break
                    return extracted
                elif r.status_code == 429:
                    time.sleep(2 * (attempt + 1))
            except Exception as e:
                if attempt == max_retries - 1:
                    print(f"  Error querying {name}: {e}")
                time.sleep(1)
        return []

    pdf_dict = {}  # cid -> (pdf_url, year)
    with ThreadPoolExecutor(max_workers=8) as ex:
        for batch in ex.map(query_partition, tasks):
            for cid, pdf_url, year in batch:
                if cid not in pdf_dict:
                    pdf_dict[cid] = (pdf_url, year)

    dt = time.time() - t0
    print(f"Step 2 Complete: Harvested {len(pdf_dict):,} citations with direct PDF links in {dt:.2f}s.\n")
    return pdf_dict

def write_urlset_xml(filepath, urls, lastmod):
    """Write standard urlset XML conforming to sitemaps.org."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
        for u in urls:
            f.write("  <url>\n")
            f.write(f"    <loc>{u}</loc>\n")
            f.write(f"    <lastmod>{lastmod}</lastmod>\n")
            f.write("    <changefreq>monthly</changefreq>\n")
            f.write("  </url>\n")
        f.write("</urlset>\n")

def write_sitemapindex_xml(filepath, sub_sitemap_urls, lastmod):
    """Write standard sitemapindex XML referencing sub-sitemaps."""
    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
        for s in sub_sitemap_urls:
            f.write("  <sitemap>\n")
            f.write(f"    <loc>{s}</loc>\n")
            f.write(f"    <lastmod>{lastmod}</lastmod>\n")
            f.write("  </sitemap>\n")
        f.write("</sitemapindex>\n")

def main():
    start_time = time.time()
    today = get_iso_date()
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # 1. Fetch all citation IDs
    all_citation_ids = step1_fetch_all_citation_ids()

    # 2. Harvest all PDF URLs
    pdf_dict = step2_harvest_full_text_pdfs()

    # 3. Categorize URLs
    print("=== Step 3: Categorizing and partitioning URLs ===")
    pdf_urls = []
    modern_pdf_urls = []
    citation_urls = []

    # Sort citations deterministically (newest first)
    sorted_all_ids = sorted(all_citation_ids, reverse=True)

    for cid in sorted_all_ids:
        if cid in pdf_dict:
            pdf_url, year = pdf_dict[cid]
            pdf_urls.append(pdf_url)
            if year >= 2010:
                modern_pdf_urls.append(pdf_url)
        else:
            citation_urls.append(f"https://ntrs.nasa.gov/citations/{cid}")

    print(f"Total Full-Text PDF URLs: {len(pdf_urls):,}")
    print(f"  Modern Era (2010-2026) PDFs: {len(modern_pdf_urls):,}")
    print(f"Total Metadata/Abstract URLs: {len(citation_urls):,}")
    print(f"Combined Total URLs: {len(pdf_urls) + len(citation_urls):,}")

    # 4. Generate PDF Sitemaps (Chunks of 50k)
    print("\n=== Step 4: Generating PDF Sitemaps ===")
    pdf_sub_urls = []
    pdf_chunks = [pdf_urls[i:i + CHUNK_SIZE] for i in range(0, len(pdf_urls), CHUNK_SIZE)]
    for idx, chunk in enumerate(pdf_chunks, 1):
        rel_path = f"sitemaps/pdf/ntrs_pdf_{idx}.xml"
        file_path = os.path.join(base_dir, rel_path)
        write_urlset_xml(file_path, chunk, today)
        raw_url = f"{GITHUB_RAW_BASE}/{rel_path}"
        pdf_sub_urls.append(raw_url)
        print(f"  Wrote {rel_path} ({len(chunk):,} URLs)")

    # PDF Modern Sitemap
    modern_rel = "sitemaps/pdf/ntrs_pdf_modern.xml"
    write_urlset_xml(os.path.join(base_dir, modern_rel), modern_pdf_urls, today)
    print(f"  Wrote {modern_rel} ({len(modern_pdf_urls):,} URLs)")

    # PDF Sitemap Index
    write_sitemapindex_xml(os.path.join(base_dir, "ntrs_pdf_sitemap.xml"), pdf_sub_urls, today)
    print(f"  Wrote ntrs_pdf_sitemap.xml ({len(pdf_sub_urls)} sub-sitemaps)")

    # 5. Generate Citations Sitemaps (Chunks of 50k)
    print("\n=== Step 5: Generating Citations Sitemaps ===")
    cit_sub_urls = []
    cit_chunks = [citation_urls[i:i + CHUNK_SIZE] for i in range(0, len(citation_urls), CHUNK_SIZE)]
    for idx, chunk in enumerate(cit_chunks, 1):
        rel_path = f"sitemaps/citations/ntrs_citations_{idx}.xml"
        file_path = os.path.join(base_dir, rel_path)
        write_urlset_xml(file_path, chunk, today)
        raw_url = f"{GITHUB_RAW_BASE}/{rel_path}"
        cit_sub_urls.append(raw_url)
        print(f"  Wrote {rel_path} ({len(chunk):,} URLs)")

    # Citations Sitemap Index
    write_sitemapindex_xml(os.path.join(base_dir, "ntrs_citations_sitemap.xml"), cit_sub_urls, today)
    print(f"  Wrote ntrs_citations_sitemap.xml ({len(cit_sub_urls)} sub-sitemaps)")

    # 6. Generate Master Sitemap Index (PDFs + Citations)
    print("\n=== Step 6: Generating Master Sitemap Index ===")
    master_subs = pdf_sub_urls + cit_sub_urls
    write_sitemapindex_xml(os.path.join(base_dir, "ntrs_sitemap.xml"), master_subs, today)
    print(f"  Wrote ntrs_sitemap.xml ({len(master_subs)} total sub-sitemaps)")

    # 7. Write Plain Text URL Lists
    print("\n=== Step 7: Writing Plain Text URL Lists ===")
    with open(os.path.join(base_dir, "ntrs_pdf_urls.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(pdf_urls) + "\n")
    with open(os.path.join(base_dir, "ntrs_citations_urls.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(citation_urls) + "\n")
    with open(os.path.join(base_dir, "ntrs_all_urls.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(pdf_urls + citation_urls) + "\n")
    print("  Wrote ntrs_pdf_urls.txt, ntrs_citations_urls.txt, ntrs_all_urls.txt")

    total_time = time.time() - start_time
    print(f"\nAll operations completed successfully in {total_time:.2f}s ({total_time / 60:.2f} mins).")

if __name__ == "__main__":
    main()
